# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

import asyncio
import base64
import json
import logging
import os
import random

import asyncssh
from bleak.backends.device import BLEDevice
from bleak import BleakClient
import semver
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from .ble import BLEConnection
from .compile import compile_file
from .usbconnection import USBConnection

logger = logging.getLogger(__name__)


class CharacterGlue():
    """Glues incoming bytes into a buffer and splits it into lines."""

    def __init__(self, EOL, **kwargs):
        """Initialize the buffer.

        Arguments:
            EOL (bytes):
                Character sequence that signifies end of line.

        """
        self.EOL = EOL

        # Create empty rx buffer
        self.char_buf = bytearray(b'')

        super().__init__(**kwargs)

    def char_handler(self, char):
        """Handles new incoming characters.

        Arguments:
            char (int):
                Character/byte to process.

        Returns:
            int or None: Processed character.

        """
        logger.debug("RX CHAR: {0} ({1})".format(chr(char), char))
        return char

    def line_handler(self, line):
        """Handles new incoming lines.

        The default just prints the line that comes in.

        Arguments:
            line (bytearray):
                Line to process.
        """
        print(line)

    def data_handler(self, sender, data):
        """Handles new incoming data. Calls char and line parsers when ready.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytearray):
                Incoming data.
        """
        logger.debug("RX DATA: {0}".format(data))

        # For each new character, call its handler and add to buffer if any
        for byte in data:
            append = self.char_handler(byte)
            if append is not None:
                self.char_buf.append(append)

        # Some applications don't have any lines to process
        if self.EOL is None:
            return

        # Break up data into lines and take those out of the buffer
        lines = []
        while True:
            # Find and split at end of line
            index = self.char_buf.find(self.EOL)
            # If no more line end is found, we are done
            if index < 0:
                break
            # If we found a line, save it, and take it from the buffer
            lines.append(self.char_buf[0:index])
            del self.char_buf[0:index+len(self.EOL)]

        # Call handler for each line that we found
        for line in lines:
            self.line_handler(line)


