# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

import asyncio
import logging

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

logger = logging.getLogger(__name__)


async def find_device(name: str, timeout: float = 5) -> BLEDevice:
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
        BLEDevice: Matching device.

    Raises:
        asyncio.TimeoutError:
            Device was not found within the timeout.
    """
    print("Searching for {0}".format(name))

    queue = asyncio.Queue()

    def set_device_discovered(device: BLEDevice, _: AdvertisementData):
        if device.name != name:
            return
        queue.put_nowait(device)

    async with BleakScanner(detection_callback=set_device_discovered):
        return await asyncio.wait_for(queue.get(), timeout=timeout)


class BLEConnection:
    """Configure BLE, connect, send data, and handle receive events."""

    def __init__(self, char_rx_UUID, char_tx_UUID, max_data_size):
        """Initializes and configures connection settings.

        Arguments:
            char_rx_UUID (str):
                UUID for RX.
            char_rx_UUID (str):
                UUID for TX.
            max_data_size (int):
                Maximum number of bytes per write operation.

        """
        # Save given settings
        self.char_rx_UUID = char_rx_UUID
        self.char_tx_UUID = char_tx_UUID
        self.max_data_size = max_data_size
        self.connected = False

    def data_handler(self, sender, data):
        """Handles new incoming data.

        This is usually overridden by a mixin class.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytes):
                Bytes to process.
        """
        logger.debug("DATA {0}".format(data))

    def disconnected_handler(self, client: BleakClient):
        """Handles disconnected event."""
        logger.debug("Disconnected.")
        self.connected = False

    async def connect(self, device: BLEDevice):
        """Connects to a BLE device.

        Arguments:
            device (BLEDevice):
                Client device
        """

        print("Connecting to", device)
        self.client = BleakClient(device)
        await self.client.connect(disconnected_callback=self.disconnected_handler)
        await self.client.start_notify(self.char_tx_UUID, self.data_handler)
        print("Connected successfully!")
        self.connected = True

    async def disconnect(self):
        """Disconnects the client from the server."""
        await self.client.stop_notify(self.char_tx_UUID)
        if self.connected:
            logger.debug("Disconnecting...")
            await self.client.disconnect()

    async def write(self, data, with_response=False):
        """Write bytes to the server, split to chunks of maximum data size.

        Arguments:
            data (bytearray):
                Data to be sent to the server.
            with_response (bool):
                Write with or without response.
        """
        # Send the chunks one by one
        for i in range(0, len(data), self.max_data_size):
            chunk = data[i: i + self.max_data_size]
            logger.debug(
                "TX CHUNK: {0}, {1} response".format(
                    chunk, "with" if with_response else "without"
                )
            )
            # Send one chunk
            await self.client.write_gatt_char(
                self.char_rx_UUID,
                bytearray(chunk),
                with_response
            )


class BLERequestsConnection(BLEConnection):
    """Sends messages and awaits replies of known length.

    This can be used for devices with known commands and known replies, such
    as some bootloaders to update firmware over the air.
    """

    def __init__(self, UUID):
        """Initialize the BLE Connection."""
        self.reply_ready = asyncio.Event()
        self.prepare_reply()

        super().__init__(UUID, UUID, 1024)

    def data_handler(self, sender, data):
        """Handles new incoming data and raise event when a new reply is ready.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytes):
                Bytes to process.
        """
        logger.debug("DATA {0}".format(data))
        self.reply = data
        self.reply_ready.set()

    def prepare_reply(self):
        """Clears existing reply and wait event.

        This is usually called prior to the write operation, to ensure we
        receive some of the bytes while are still awaiting the sending process.
        """
        self.reply = None
        self.reply_ready.clear()

    async def wait_for_reply(self, timeout=None):
        """Awaits for given number of characters since prepare_reply.

        Arguments:
            timeout (float or None):
                Time out to await. Same as asyncio.wait_for.

        Returns:
            bytearray: The reply.

        Raises
            TimeOutError. Same as asyncio.wait_for.
        """
        # Await for the reply ready event to be raised.
        await asyncio.wait_for(self.reply_ready.wait(), timeout)

        # Return reply and clear internal buffer
        reply = self.reply
        self.prepare_reply()
        return reply
