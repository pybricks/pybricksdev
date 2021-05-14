# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

import logging
import asyncio
import aioserial
from serial.tools import list_ports

logger = logging.getLogger(__name__)


async def find_device():
    pass


class USBConnection:
    """Configure USB, connect, send data, and handle receive events."""

    def __init__(self):
        """Initializes and configures connection settings."""
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

    # def disconnected_handler(self, client, *args):
    #     """Handles disconnected event. Intended to be overridden."""
    #     logger.info("Disconnected by server.")
    #     self.connected = False

    async def _read_loop(self):
        logger.debug("Started readloop")
        while self.connected:
            data = await self.ser.read_async(self.ser.in_waiting)
            if data:
                self.data_handler("", data)

        self.ser.close()

    async def connect(self, product):
        """Creates connection to server at given address.

        Arguments:
            product (str):
                USB product string to search for
        """
        port = None
        devices = list_ports.comports()
        for dev in devices:
            # FIXME: Generalize for cross platform
            if dev.product == product or (dev.pid == 0x5740 and dev.vid == 0x0483) or (dev.vid == 0x0694 and dev.pid == 0x0010) or (dev.vid == 0x0694 and dev.pid == 0x0009):
                port = dev.device
                break

        if port is None:
            raise ValueError("Could not find hub.")

        print("Connecting to {0}".format(port))
        self.ser = aioserial.AioSerial(port)
        self.connected = True
        self.task = asyncio.create_task(self._read_loop())
        await asyncio.sleep(0.5)

    async def disconnect(self):
        """Disconnects the client from the server."""
        if self.connected:
            logger.debug("Disconnecting...")
            self.connected = False
            self.ser.cancel_read()
            await self.task
            logger.info("Disconnected by client.")

    async def write(self, data):
        """Write bytes to the server.

        Arguments:
            data (bytearray):
                Data to be sent to the server.
        """
        logger.debug("TX data: {0}".format(data))
        await self.ser.write_async(data)