class PybricksPUPProtocol(CharacterGlue):
    """Parse and send data to make Pybricks Hubs run MicroPython scripts."""

    UNKNOWN = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3
    AWAITING_CHECKSUM = 4

    def __init__(self, **kwargs):
        """Initialize the protocol state."""
        self.state = self.UNKNOWN
        self.checksum = None
        self.checksum_ready = asyncio.Event()
        self.log_file = None
        self.output = []
        super().__init__(EOL=b'\r\n', **kwargs)

    def char_handler(self, char):
        """Handles new incoming characters.

        This overrides the same method from CharacterGlue to change what
        we do with individual incoming characters/bytes.

        If we are awaiting the checksum, it raises the event to say the
        checksum has arrived. Otherwise, it just returns the character as-is
        so it can be added to standard output.

        Arguments:
            char (int):
                Character/byte to process

        Returns:
            int or None: The same character or None if the checksum stole it.
        """
        if self.state == self.AWAITING_CHECKSUM:
            # If we are awaiting on a checksum, this is that byte. So,
            # don't add it to the buffer but tell checksum awaiter that we
            # are ready to process it.
            self.checksum = char
            self.checksum_ready.set()
            logger.debug("RX CHECKSUM: {0}".format(char))
            return None
        else:
            # Otherwise, return it so it gets added to standard output buffer.
            return char

    def line_handler(self, line):
        """Handles new incoming lines. Handle special actions if needed,
        otherwise just print it as regular lines.

        Arguments:
            line (bytearray):
                Line to process.
        """
        # The line tells us to open a log file, so do it.
        if b'PB_OF' in line:
            if self.log_file is not None:
                raise RuntimeError("Log file is already open!")
            name = line[6:].decode()
            logger.info("Saving log to {0}.".format(name))
            self.log_file = open(name, 'w')
            return

        # The line tells us to close a log file, so do it.
        if b'PB_EOF' in line:
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

    def set_state(self, new_state):
        """Updates state if it is new.

        Arguments:
            new_state (int):
                New state
        """
        if new_state != self.state:
            logger.debug("New State: {0}".format(new_state))
            self.state = new_state

    def prepare_checksum(self):
        """Prepare state to start receiving checksum."""
        self.set_state(self.AWAITING_CHECKSUM)
        self.checksum = None
        self.checksum_ready.clear()

    async def wait_for_checksum(self):
        """Awaits and returns a checksum character.

        Returns:
            int: checksum character
        """
        await asyncio.wait_for(self.checksum_ready.wait(), timeout=0.5)
        result = self.checksum
        self.prepare_checksum()
        self.set_state(self.IDLE)
        return result

    async def wait_until_state_is_not(self, state):
        """Awaits until the requested state is no longer active."""
        # FIXME: handle using event on state change
        while True:
            await asyncio.sleep(0.1)
            if self.state != state:
                break

    async def send_message(self, data):
        """Send bytes to the hub, and check if reply matches checksum.

        Arguments:
            data (bytearray):
                Data to write. At most 100 bytes.

        Raises:
            ValueError:
                Did not receive expected checksum for this message.
        """

        if len(data) > 100:
            raise ValueError("Cannot send this much data at once")

        # Compute expected reply
        checksum = 0
        for b in data:
            checksum ^= b

        # Clear existing checksum
        self.prepare_checksum()

        # Send the data
        await self.write(data)

        # Await the reply
        reply = await self.wait_for_checksum()
        logger.debug("expected: {0}, reply: {1}".format(checksum, reply))

        # Check the response
        if checksum != reply:
            raise ValueError(
                "Expected checksum {0} but received {1}.".format(
                    checksum, reply
                )
            )

    async def run(self, py_path, wait=True, print_output=True):
        """Run a Pybricks MicroPython script on the hub and print output.

        Arguments:
            py_path (str):
                Path to MicroPython script.
            wait (bool):
                Whether to wait for any output until the program completes.
            print_output(bool):
                Whether to print the standard output.
        """

        # Reset output buffer
        self.log_file = None
        self.output = []
        self.print_output = print_output

        # Compile the script to mpy format
        mpy = await compile_file(py_path)

        # Get length of file and send it as bytes to hub
        length = len(mpy).to_bytes(4, byteorder='little')
        await self.send_message(length)

        # Divide script in chunks of bytes
        n = 100
        chunks = [mpy[i: i + n] for i in range(0, len(mpy), n)]

        # Send the data chunk by chunk
        with logging_redirect_tqdm(), tqdm(total=len(mpy), unit='B', unit_scale=True) as pbar:
            for chunk in chunks:
                await self.send_message(chunk)
                pbar.update(len(chunk))

        # Optionally wait for the program to finish
        if wait:
            await asyncio.sleep(0.2)
            await self.wait_until_state_is_not(self.RUNNING)


class BLEPUPConnection(PybricksPUPProtocol, BLEConnection):

    def __init__(self):
        """Initialize the BLE Connection with settings for Pybricks service."""

        super().__init__(
            char_rx_UUID='6e400002-b5a3-f393-e0a9-e50e24dcca9e',
            char_tx_UUID='6e400003-b5a3-f393-e0a9-e50e24dcca9e',
            max_data_size=20
        )


class USBPUPConnection(PybricksPUPProtocol, USBConnection):

    def __init__(self):
        """Initialize."""

        super().__init__()


