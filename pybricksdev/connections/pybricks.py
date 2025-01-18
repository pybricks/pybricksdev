# SPDX-License-Identifier: MIT
# Copyright (c) 2021-2023 The Pybricks Authors

import asyncio
import contextlib
import logging
import os
import struct
from typing import Awaitable, List, Optional, TypeVar

import reactivex.operators as op
import semver
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from packaging.version import Version
from reactivex import Observable
from reactivex.subject import BehaviorSubject, Subject
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from pybricksdev.ble.lwp3.bytecodes import HubKind
from pybricksdev.ble.nus import NUS_RX_UUID, NUS_TX_UUID
from pybricksdev.ble.pybricks import (
    FW_REV_UUID,
    PNP_ID_UUID,
    PYBRICKS_COMMAND_EVENT_UUID,
    PYBRICKS_HUB_CAPABILITIES_UUID,
    PYBRICKS_PROTOCOL_VERSION,
    SW_REV_UUID,
    Command,
    Event,
    HubCapabilityFlag,
    StatusFlag,
    unpack_hub_capabilities,
    unpack_pnp_id,
)
from pybricksdev.compile import compile_file, compile_multi_file
from pybricksdev.connections import ConnectionState
from pybricksdev.tools import chunk
from pybricksdev.tools.checksum import xor_bytes

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PybricksHub:
    EOL = b"\r\n"  # MicroPython EOL

    fw_version: Optional[Version]
    """
    Firmware version of the connected hub or ``None`` if not connected yet.
    """

    _mpy_abi_version: int
    """
    MPY ABI version of the connected hub or ``0`` if not connected yet or if
    connected to hub with Pybricks profile >= v1.2.0.
    """

    _max_write_size: int = 20
    """
    Maximum characteristic write size in bytes.

    This will be the minium safe write size unless a hub is connected and it has
    Pybricks profile >= v1.2.0.
    """

    _capability_flags: HubCapabilityFlag
    """
    Hub capability flags of connected hub. ``HubCapabilityFlags(0)`` if the hub
    has not been connected yet or the connected hub has Pybricks profile < v1.2.0.
    """

    _max_user_program_size: int
    """
    The maximum allowable user program size for the connected hub. ``0`` if the hub
    has not been connected yet or the connected hub has Pybricks profile < v1.2.0.
    """

    def __init__(self):
        self.connection_state_observable = BehaviorSubject(ConnectionState.DISCONNECTED)
        self.status_observable = BehaviorSubject(StatusFlag(0))
        self._stdout_subject = Subject()
        self.nus_observable = Subject()
        self.print_output = True
        self.fw_version = None
        self._mpy_abi_version = 0
        self._capability_flags = HubCapabilityFlag(0)
        self._max_user_program_size = 0

        # whether to enable line handler features or not
        self._enable_line_handler = False

        # buffered stdout from the hub for splitting into lines
        self._stdout_buf = bytearray()

        # REVISIT: this can potentially waste a lot of RAM if not drained
        self._stdout_line_queue = asyncio.Queue()

        # REVISIT: It would be better to be able to subscribe to output instead
        # of always capturing it even if it is not used. This is currently
        # used in motor test code in pybricks-micropython.
        self.output: List[bytes] = []
        """
        Contains lines printed to stdout of the hub as a a list of bytes.

        List is reset each time :meth:`run()` is called.
        """

        # prior to Pybricks Profile v1.3.0, NUS was used for stdio
        self._legacy_stdio = False

        # indicates is we are currently downloading a program over NUS (legacy download)
        self._downloading_via_nus = False

        self.hub_kind: HubKind
        self.hub_variant: int

        # File handle for logging
        self.log_file = None

    @property
    def stdout_observable(self) -> Observable[bytes]:
        """
        Observable used to subscribe to stdout of the hub.
        """
        return self._stdout_subject

    def _line_handler(self, line: bytes) -> None:
        """
        Handles new incoming lines. Handle special actions if needed,
        otherwise just print it as regular lines.

        Arguments:
            line: Line to process.
        """

        # The line tells us to open a log file, so do it.
        if b"PB_OF:" in line or b"_file_begin_ " in line:
            if self.log_file is not None:
                raise RuntimeError("Log file is already open!")

            path_start = len(b"PB_OF:") if b"PB_OF:" in line else len(b"_file_begin_ ")

            # Get path relative to running script, so log will go
            # in the same folder unless specified otherwise.
            full_path = os.path.join(self.script_dir, line[path_start:].decode())
            dir_path, _ = os.path.split(full_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            logger.info("Saving log to {0}.".format(full_path))
            self.log_file = open(full_path, "w")
            return

        # The line tells us to close a log file, so do it.
        if b"PB_EOF" in line or b"_file_end_" in line:
            if self.log_file is None:
                raise RuntimeError("No log file is currently open!")
            logger.info("Done saving log.")
            self.log_file.close()
            self.log_file = None
            return

        line_str = line.decode()

        # If we are processing datalog, save current line to the open file.
        if self.log_file is not None:
            print(line_str, file=self.log_file)
            return

        self.output.append(line)

        if self.print_output:
            print(line_str)
            return

        self._stdout_line_queue.put_nowait(line_str)

    def _handle_line_data(self, data: bytes) -> None:
        self._stdout_buf.extend(data)

        # Break up data into lines and take those out of the buffer
        lines = []
        while True:
            # Find and split at end of line
            index = self._stdout_buf.find(self.EOL)
            # If no more line end is found, we are done
            if index < 0:
                break
            # If we found a line, save it, and take it from the buffer
            lines.append(self._stdout_buf[:index])
            del self._stdout_buf[: index + len(self.EOL)]

        # Call handler for each line that we found
        for line in lines:
            self._line_handler(line)

    def _nus_handler(self, sender, data: bytearray) -> None:
        self.nus_observable.on_next(data)

        # legacy firmware may use NUS for download and run, in which case
        # we need to ignore the incoming data
        if self._downloading_via_nus:
            return

        logger.debug("NUS DATA: %r", data)

        # support legacy firmware where the Nordic UART service
        # was used for stdio
        if self._legacy_stdio:
            self._stdout_subject.on_next(data)

            if self._enable_line_handler:
                self._handle_line_data(data)

    def _pybricks_service_handler(self, _: int, data: bytes) -> None:
        if data[0] == Event.STATUS_REPORT:
            # decode the payload
            (flags,) = struct.unpack_from("<I", data, 1)
            self.status_observable.on_next(StatusFlag(flags))
        elif data[0] == Event.WRITE_STDOUT:
            payload = data[1:]
            self._stdout_subject.on_next(payload)

            if self._enable_line_handler:
                self._handle_line_data(payload)

    async def connect(self, device: BLEDevice):
        """Connects to a device that was discovered with :meth:`pybricksdev.ble.find_device`

        Args:
            device: The device to connect to.

        Raises:
            BleakError: if connecting failed (or old firmware without Device
                Information Service)
            RuntimeError: if Pybricks Protocol version is not supported
        """
        logger.info(f"Connecting to {device.name}")

        if self.connection_state_observable.value != ConnectionState.DISCONNECTED:
            raise RuntimeError(
                f"attempting to connect with invalid state: {self.connection_state_observable.value}"
            )

        async with contextlib.AsyncExitStack() as stack:
            self.connection_state_observable.on_next(ConnectionState.CONNECTING)

            stack.callback(
                self.connection_state_observable.on_next, ConnectionState.DISCONNECTED
            )

            def handle_disconnect(_: BleakClient):
                logger.info("Disconnected!")
                self.connection_state_observable.on_next(ConnectionState.DISCONNECTED)

            self.client = BleakClient(device, disconnected_callback=handle_disconnect)

            await self.client.connect()

            stack.push_async_callback(self.disconnect)

            logger.info("Connected successfully!")

            fw_version = await self.client.read_gatt_char(FW_REV_UUID)
            self.fw_version = Version(fw_version.decode())

            protocol_version = await self.client.read_gatt_char(SW_REV_UUID)
            protocol_version = semver.VersionInfo.parse(protocol_version.decode())

            if (
                protocol_version < PYBRICKS_PROTOCOL_VERSION
                or protocol_version >= PYBRICKS_PROTOCOL_VERSION.bump_major()
            ):
                raise RuntimeError(
                    f"Unsupported Pybricks protocol version: {protocol_version}"
                )

            pnp_id = await self.client.read_gatt_char(PNP_ID_UUID)
            _, _, self.hub_kind, self.hub_variant = unpack_pnp_id(pnp_id)

            if protocol_version >= "1.2.0":
                caps = await self.client.read_gatt_char(PYBRICKS_HUB_CAPABILITIES_UUID)
                (
                    self._max_write_size,
                    self._capability_flags,
                    self._max_user_program_size,
                ) = unpack_hub_capabilities(caps)
            else:
                # HACK: prior to profile v1.2.0 isn't a proper way to get the
                # MPY ABI version from hub so we use heuristics on the firmware version
                self._mpy_abi_version = (
                    6 if self.fw_version >= Version("3.2.0b2") else 5
                )

            if protocol_version < "1.3.0":
                self._legacy_stdio = True

            await self.client.start_notify(NUS_TX_UUID, self._nus_handler)
            await self.client.start_notify(
                PYBRICKS_COMMAND_EVENT_UUID, self._pybricks_service_handler
            )

            self.connection_state_observable.on_next(ConnectionState.CONNECTED)

            # don't unwind on success
            stack.pop_all()

    async def disconnect(self):
        logger.info("Disconnecting...")

        if self.connection_state_observable.value == ConnectionState.CONNECTED:
            self.connection_state_observable.on_next(ConnectionState.DISCONNECTING)
            await self.client.disconnect()
            # ConnectionState.DISCONNECTED should be set by disconnect callback
            assert (
                self.connection_state_observable.value == ConnectionState.DISCONNECTED
            )
        else:
            logger.debug("skipping disconnect because not connected")

    async def race_disconnect(self, awaitable: Awaitable[T]) -> T:
        """
        Races an awaitable against a disconnect event.

        If a disconnect event occurs before the awaitable is complete, a
        ``RuntimeError`` is raised and the awaitable is canceled.

        Otherwise, the result of the awaitable is returned. If the awaitable
        raises an exception, that exception will be raised.

        Args:
            awaitable: Any awaitable such as a coroutine.

        Returns:
            The result of the awaitable.

        Raises:
            RuntimeError:
                Thrown if the hub is disconnected before the awaitable completed.
        """
        awaitable_task = asyncio.ensure_future(awaitable)

        disconnect_event = asyncio.Event()
        disconnect_task = asyncio.ensure_future(disconnect_event.wait())

        def handle_disconnect(state: ConnectionState):
            if state == ConnectionState.DISCONNECTED:
                disconnect_event.set()

        with self.connection_state_observable.subscribe(handle_disconnect):
            done, pending = await asyncio.wait(
                {awaitable_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for t in pending:
                t.cancel()

            if awaitable_task not in done:
                raise RuntimeError("disconnected during operation")

            return awaitable_task.result()

    async def write(self, data: bytes) -> None:
        """
        Writes raw data to stdin on the hub.

        This is a low-level function to send a single write command over
        Bluetooth. Most users will want to use :meth:`write_string()` or
        :meth:`write_line()` instead.

        Args:
            data: Any bytes-like object that will fit in a single BLE packet.
        """
        if self._legacy_stdio:
            await self.client.write_gatt_char(NUS_RX_UUID, data, False)
        else:
            msg = bytearray([Command.WRITE_STDIN])
            msg.extend(data)

            if len(msg) > self._max_write_size:
                raise ValueError(
                    f"data is too big, limited to {self._max_write_size - 1} bytes"
                )

            await self.client.write_gatt_char(PYBRICKS_COMMAND_EVENT_UUID, msg, True)

    async def write_string(self, value: str) -> None:
        """
        Writes a string to stdin on the hub.

        Args:
            value: The string to write.
        """

        for c in chunk(value.encode(), self._max_write_size - 1):
            await self.write(c)

    async def write_line(self, value: str) -> None:
        """
        Writes a string to stdin on the hub and adds a newline (``\\n``)
        to the end.

        Args:
            value: The string to write.
        """
        await self.write_string(value + "\n")

    async def read_line(self) -> str:
        """
        Waits for a line to be read from stdout on the hub.

        Returns:
            The next line read from stdout (without the newline).

        Raises:
            RuntimeError:
                if line handler is disabled (e.g. :meth:`run` is
                called with ``line_handler=False``)
            RuntimeError:
                if hub becomes disconnected
        """
        if not self._enable_line_handler:
            raise RuntimeError("line handler is disabled, method would block forever")

        return await self.race_disconnect(self._stdout_line_queue.get())

    async def download_user_program(self, program: bytes) -> None:
        """
        Downloads user program to user RAM on the hub and indicates progress
        using tqdm.

        This is a somewhat low-level function. It verifies that the size of the
        program is not too big but it does not verify that the program data
        is valid or can be run on the hub. Also see :meth:`run`.

        Requires hub with Pybricks Profile >= v1.2.0.

        Args:
            program: The raw program data.

        Raises:
            ValueError: if program is too large to fit on the hub
        """
        # the hub tells us the max size of program that is allowed, so we can fail early
        if len(program) > self._max_user_program_size:
            raise ValueError(
                f"program is too big ({len(program)} bytes). Hub has limit of {self._max_user_program_size} bytes."
            )

        # clear user program meta so hub doesn't try to run invalid program
        await self.client.write_gatt_char(
            PYBRICKS_COMMAND_EVENT_UUID,
            struct.pack("<BI", Command.WRITE_USER_PROGRAM_META, 0),
            response=True,
        )

        # payload is max size minus header size
        payload_size = self._max_write_size - 5

        # write program data with progress bar
        with logging_redirect_tqdm(), tqdm(
            total=len(program), unit="B", unit_scale=True
        ) as pbar:
            for i, c in enumerate(chunk(program, payload_size)):
                await self.client.write_gatt_char(
                    PYBRICKS_COMMAND_EVENT_UUID,
                    struct.pack(
                        f"<BI{len(c)}s",
                        Command.COMMAND_WRITE_USER_RAM,
                        i * payload_size,
                        c,
                    ),
                    response=True,
                )
                pbar.update(len(c))

        # set the metadata to notify that writing was successful
        await self.client.write_gatt_char(
            PYBRICKS_COMMAND_EVENT_UUID,
            struct.pack("<BI", Command.WRITE_USER_PROGRAM_META, len(program)),
            response=True,
        )

    async def start_user_program(self) -> None:
        """
        Starts the user program that is already in RAM on the hub.

        Requires hub with Pybricks Profile >= v1.2.0.
        """
        await self.client.write_gatt_char(
            PYBRICKS_COMMAND_EVENT_UUID,
            struct.pack("<B", Command.START_USER_PROGRAM),
            response=True,
        )

    async def stop_user_program(self) -> None:
        """
        Stops the user program on the hub if it is running.
        """
        await self.client.write_gatt_char(
            PYBRICKS_COMMAND_EVENT_UUID,
            struct.pack("<B", Command.STOP_USER_PROGRAM),
            response=True,
        )

    async def run(
        self,
        py_path: Optional[str] = None,
        wait: bool = True,
        print_output: bool = True,
        line_handler: bool = True,
    ) -> None:
        """
        Compiles and runs a user program.

        Args:
            py_path: The path to the .py file to compile. If None, runs a
                previously downloaded program.
            wait: If true, wait for the user program to stop before returning.
            print_output: If true, echo stdout of the hub to ``sys.stdout``.
            line_handler: If true enable hub stdout line handler features.
        """
        if self.connection_state_observable.value != ConnectionState.CONNECTED:
            raise RuntimeError("not connected")

        # Reset output buffer
        self.log_file = None
        self.output = []
        self._stdout_buf.clear()
        self._stdout_line_queue = asyncio.Queue()
        self.print_output = print_output
        self._enable_line_handler = line_handler
        self.script_dir = os.getcwd()
        if py_path is not None:
            self.script_dir, _ = os.path.split(py_path)

        # maintain compatibility with older firmware (Pybricks profile < 1.2.0).
        if self._mpy_abi_version:
            if py_path is None:
                raise RuntimeError(
                    "Hub does not support running stored program. Provide a py_path to run"
                )
            await self._legacy_run(py_path, wait)
            return

        # since Pybricks profile v1.2.0, the hub will tell us which file format(s) it supports
        if not (
            self._capability_flags
            & (
                HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6
                | HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6_1_NATIVE
            )
        ):
            raise RuntimeError(
                "Hub is not compatible with any of the supported file formats"
            )

        # no support for native modules unless one of the flags below is set
        abi = 6

        if (
            self._capability_flags
            & HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6_1_NATIVE
        ):
            abi = (6, 1)

        if py_path is not None:
            mpy = await compile_multi_file(py_path, abi)
            await self.download_user_program(mpy)

        await self.start_user_program()

        if wait:
            await self._wait_for_user_program_stop()

    async def _legacy_run(self, py_path: str, wait: bool) -> None:
        """
        Version of :meth:`run` for compatibility with older firmware ()
        """
        # Compile the script to mpy format
        mpy = await compile_file(
            os.path.dirname(py_path), os.path.basename(py_path), self._mpy_abi_version
        )

        try:
            self._downloading_via_nus = True

            queue: asyncio.Queue[bytes] = asyncio.Queue()
            subscription = self.nus_observable.subscribe(
                lambda data: queue.put_nowait(data)
            )

            async def send_block(data: bytes) -> None:
                """
                In order to prevent sending data to the hub faster than it can
                be processed, it is sent in blocks of 100 bytes or less. Then
                we wait for the hub to send a checksum to acknowledge that it
                has processed the data.

                Args:
                    data: The data to send (100 bytes or less).
                """
                if self.hub_kind == HubKind.BOOST:
                    # BOOST Move hub has fixed MTU of 23 so we can only send 20
                    # bytes at a time
                    for c in chunk(data, 20):
                        await self.client.write_gatt_char(NUS_RX_UUID, c, False)
                else:
                    await self.client.write_gatt_char(NUS_RX_UUID, data, False)

                msg = await asyncio.wait_for(
                    self.race_disconnect(queue.get()), timeout=0.5
                )
                actual_checksum = msg[0]
                expected_checksum = xor_bytes(data, 0)

                if actual_checksum != expected_checksum:
                    raise RuntimeError(
                        f"bad checksum: expecting {hex(expected_checksum)} but received {hex(actual_checksum)}"
                    )

            # Get length of file and send it as bytes to hub
            length = len(mpy).to_bytes(4, byteorder="little")
            await send_block(length)

            # Send the data chunk by chunk
            with logging_redirect_tqdm(), tqdm(
                total=len(mpy), unit="B", unit_scale=True
            ) as pbar:
                for c in chunk(mpy, 100):
                    await send_block(c)
                    pbar.update(len(c))
        finally:
            subscription.dispose()
            self._downloading_via_nus = False

        if wait:
            await self._wait_for_user_program_stop()

    async def _wait_for_user_program_stop(self):
        user_program_running: asyncio.Queue[bool] = asyncio.Queue()

        with self.status_observable.pipe(
            op.map(lambda s: bool(s & StatusFlag.USER_PROGRAM_RUNNING)),
            op.distinct_until_changed(),
        ).subscribe(lambda s: user_program_running.put_nowait(s)):
            # The first item in the queue is the current status. The status
            # could change before or after the last checksum is received,
            # so this could be either true or false.
            is_running = await self.race_disconnect(user_program_running.get())

            if not is_running:
                # if the program has not already started, wait a short time
                # for it to start
                try:
                    await asyncio.wait_for(
                        self.race_disconnect(user_program_running.get()), 1
                    )
                except asyncio.TimeoutError:
                    # if it doesn't start, assume it was a very short lived
                    # program and we just missed the status message
                    logger.debug(
                        "timed out waiting for user program to start, assuming it was short lived"
                    )
                    return

            # At this point, we know the user program is running, so the
            # next item in the queue must indicate that the user program
            # has stopped.
            is_running = await self.race_disconnect(user_program_running.get())

            # maybe catch mistake if the code is changed
            assert not is_running

            # sleep is a hack to receive all output from user program since
            # the firmware currently doesn't flush the buffer before clearing
            # the user program running status flag
            # https://github.com/pybricks/support/issues/305
            await asyncio.sleep(0.3)
