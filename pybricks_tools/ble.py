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

    IDLE = b'>>>> IDLE'
    RUNNING = b'>>>> RUNNING'
    ERROR = b'>>>> ERROR'
    UNKNOWN = None

    def __init__(self, debug=False):
        self.buf = b''
        self.state = self.UNKNOWN

        # Get a logger
        self.logger = logging.getLogger('Hub Data')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '\t\t\t\t\t\t %(asctime)s: %(levelname)7s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def update_data_buffer(self, sender, data):
        # Append incoming data to buffer
        self.buf += data

        # Break up data into lines as soon as a line is complete
        while True:
            try:
                # Try to find line break and split there
                index = self.buf.index(b'\r\n')
                line = self.buf[0:index]
                self.buf = self.buf[index+2:]

                # Check line contents to see if state needs updating
                self.logger.debug("New Data: {0}".format(line))
                self.update_state(line)

                # Print the line that has been received
                print(line.decode())
            # Exit the loop once no more line breaks are found
            except ValueError:
                break

    def update_state(self, line):
        """Update state if data contains state information."""
        if line in (self.IDLE, self.RUNNING, self.ERROR):
            if line != self.state:
                self.logger.debug("New State: {0}".format(line))
                self.state = line

    def update_state_disconnected(self, client, *args):
        self.state = self.UNKNOWN
        self.logger.info("Disconnected!")


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
        self.logger.debug("Sending {0}".format(data))
        await self.client.write_gatt_char(bleNusCharRXUUID, data)

    async def wait_for_response(self, previous_length):
        for i in range(20):
            await asyncio.sleep(0.05)
            if len(self.buf) > previous_length:
                return self.buf[-1]
        raise TimeoutError("Hub did not return checksum")

    async def send_message(self, data):
        """Send bytes to the hub, and check if reply matches checksum."""

        # Initial checksum
        checksum = 0

        # Send data
        buf_length_start = len(self.buf)

        n = 20
        chunks = [data[i : i + n] for i in range(0, len(data), n)]
        for chunk in chunks:
            await self.write(chunk)
            await asyncio.sleep(0.1)

        reply = await self.wait_for_response(buf_length_start)

        # Compute expected reply
        for b in data:
            checksum ^= b

        reply = self.buf[-1]
        self.logger.debug("expected: {0}, reply: {1}".format(reply, checksum))

        # Raise errors if we did not get the checksum we wanted
        if not reply:
            raise OSError("Did not receive reply.")

        if checksum != reply:
            raise ValueError("Did not receive expected checksum.")

    async def wait_for_completion(self):
        asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(0.1)
            if self.state != self.RUNNING:
                break


async def main(mpy):
    async with PybricksHubConnection(debug=True) as hub:
        await asyncio.sleep(2.0)

        length = len(mpy).to_bytes(4, byteorder='little')
        await hub.send_message(length)

        n = 100
        chunks = [mpy[i: i + n] for i in range(0, len(mpy), n)]

        # Send the data
        for chunk in chunks:
            await hub.send_message(chunk)

        await hub.wait_for_completion()

if __name__ == "__main__":

    # Parse all arguments
    parser = get_mpy_arg_parser(
        description="Run Pybricks MicroPython scripts via BLE."
    )
    args = parser.parse_args()

    # Use arguments to produce mpy bytes
    data = get_mpy_bytes(args)

    asyncio.run(main(data))
