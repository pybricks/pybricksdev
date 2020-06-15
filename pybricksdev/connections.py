from bleak import BleakClient
import asyncio
import asyncssh
import os
import logging
from pybricksdev.ble import BLEStreamConnection


bleNusCharRXUUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
bleNusCharTXUUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'


class BasicPUPConnection(BLEStreamConnection):

    UNKNOWN = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3
    AWAITING_CHECKSUM = 4

    def __init__(self):
        self.state = self.UNKNOWN
        self.checksum = None
        self.checksum_ready = asyncio.Event()
        super().__init__(bleNusCharRXUUID, bleNusCharTXUUID, 20, b'\r\n')

    def update_state(self, new_state):
        """Updates state if data contains state information."""
        if new_state != self.state:
            self.logger.debug("New State: {0}".format(new_state))
            self.state = new_state

    def line_handler(self, line):

        # If the line tells us about the state, set the state and be done.
        if line == b'>>>> IDLE':
            self.update_state(self.IDLE)
            return
        if line == b'>>>> RUNNING':
            self.update_state(self.RUNNING)
            return
        if line == b'>>>> ERROR':
            self.update_state(self.ERROR)
            return

        # If there is nothing special about this line, print it.
        print(line.decode())

    def char_handler(self, char):
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
            # Otherwise, return it so it gets added to standard output buffer
            return char

    def disconnected_handler(self, client, *args):
        self.update_state(self.UNKNOWN)
        self.logger.info("Disconnected by server.")

    async def wait_for_checksum(self):
        self.update_state(self.AWAITING_CHECKSUM)
        await asyncio.wait_for(self.checksum_ready.wait(), timeout=0.5)
        result = self.checksum
        self.checksum = None
        self.update_state(self.IDLE)
        return result

    async def wait_until_not_running(self):
        await asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(0.1)
            if self.state != self.RUNNING:
                break

    async def send_message(self, data):
        """Send bytes to the hub, and check if reply matches checksum."""

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

        if checksum != reply:
            raise ValueError("Did not receive expected checksum.")

    async def download_and_run(self, mpy):
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


class PUPConnection(BasicPUPConnection):

    def __init__(self):
        self.log_file = None
        super().__init__()

    def line_handler(self, line):

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
