from bleak import BleakScanner, BleakClient
from asyncio import sleep
import logging


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
    print("Searching for {0}".format(name))

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

    def __init__(self, char_rx_UUID, char_tx_UUID, mtu, EOL):
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
        # Save given settings
        self.char_rx_UUID = char_rx_UUID
        self.char_tx_UUID = char_tx_UUID
        self.EOL = EOL
        self.mtu = mtu

        # Create empty rx buffer
        self.char_buf = bytearray(b'')

        # Get a logger and set at given level
        self.logger = logging.getLogger('BLEStreamConnection')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s: %(levelname)7s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.WARNING)

    def char_handler(self, char):
        """Handles new incoming characters. Intended to be overridden.

        Arguments:
            char (int):
                Character/byte to process.

        Returns:
            int or None: Processed character.

        """
        self.logger.debug("RX CHAR: {0} ({1})".format(chr(char), char))
        return char

    def line_handler(self, line):
        """Handles new incoming lines. Intended to be overridden.

        The default just prints the line that comes in.

        Arguments:
            line (bytearray):
                Line to process.
        """
        print(line)

    def disconnected_handler(self, client, *args):
        """Handles disconnected event. Intended to be overridden."""
        self.logger.info("Disconnected by server.")

    def _data_handler(self, sender, data):
        """Handles new incoming data. Calls char and line parsers when ready.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytearray):
                Incoming data.
        """
        self.logger.debug("RX DATA: {0}".format(data))

        # For each new character, call its handler and add to buffer if any
        for byte in data:
            append = self.char_handler(byte)
            if append is not None:
                self.char_buf.append(append)

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
        self.logger.debug("Disconnecting...")
        await self.client.disconnect()  # FIXME: handle already disconnected
        self.logger.info("Disconnected by client.")

    async def write(self, data, pause=0.05):
        """Write bytes to the server, split to chunks of maximum mtu size.

        Arguments:
            data (bytearray):
                Data to be sent to the server.
            pause (float):
                Time between chunks of data.
        """
        # Chop data into chunks of maximum tranmission size
        chunks = [data[i: i + self.mtu] for i in range(0, len(data), self.mtu)]

        # Send the chunks one by one
        for chunk in chunks:
            self.logger.debug("TX CHUNK: {0}".format(chunk))
            # Send one chunk
            await self.client.write_gatt_char(self.char_rx_UUID, chunk)
            # Give server some time to process chunk
            await sleep(pause)
