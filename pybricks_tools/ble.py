# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import asyncio
from bleak import BleakClient, BleakScanner
import logging

from pybricks_tools.mpy import get_mpy_arg_parser, get_mpy_bytes

bleNusCharRXUUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
bleNusCharTXUUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'


async def scan_and_get_address(device_name, timeout=5):
    """Scan for device by name and return address of first match."""
    # To do: search by service instead."""

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

    # Sleep until a device of interest is discovered
    # It would be nice to use a filter, but this hack
    # is a simple way to keep it cross platform.
    for i in range(round(timeout/INTERVAL)):
        # If device_discovered flag is raised, check if it's the right one.
        if device_discovered:
            # Unset the flag so we only check if raised again.
            device_discovered = False
            # Check if any of the devices found so far has the expected name.
            devices = await scanner.get_discovered_devices()
            for dev in devices:
                # If the name matches, stop scanning and return address.
                if device_name in dev.name:
                    await scanner.stop()
                    return dev.address
        # Await until we check again.
        await asyncio.sleep(INTERVAL)

    # If we are here, scanning has timed out.
    await scanner.stop()
    raise TimeoutError(
        "Could not find {0} in {1} seconds".format(device_name, timeout)
    )


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

                # Print the line that has been received as human readable
                print(line.decode())
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


class PybricksHubConnection(HubDataReceiver):

    async def connect(self):
        self.logger.info("Scanning for Pybricks Hub")
        address = await scan_and_get_address('Pybricks Hub', timeout=5)

        self.logger.info("Found {0}!".format(address))
        self.logger.info("Connecting...")
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

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def write(self, data):
        self.logger.debug("\t\t\t\tTX: {0}".format(data))
        await self.client.write_gatt_char(bleNusCharRXUUID, data)

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
            print(round(i/len(chunks)*100))
            await self.send_message(chunk)

        # Wait for the program to finish
        await self.wait_until_not_running()


if __name__ == "__main__":
    # Parse all arguments
    parser = get_mpy_arg_parser(
        description="Run Pybricks MicroPython scripts via BLE."
    )
    args = parser.parse_args()

    # Use arguments to produce mpy bytes
    data = get_mpy_bytes(args)

    async def main(mpy):
        async with PybricksHubConnection(debug=False) as hub:
            await hub.download_and_run(mpy)

    # Asynchronously send and run the script
    asyncio.run(main(data))
