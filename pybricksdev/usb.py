import logging
import asyncio
import aioserial
from serial.tools import list_ports


async def find_device():
    pass


class USBConnection():
    """Configure USB, connect, send data, and handle receive events."""

    def __init__(self, **kwargs):
        """Initializes and configures connection settings."""
        self.connected = False

        # Get a logger and set at given level
        self.logger = logging.getLogger('BLERequestsConnection')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s: %(levelname)7s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.WARNING)

        super().__init__(**kwargs)

    def data_handler(self, sender, data):
        """Handles new incoming data.

        This is usually overridden by a mixin class.

        Arguments:
            sender (str):
                Sender uuid.
            data (bytes):
                Bytes to process.
        """
        self.logger.debug("DATA {0}".format(data))

    # def disconnected_handler(self, client, *args):
    #     """Handles disconnected event. Intended to be overridden."""
    #     self.logger.info("Disconnected by server.")
    #     self.connected = False

    async def _read_loop(self):
        self.logger.debug("Started readloop")
        while self.connected:
            data = await self.ser.read_all_async()
            if len(data) > 0:
                self.data_handler("", data)
            else:
                await asyncio.sleep(0.1)

    async def connect(self, product):
        """Creates connection to server at given address.

        Arguments:
            product (str):
                USB product string to search for
        """
        port = None
        devices = list_ports.comports()
        for dev in devices:
            if dev.product == product:
                port = dev.device
                break

        if port is None:
            raise OSError("Could not find hub.")

        print("Connecting to {0}".format(port))
        self.ser = aioserial.AioSerial(port)
        self.connected = True
        self.task = asyncio.create_task(self._read_loop())
        await asyncio.sleep(0.5)

    async def disconnect(self):
        """Disconnects the client from the server."""
        if self.connected:
            self.logger.debug("Disconnecting...")
            self.ser.close()
            self.logger.info("Disconnected by client.")
            # self.task.cancel()
            self.connected = False

    async def write(self, data, pause=0.05):
        """Write bytes to the server, split to chunks of maximum mtu size.

        Arguments:
            data (bytearray):
                Data to be sent to the server.
            pause (float):
                Time between chunks of data.
        """
        self.logger.debug("TX data: {0}".format(data))
        await self.ser.write_async(data)