class USBRPCConnection(CharacterGlue, USBConnection):

    def __init__(self, **kwargs):
        self.m_data = [{}] * 20
        self.i_data = []
        self.log_file = None
        super().__init__(EOL=b'\r', **kwargs)

    def user_line_handler(self, line):

        if 'PB_OF' in line:
            if self.log_file is not None:
                raise RuntimeError("Log file is already open!")
            name = line[6:]
            logger.info("Saving log to {0}.".format(name))
            self.log_file = open(name, 'w')
            return

        if 'PB_EOF' in line:
            if self.log_file is None:
                raise RuntimeError("No log file is currently open!")
            logger.info("Done saving log.")
            self.log_file.close()
            self.log_file = None
            return

        if self.log_file is not None:
            print(line, file=self.log_file)
            return

        print(line)

    def line_handler(self, line):
        try:
            data = json.loads(line)
            if 'e' in data:
                print(base64.b64decode(data['e']))
            elif 'm' in data:
                if type(data['m']) == int:
                    self.m_data[data['m']] = data
                elif data['m'] == 'runtime_error':
                    print(base64.b64decode(data['p'][3]))
                elif data['m'] == 'userProgram.print':
                    self.user_line_handler(base64.b64decode(data['p']['value']).decode('ascii').strip())
                else:
                    print("unknown", data)
            else:
                self.i_data.append(data)
        except json.JSONDecodeError:
            pass

    async def send_dict(self, command):
        await self.write(json.dumps(command).encode('ascii') + b'\r')

    async def send_command(self, message, payload):

        data_id = ''
        for i in range(4):
            c = chr(random.randint(ord('A'), ord('Z')))
            data_id += c

        data = {
            'i': data_id,
            'm': message,
            'p': payload
        }

        await self.send_dict(data)
        return data_id

    async def send_command_and_get_response(self, message, payload):

        data_id = await self.send_command(message, payload)
        response = None

        for i in range(30):

            while len(self.i_data) > 0:
                data = self.i_data.pop(0)
                if data['i'] == data_id:
                    response = data
                    break

            if response is not None:
                return response['r']
            else:
                await asyncio.sleep(0.1)

    async def run(self, py_path, wait=False):
        response = await self.send_command_and_get_response("program_modechange", {
                "mode": "download"
            })

        with open(py_path, 'rb') as demo:
            program = demo.read()

        chunk_size = 512
        chunks = [program[i:i+chunk_size] for i in range(0, len(program), chunk_size)]

        while response is None or 'transferid' not in response:
            response = await self.send_command_and_get_response("start_write_program", {
                        "meta": {
                            "created": 0,
                            "modified": 0,
                            "project_id": "Pybricksdev_",
                            "project_id": "Pybricksdev_",
                            "name": "Pybricksdev_____",
                            "type": "python"
                        },
                        "size": len(program),
                        "slotid": 0
                    })
        transferid = response['transferid']

        with logging_redirect_tqdm(), tqdm(total=len(program), unit='B', unit_scale=True) as pbar:
            for chunk in chunks:
                response = await self.send_command_and_get_response("write_package", {
                            "data": base64.b64encode(chunk).decode('ascii'),
                            "transferid": transferid
                        })
                pbar.update(len(chunk))

        await asyncio.sleep(0.5)
        response = await self.send_command_and_get_response("program_execute", {
                    "slotid": 0
                })
        print(response)


