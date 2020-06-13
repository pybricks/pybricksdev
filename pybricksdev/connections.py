from bleak import BleakScanner
import asyncio
import asyncssh
import os


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


class EV3Connection():
    """EV3 Pybricks MicroPython SSH wrapper around asyncssh client."""

    _HOME = '/home/robot'
    _USER = 'robot'
    _PASSWORD = 'maker'

    

    async def connect(self, address):
        """Connect to EV3 or get existing connection."""

        print("Connecting to", address, "...", end=" ")
        self.client = await asyncssh.connect(
            address, username=self._USER, password=self._PASSWORD
        )
        print("Connected.", end=" ")

        self.client.sftp = await self.client.start_sftp_client()
        await self.client.sftp.chdir(self._HOME)
        print("Opened SFTP.")

    async def beep(self):
        """Runs a command on the shell and returns stdout and stderr."""
        await self.client.run('beep')

    async def disconnect(self):
        """Close the connection."""
        self.client.sftp.exit()
        self.client.close()

    async def download(self, file_path):
        # Compute paths
        dirs, file_name = os.path.split(file_path)

        # Make sure same directory structure exists on EV3
        if not await self.client.sftp.exists(os.path.join(self._HOME, dirs)):
            # If not, make the folders one by one
            total = ''
            for name in dirs.split(os.sep):
                total = os.path.join(total, name)
                if not await self.client.sftp.exists(os.path.join(self._HOME, total)):
                    await self.client.sftp.mkdir(os.path.join(self._HOME, total))

        # Send script to EV3
        remote_path = os.path.join(self._HOME, file_path)
        await self.client.sftp.put(file_path, remote_path)
        return remote_path

    async def pybricks(self, file_path):
        """Download and run a Pybricks MicroPython script."""

        # Send script to the hub
        remote_path = await self.download(file_path)

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

    async def get(self, file_path, local_path=None):
        if local_path is None:
            local_path = file_path
        await self.client.sftp.get(os.path.join(self._HOME, file_path), localpath=local_path)
