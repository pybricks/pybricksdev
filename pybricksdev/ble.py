from bleak import BleakScanner, BleakClient
from asyncio import sleep


async def find_device(name, timeout=5):
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
        await sleep(INTERVAL)

    # If we are here, scanning has timed out.
    await scanner.stop()
    raise TimeoutError(
        "Could not find {0} in {1} seconds".format(name, timeout)
    )


class BLEStreamConnection():

    def __init__(self, char_rx_UUID, char_tx_UUID, mtu, EOL=b'\r\n'):
        """Initializes and configures connection settings.

        Arguments:
            char_rx_UUID (str):
                UUID for RX.
            char_rx_UUID (str):
                UUID for TX.
            mtr (int):
                Maximum number of bytes per write operation.
            EOL (bytes):
                Character sequence that signifies end of line.

        """
        self.char_rx_UUID = char_rx_UUID
        self.char_tx_UUID = char_tx_UUID
        self.EOL = EOL
        self.mtu = mtu
        self.char_buf = bytearray(b'')

    def char_handler(self, char):
        """Handles new incoming characters. Intended to be overridden.

        Arguments:
            char (int):
                Character/byte to process
        """
        pass

    def line_handler(self, line):
        """Handles new incoming lines. Intended to be overridden.

        The default just prints the line that comes in.

        Arguments:
            line (bytearray):
                Line to process.
        """
        print(line)

    def disconnected_handler(self, client, *args):
        """Handles disconnected event.  Intended to be overridden."""
        print("Disconnected")

    def _data_handler(self, sender, data):
        """Handles new incoming data. Calls char and line parsers when needed.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytearray):
                Incoming data.
        """

        # Append all new characters to buffer
        self.char_buf += data

        # For each new character, call its handler
        for b in data:
            self.char_handler(b)

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

    async def connect(self, address):
        """Creates connection to server at given address.

        Arguments:
            address (str):
                Client address
        """

        print("Connecting to {0}".format(address))
        self.client = BleakClient(address)
        await self.client.connect()
        self.client.set_disconnected_callback(self.disconnected_handler)
        await self.client.start_notify(self.char_tx_UUID, self._data_handler)
        print("Connected successfully!")

    async def disconnect(self):
        """Disconnects the client from the server."""
        await self.client.stop_notify(self.char_tx_UUID)
        await self.client.disconnect()

    async def write(self, data):
        """Write bytes to the server, split to chunks of maximum mtu size.

        Arguments:
            data (bytearray):
                Data to be sent to the server.
        """
        chunks = [data[i: i + self.mtu] for i in range(0, len(data), self.mtu)]
        for i, chunk in enumerate(chunks):
            print("TX: {0}".format(chunk))
            await sleep(0.05)
            await self.client.write_gatt_char(self.char_rx_UUID, chunk)
