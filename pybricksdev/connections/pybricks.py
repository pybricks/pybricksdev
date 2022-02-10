# SPDX-License-Identifier: MIT
# Copyright (c) 2021-2022 The Pybricks Authors

import asyncio
import logging
import os
import struct
from typing import Awaitable, TypeVar

import rx.operators as op
import semver
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from rx.subject import Subject, BehaviorSubject, AsyncSubject
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from ..ble.lwp3.bytecodes import HubKind
from ..ble.nus import NUS_RX_UUID, NUS_TX_UUID
from ..ble.pybricks import (
    PYBRICKS_CONTROL_UUID,
    PYBRICKS_PROTOCOL_VERSION,
    SW_REV_UUID,
    PNP_ID_UUID,
    Event,
    StatusFlag,
    unpack_pnp_id,
)
from ..compile import compile_file
from ..tools import chunk
from ..tools.checksum import xor_bytes

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PybricksHub:
    EOL = b"\r\n"  # MicroPython EOL

    def __init__(self):
        self.disconnect_observable = AsyncSubject()
        self.status_observable = BehaviorSubject(StatusFlag(0))
        self.nus_observable = Subject()
        self.stream_buf = bytearray()
        self.output = []
        self.print_output = True

        # indicates that the hub is currently connected via BLE
        self.connected = False

        # indicates is we are currently downloading a program
        self.loading = False

        self.hub_kind: HubKind
        self.hub_variant: int

        # File handle for logging
        self.log_file = None

    def line_handler(self, line):
        """Handles new incoming lines. Handle special actions if needed,
        otherwise just print it as regular lines.

        Arguments:
            line (bytearray):
                Line to process.
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

        # If we are processing datalog, save current line to the open file.
        if self.log_file is not None:
            print(line.decode(), file=self.log_file)
            return

        # If there is nothing special about this line, print it if requested.
        self.output.append(line)
        if self.print_output:
            print(line.decode())

    def nus_handler(self, sender, data):
        self.nus_observable.on_next(data)

        # Store incoming data
        if not self.loading:
            self.stream_buf += data
            logger.debug("NUS DATA: {0}".format(data))

        # Break up data into lines and take those out of the buffer
        lines = []
        while True:
            # Find and split at end of line
            index = self.stream_buf.find(self.EOL)
            # If no more line end is found, we are done
            if index < 0:
                break
            # If we found a line, save it, and take it from the buffer
            lines.append(self.stream_buf[0:index])
            del self.stream_buf[0 : index + len(self.EOL)]

        # Call handler for each line that we found
        for line in lines:
            self.line_handler(line)

    def pybricks_service_handler(self, _: int, data: bytes) -> None:
        if data[0] == Event.STATUS_REPORT:
            # decode the payload
            (flags,) = struct.unpack_from("<I", data, 1)
            self.status_observable.on_next(StatusFlag(flags))

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

        def handle_disconnect(client: BleakClient):
            logger.info("Disconnected!")
            self.disconnect_observable.on_next(True)
            self.disconnect_observable.on_completed()
            self.connected = False

        self.client = BleakClient(device, disconnected_callback=handle_disconnect)

        await self.client.connect()

        try:
            logger.info("Connected successfully!")
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

            await self.client.start_notify(NUS_TX_UUID, self.nus_handler)
            await self.client.start_notify(
                PYBRICKS_CONTROL_UUID, self.pybricks_service_handler
            )
            self.connected = True
        except:  # noqa: E722
            self.disconnect()
            raise

    async def disconnect(self):
        if self.connected:
            logger.info("Disconnecting...")
            await self.client.disconnect()
        else:
            logger.debug("already disconnected")

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

        with self.disconnect_observable.subscribe(lambda _: disconnect_event.set()):
            done, pending = await asyncio.wait(
                {awaitable_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for t in pending:
                t.cancel()

            if awaitable_task not in done:
                raise RuntimeError("disconnected during operation")

            return awaitable_task.result()

    async def write(self, data, with_response=False):
        await self.client.write_gatt_char(NUS_RX_UUID, bytearray(data), with_response)

    async def run(self, py_path, wait=True, print_output=True):

        # Reset output buffer
        self.log_file = None
        self.output = []
        self.print_output = print_output

        # Compile the script to mpy format
        self.script_dir, _ = os.path.split(py_path)
        mpy = await compile_file(py_path)

        try:
            self.loading = True

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
            self.loading = False

        if wait:
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
                            self.race_disconnect(user_program_running.get()), 0.2
                        )
                    except asyncio.TimeoutError:
                        # if it doesn't start, assume it was a very short lived
                        # program and we just missed the status message
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
