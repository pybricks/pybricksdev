from bleak import BleakScanner, BleakClient
import asyncio
import asyncssh
import os
import logging


async def find_ble_device(name, timeout=5):
    """Quickly find BLE device address by friendly device name.

    This is an alternative to bleak.discover. Instead of waiting a long time to
    scan everything, it returns as soon as it finds any device with the
    requested name.

    Arguments:
        name (str):
            Friendly device name.
        timeout (float):
            When to give up searching.

    Returns:
        str: Matching device address.

    Raises:
        TimeoutError:
            Device was not found within the timeout.
    """

    # Flag raised by detection of a device
    device_discovered = False

    def set_device_discovered(*args):
        nonlocal device_discovered
        device_discovered = True

    # Create scanner object and register callback to raise discovery flag
    scanner = BleakScanner()
    scanner.register_detection_callback(set_device_discovered)

    # Start the scanner
    await scanner.start()

    INTERVAL = 0.1

    # Sleep until a device of interest is discovered. We cheat by using the
    # cross-platform get_discovered_devices() ahead of time, instead of waiting
    # for the whole discover() process to complete. We call it every time
    # a new device is detected by the register_detection_callback.
    for i in range(round(timeout/INTERVAL)):
        # If device_discovered flag is raised, check if it's the right one.
        if device_discovered:
            # Unset the flag so we only check if raised again.
            device_discovered = False
            # Check if any of the devices found so far has the expected name.
            devices = await scanner.get_discovered_devices()
            for dev in devices:
                # If the name matches, stop scanning and return address.
                if name == dev.name:
                    await scanner.stop()
                    return dev.address
        # Await until we check again.
        await asyncio.sleep(INTERVAL)

    # If we are here, scanning has timed out.
    await scanner.stop()
    raise TimeoutError(
        "Could not find {0} in {1} seconds".format(name, timeout)
    )


bleNusCharRXUUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
bleNusCharTXUUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'


class HubDataReceiver():

    UNKNOWN = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3
    CHECKING = 4

    def __init__(self, debug=False):
        self.buf = b''
        self.state = self.UNKNOWN
        self.reply = None

        # Get a logger
        self.logger = logging.getLogger('Hub Data')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '\t\t\t\t %(asctime)s: %(levelname)7s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Data log state
        self.log_file = None

    def process_line(self, line):
        # Decode the output
        text = line.decode()

        # Output tells us to open a log file
        if 'PB_OF' in text:
            if self.log_file is not None:
                raise OSError("Log file is already open!")
            name = text[6:]
            self.logger.info("Saving log to {0}.".format(name))
            self.log_file = open(name, 'w')
            return

        # Enf of data log file, so close it
        if 'PB_EOF' in text:
            if self.log_file is None:
                raise OSError("No log file is currently open!")
            self.logger.info("Done saving log.")
            self.log_file.close()
            self.log_file = None
            return

        # We are processing datalog, so save this line
        if self.log_file is not None:
            print(text, file=self.log_file)
            self.logger.debug(text)
            return

        # If it is not special, just print it
        print(text)

    def update_data_buffer(self, sender, data):
        # If we are transmitting, the replies are checksums
        if self.state == self.CHECKING:
            self.reply = data[-1]
            self.logger.debug("\t\t\t\tCS: {0}".format(self.reply))
            return

        # Otherwise, append incoming data to buffer
        self.buf += data

        # Break up data into lines as soon as a line is complete
        while True:
            try:
                # Try to find line break and split there
                index = self.buf.index(b'\r\n')
                line = self.buf[0:index]
                self.buf = self.buf[index+2:]

                # Check line contents to see if state needs updating
                self.logger.debug("\t\t\t\tRX: {0}".format(line))

                # If the retrieved line is a state, update it
                if self.map_state(line) is not None:
                    self.update_state(self.map_state(line))

                # Process special lines else print as human readable
                self.process_line(line)
            # Exit the loop once no more line breaks are found
            except ValueError:
                break

    def map_state(self, line):
        """"Maps state strings to states."""
        if line == b'>>>> IDLE':
            return self.IDLE
        if line == b'>>>> RUNNING':
            return self.RUNNING
        if line == b'>>>> ERROR':
            return self.ERROR
        return None

    def update_state(self, new_state):
        """Updates state if data contains state information."""
        if new_state != self.state:
            self.logger.debug("New State: {0}".format(new_state))
            self.state = new_state

    def update_state_disconnected(self, client, *args):
        self.update_state(self.UNKNOWN)
        self.logger.info("Disconnected!")

    async def wait_for_checksum(self):
        self.update_state(self.CHECKING)
        for i in range(50):
            await asyncio.sleep(0.01)
            if self.reply is not None:
                reply = self.reply
                self.reply = None
                self.update_state(self.IDLE)
                return reply
        raise TimeoutError("Hub did not return checksum")

    async def wait_until_not_running(self):
        await asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(0.1)
            if self.state != self.RUNNING:
                break


class PUPConnection(HubDataReceiver):

    async def connect(self, address):
        self.logger.info("Connecting to {0}".format(address))
        self.client = BleakClient(address)
        await self.client.connect()
        self.client.set_disconnected_callback(self.update_state_disconnected)
        self.logger.info("Connected successfully!")
        await self.client.start_notify(
            bleNusCharTXUUID, self.update_data_buffer
        )

    async def disconnect(self):
        await self.client.stop_notify(bleNusCharTXUUID)
        await self.client.disconnect()

    async def write(self, data):
        n = 20
        chunks = [data[i: i + n] for i in range(0, len(data), n)]
        for i, chunk in enumerate(chunks):
            self.logger.debug("\t\t\t\tTX: {0}".format(chunk))
            await asyncio.sleep(0.05)
            await self.client.write_gatt_char(bleNusCharRXUUID, bytearray(chunk))

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

        # Raise errors if we did not get the checksum we wanted
        if reply is None:
            raise OSError("Did not receive reply.")

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
