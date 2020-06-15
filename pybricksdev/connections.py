import asyncio
import asyncssh
import os
from pybricksdev.ble import BLEStreamConnection
from pybricksdev.compile import compile_file


class PUPConnection(BLEStreamConnection):
    """Connect to Pybricks Hubs and run MicroPython scripts."""

    UNKNOWN = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3
    AWAITING_CHECKSUM = 4

    CharRXUUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
    CharTXUUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

    def __init__(self):
        """Initialize the BLE Connection with settings for Pybricks service."""
        self.state = self.UNKNOWN
        self.checksum = None
        self.checksum_ready = asyncio.Event()
        super().__init__(self.CharRXUUID, self.CharTXUUID, 20, b'\r\n')

    def char_handler(self, char):
        """Handles new incoming characters.

        This overrides the same method from BLEStreamConnection to change what
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
            self.checksum_ready.clear()
            self.logger.debug("RX CHECKSUM: {0}".format(char))
            return None
        else:
            # Otherwise, return it so it gets added to standard output buffer.
            return char

    def line_handler(self, line):
        """Handles new incoming lines.

        This overrides the same method from BLEStreamConnection to change what
        we do with lines. In this application, we check if the line equals a
        state change message. Otherwise, we just print it.

        Arguments:
            line (bytearray):
                Line to process.
        """

        # If the line tells us about the state, set the state and be done.
        if line == b'>>>> IDLE':
            self.set_state(self.IDLE)
            return
        if line == b'>>>> RUNNING':
            self.set_state(self.RUNNING)
            return
        if line == b'>>>> ERROR':
            self.set_state(self.ERROR)
            return

        # If there is nothing special about this line, print it.
        print(line.decode())

    def disconnected_handler(self, client, *args):
        """Processes external disconnection event.

        This overrides the same method from BLEStreamConnection to change what
        we do when the connection is broken. Here, we just set the state.
        """
        self.set_state(self.UNKNOWN)
        self.logger.info("Disconnected by server.")

    def set_state(self, new_state):
        """Updates state if it is new.

        Arguments:
            new_state (int):
                New state
        """
        if new_state != self.state:
            self.logger.debug("New State: {0}".format(new_state))
            self.state = new_state

    async def wait_for_checksum(self):
        """Awaits and returns a checksum character.

        Returns:
            int: checksum character
        """
        self.set_state(self.AWAITING_CHECKSUM)
        await asyncio.wait_for(self.checksum_ready.wait(), timeout=0.5)
        result = self.checksum
        self.checksum = None
        self.set_state(self.IDLE)
        return result

    async def wait_until_not_running(self):
        """Awaits until the script is no longer running."""
        await asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(0.1)
            if self.state != self.RUNNING:
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

        # Send the data
        await self.write(data)

        # Await the reply
        reply = await self.wait_for_checksum()
        self.logger.debug("expected: {0}, reply: {1}".format(checksum, reply))

        # Check the response
        if checksum != reply:
            raise ValueError("Did not receive expected checksum.")

    async def run(self, py_path, mpy_cross_path=None):
        """Run a Pybricks MicroPython script on the hub and print output.

        Arguments:
            py_path (str):
                Path to MicroPython script.
            mpy_cross_path (str):
                Path to mpy-cross. Choose None to use default from package.
        """
        # Compile the script to mpy format
        mpy = await compile_file(py_path, mpy_cross_path)

        # Get length of file and send it as bytes to hub
        length = len(mpy).to_bytes(4, byteorder='little')
        await self.send_message(length)

        # Divide script in chunks of bytes
        n = 100
        chunks = [mpy[i: i + n] for i in range(0, len(mpy), n)]

        # Send the data chunk by chunk
        for i, chunk in enumerate(chunks):
            self.logger.info("Sending: {0}%".format(
                round((i+1)/len(chunks)*100))
            )
            await self.send_message(chunk)

        # Wait for the program to finish
        await self.wait_until_not_running()


class ExtendedPUPConnection(PUPConnection):
    """Connect to Pybricks Hubs and run MicroPython scripts.

    This extends the BasePUPConnection with experimental line parses that
    allow users to let the hub interact with the PC.
    """

    def __init__(self):
        self.log_file = None
        super().__init__()

    def line_handler(self, line):
        """Handles new incoming lines.

        This overrides the same method from BasicPUPConnection to add
        file saving functionality. If no special datalog line is detected,
        it calls the default line handler.

        Arguments:
            line (bytearray):
                Line to process.
        """
        # The line tells us to open a log file, so do it.
        if b'PB_OF' in line:
            if self.log_file is not None:
                raise OSError("Log file is already open!")
            name = line[6:].decode()
            self.logger.info("Saving log to {0}.".format(name))
            self.log_file = open(name, 'w')
            return

        # The line tells us to close a log file, so do it.
        if b'PB_EOF' in line:
            if self.log_file is None:
                raise OSError("No log file is currently open!")
            self.logger.info("Done saving log.")
            self.log_file.close()
            self.log_file = None
            return

        # If we are processing datalog, save current line to the open file.
        if self.log_file is not None:
            print(line.decode(), file=self.log_file)
            return

        # We don't want to do anything special with this line, so call
        # the handler from the parent class to deal with it.
        super().line_handler(line)


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

    async def run(self, local_path):
        """Downloads and runs a Pybricks MicroPython script.

        Arguments:
            local_path (str):
                Path to the file to be downloaded. Relative to current working
                directory. This same tree will be created on the EV3 if it
                does not already exist.
        """

        # Send script to the hub
        remote_path = await self.download(local_path)

        # Run it and return stderr to get Pybricks MicroPython output
        print("Now starting:", remote_path)
        prog = 'brickrun -r -- pybricks-micropython {0}'.format(remote_path)

        # Run process asynchronously and print output as it comes in
        async with self.client.create_process(prog) as process:
            # Keep going until the process is done
            while process.exit_status is None:
                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(), timeout=0.1
                    )
                    print(line.strip())
                except asyncio.exceptions.TimeoutError:
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
