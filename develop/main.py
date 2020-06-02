
import asyncio
from bleak import BleakClient, BleakScanner

bleNusCharRXUUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
bleNusCharTXUUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

# Scan for a device with the given name and return address of first match.
# To do: search by service instead.
async def scan_and_get_address(device_name, timeout=5):

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


def test_callback(client, *args):
    print("Disconnected", client.address)


class HubBuffer():

    IDLE = b'>>>> IDLE'
    RUNNING = b'>>>> RUNNING'
    ERROR = b'>>>> ERROR'

    def __init__(self):
        self.buf = b''
        self.state = self.IDLE

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
                self.update_state(line)

                # Print the line that has been received
                print(line.decode())

            except ValueError:
                break

    def update_state(self, line):
        if line in (self.IDLE, self.RUNNING, self.ERROR):
            self.state = line


# Main function, to be replaced with an argparser
async def main():
    # Scan for a Pybricks Hub
    address = await scan_and_get_address('Pybricks Hub', timeout=5)
    print("Found", address)

    print("Connecting...")

    # Connect to detected device and start listening for its output
    async with BleakClient(address) as client:
        client.set_disconnected_callback(test_callback)
        # await client.is_connected()
        print("Connected!")
        buffer = HubBuffer()
        await client.start_notify(bleNusCharTXUUID, buffer.update_data_buffer)
        # await asyncio.sleep(2.0)
        await client.write_gatt_char(bleNusCharRXUUID, b'    ')
        await asyncio.sleep(2.0)
        await client.stop_notify(bleNusCharTXUUID)
        # await client.disconnect()


asyncio.run(main())