class EV3Connection():
    """ev3dev SSH connection for running pybricks-micropython scripts.

    This wraps convenience functions around the asyncssh client.
    """

    _HOME = '/home/robot'
    _USER = 'robot'
    _PASSWORD = 'maker'

    def abs_path(self, path):
        return os.path.join(self._HOME, path)

    async def connect(self, address):
        """Connects to ev3dev using SSH with a known IP address.

        Arguments:
            address (str):
                IP address of the EV3 brick running ev3dev.

        Raises:
            OSError:
                Connect failed.
        """

        print("Connecting to", address, "...", end=" ")
        self.client = await asyncssh.connect(
            address, username=self._USER, password=self._PASSWORD
        )
        print("Connected.", end=" ")
        self.client.sftp = await self.client.start_sftp_client()
        await self.client.sftp.chdir(self._HOME)
        print("Opened SFTP.")

    async def beep(self):
        """Makes the EV3 beep."""
        await self.client.run('beep')

    async def disconnect(self):
        """Closes the connection."""
        self.client.sftp.exit()
        self.client.close()

    async def download(self, local_path):
        """Downloads a file to the EV3 Brick using sftp.

        Arguments:
            local_path (str):
                Path to the file to be downloaded. Relative to current working
                directory. This same tree will be created on the EV3 if it
                does not already exist.
        """
        # Compute paths
        dirs, file_name = os.path.split(local_path)

        # Make sure same directory structure exists on EV3
        if not await self.client.sftp.exists(self.abs_path(dirs)):
            # If not, make the folders one by one
            total = ''
            for name in dirs.split(os.sep):
                total = os.path.join(total, name)
                if not await self.client.sftp.exists(self.abs_path(total)):
                    await self.client.sftp.mkdir(self.abs_path(total))

        # Send script to EV3
        remote_path = self.abs_path(local_path)
        await self.client.sftp.put(local_path, remote_path)
        return remote_path

    async def run(self, local_path, wait=True):
        """Downloads and runs a Pybricks MicroPython script.

        Arguments:
            local_path (str):
                Path to the file to be downloaded. Relative to current working
                directory. This same tree will be created on the EV3 if it
                does not already exist.
            wait (bool):
                Whether to wait for any output until the program completes.
        """

        # Send script to the hub
        remote_path = await self.download(local_path)

        # Run it and return stderr to get Pybricks MicroPython output
        print("Now starting:", remote_path)
        prog = 'brickrun -r -- pybricks-micropython {0}'.format(remote_path)

        # Run process asynchronously and print output as it comes in
        async with self.client.create_process(prog) as process:
            # Keep going until the process is done
            while process.exit_status is None and wait:
                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(), timeout=0.1
                    )
                    print(line.strip())
                except asyncio.TimeoutError:
                    pass

    async def get(self, remote_path, local_path=None):
        """Gets a file from the EV3 over sftp.

        Arguments:
            remote_path (str):
                Path to the file to be fetched. Relative to ev3 home directory.
            local_path (str):
                Path to save the file. Defaults to same as remote_path.
        """
        if local_path is None:
            local_path = remote_path
        await self.client.sftp.get(
            self.abs_path(remote_path), localpath=local_path
        )


# Pybricks control characteristic UUID
PYBRICKS_UUID = 'c5f50002-8280-46da-89f4-6d8051e4aeef'
# The minimum required Pybricks protocol version
PYBRICKS_PROTOCOL_VERSION = semver.VersionInfo(1)

# Standard Device Information Service UUID
DI_SERVICE_UUID = '0000180a-0000-1000-8000-00805f9b34fb'
# Standard Firmware Revision String characteristic UUID
FW_REV_UUID = '00002a26-0000-1000-8000-00805f9b34fb'
# Standard Software Revision String UUID (Pybricks protocol version)
SW_REV_UUID = '00002a28-0000-1000-8000-00805f9b34fb'

# Nordic UART hub Rx, pybricksdev Tx characteristic
NUS_RX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
# Nordic UART hub Tx, pybricksdev Rx characteristic
NUS_TX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'


class PybricksHub:
    EOL = b"\r\n"  # MicroPython EOL

    def __init__(self):
        self.stream_buf = bytearray()
        self.output = []
        self.print_output = True

        # indicates that the hub is currently connected via BLE
        self.connected = False

        # stores the next expected checksum or -1 when not expecting a checksum
        self.expected_checksum = -1
        # indicates when a valid checksum was received
        self.checksum_ready = asyncio.Event()

        # indicates is we are currently downloading a program
        self.loading = False
        # indicates that the user program is running
        self.program_running = False
        # used to notify when the user program has ended
        self.user_program_stopped = asyncio.Event()

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
        if b'PB_OF' in line:
            if self.log_file is not None:
                raise RuntimeError("Log file is already open!")

            # Get path relative to running script, so log will go
            # in the same folder unless specified otherwise.
            full_path = os.path.join(self.script_dir, line[6:].decode())
            dir_path, _ = os.path.split(full_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            logger.info("Saving log to {0}.".format(full_path))
            self.log_file = open(full_path, 'w')
            return

        # The line tells us to close a log file, so do it.
        if b'PB_EOF' in line:
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
        # If we are currently expecting a checksum, validate it and notify the waiter
        if self.expected_checksum != -1:
            checksum = data[0]
            if checksum != self.expected_checksum:
                raise RuntimeError(
                    f"Expected checksum {self.expected_checksum} but got {checksum}"
                )

            self.expected_checksum = -1
            self.checksum_ready.set()
            logger.debug(f"Correct checksum: {checksum}")
            return

        # Store incoming data
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
            del self.stream_buf[0:index+len(self.EOL)]

        # Call handler for each line that we found
        for line in lines:
            self.line_handler(line)

    def pybricks_service_handler(self, _: int, data: bytearray):
        if data[0] == 0:

            # Get new state
            msg = data[1]

            # Get new program state
            program_running_now = bool(msg & (1 << 6))

            # If we are currently downloading a program, we must ignore user
            # program running state changes, otherwise the checksum will be
            # sent to the terminal instead of being handled by the download
            # algorithm
            if not self.loading:
                if self.program_running != program_running_now:
                    logger.info(f"Program running: {program_running_now}")
                    self.program_running = program_running_now
                if not program_running_now:
                    self.user_program_stopped.set()

    async def connect(self, device: BLEDevice):
        """Connects to a device that was discovered with :meth:`pybricksdev.ble.find_device`

        Args:
            device: The device to connect to.

        Raises:
            BleakError: if connecting failed (or old firmware without Device
                Information Service)
            RuntimeError: if Pybricks Protocol version is not supported
        """
        logger.info(f"Connecting to {device.address}")
        self.client = BleakClient(device)

        def disconnected_handler(self, _: BleakClient):
            logger.info("Disconnected!")
            self.connected = False

        await self.client.connect(disconnected_callback=disconnected_handler)
        try:
            logger.info("Connected successfully!")
            protocol_version = await self.client.read_gatt_char(SW_REV_UUID)
            protocol_version = semver.VersionInfo.parse(protocol_version.decode())
            if (
                protocol_version < PYBRICKS_PROTOCOL_VERSION or
                protocol_version >= PYBRICKS_PROTOCOL_VERSION.bump_major()
            ):
                raise RuntimeError(f"Unsupported Pybricks protocol version: {protocol_version}")
            await self.client.start_notify(NUS_TX_UUID, self.nus_handler)
            await self.client.start_notify(PYBRICKS_UUID, self.pybricks_service_handler)
            self.connected = True
        except:
            self.disconnect()
            raise

    async def disconnect(self):
        if self.connected:
            logger.info("Disconnecting...")
            await self.client.disconnect()
        else:
            logger.debug("already disconnected")

    def get_checksum(self, block):
        checksum = 0
        for b in block:
            checksum ^= b
        return checksum

    async def send_block(self, data):
        self.checksum_ready.clear()
        self.expected_checksum = self.get_checksum(data)
        try:
            await self.client.write_gatt_char(NUS_RX_UUID, bytearray(data), False)
            await asyncio.wait_for(self.checksum_ready.wait(), timeout=0.5)
        except:
            # normally self.expected_checksum = -1 will be called in nus_handler()
            # but if we timeout or something like that, we need to reset it here
            self.expected_checksum = -1
            raise

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
            self.user_program_stopped.clear()

            # Get length of file and send it as bytes to hub
            length = len(mpy).to_bytes(4, byteorder='little')
            await self.send_block(length)

            # Divide script in chunks of bytes
            n = 100
            chunks = [mpy[i: i + n] for i in range(0, len(mpy), n)]

            # Send the data chunk by chunk
            with logging_redirect_tqdm(), tqdm(total=len(mpy), unit='B', unit_scale=True) as pbar:
                for chunk in chunks:
                    await self.send_block(chunk)
                    pbar.update(len(chunk))
        finally:
            self.loading = False

        if wait:
            await self.user_program_stopped.wait()
            await asyncio.sleep(0.3)
