# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import io
from collections import namedtuple
import json
import struct
import sys
from tqdm import tqdm
import zipfile

from .ble import BLERequestsConnection
from .compile import save_script, compile_file


def sum_complement(fw, max_size):
    """Calculates the checksum of a firmware file using the sum complement
    method of adding each 32-bit word and the returning the two's complement
    as the checksum.

    Arguments:
        fw (file):
            The firmware file (a binary buffer - e.g. a file opened in 'rb' mode)
        max_size (int):
            The maximum size of the firmware file.

    Returns:
        int: The correction needed to make the checksum of the file == 0.
    """
    checksum = 0
    size = 0

    while True:
        word = fw.read(4)
        if not word:
            break
        checksum += struct.unpack('I', word)[0]
        size += 4

    if size > max_size:
        print('firmware + main.mpy is too large"', file=sys.stderr)
        exit(1)

    for _ in range(size, max_size, 4):
        checksum += 0xffffffff

    checksum &= 0xffffffff
    correction = checksum and (1 << 32) - checksum or 0

    return correction


async def create_firmware(firmware_zip):
    """Creates a firmware blob from base firmware and main.mpy file.

    Arguments:
        firmware_zip (str):
            Path to the firmware zip file.

    Returns:
        bytes: Composite binary blob with correct padding and checksum.
        dict: Meta data for this firmware file.
    """

    archive = zipfile.ZipFile(firmware_zip)
    base = archive.open('firmware-base.bin').read()
    main_py = io.TextIOWrapper(archive.open('main.py'))
    metadata = json.load(archive.open('firmware.metadata.json'))

    mpy = await compile_file(
        save_script(main_py.read()),
        metadata['mpy-cross-options'],
        metadata['mpy-abi-version']
    )

    # start with base firmware binary blob
    firmware = bytearray(base)
    # pad with 0s until user-mpy-offset
    firmware.extend(
        0 for _ in range(metadata['user-mpy-offset'] - len(firmware)))
    # append 32-bit little-endian main.mpy file size
    firmware.extend(struct.pack('<I', len(mpy)))
    # append main.mpy file
    firmware.extend(mpy)
    # pad with 0s to align to 4-byte boundary
    firmware.extend(0 for _ in range(-len(firmware) % 4))

    # append 32-bit little-endian checksum
    if metadata['checksum-type'] == "sum":
        firmware.extend(
            struct.pack(
                '<I',
                sum_complement(io.BytesIO(firmware),
                               metadata['max-firmware-size'] - 4)))
    else:
        print(f'Unknown checksum type "{metadata["checksum-type"]}"',
              file=sys.stderr)
        exit(1)

    return firmware, metadata


HUB_NAMES = {
    0x40: 'Move Hub',
    0x41: 'City Hub',
    0x80: 'Control+ Hub'
}

# FIXME: This belongs in metadata
PAYLOAD_SIZE = {
    0x40: 14,
    0x41: 32,  # untested
    0x80: 32,
}


class BootloaderRequest():
    """Bootloader request structure."""

    def __init__(self, command, name, request_format, data_format, request_confirm=True):
        self.command = command
        self.ReplyClass = namedtuple(name, request_format)
        self.data_format = data_format
        self.reply_len = struct.calcsize(data_format)
        if request_confirm:
            self.reply_len += 1

    def make_request(self, payload=None):
        request = bytearray((self.command,))
        if payload is not None:
            request += payload
        return request

    def parse_reply(self, reply):
        if reply[0] == self.command:
            return self.ReplyClass(*struct.unpack(self.data_format, reply[1:]))
        else:
            raise ValueError("Unknown message: {0}".format(reply))


class BootloaderConnection(BLERequestsConnection):
    """Connect to Powered Up Hub Bootloader and update firmware."""

    # Static BootloaderRequest instances for particular messages
    ERASE_FLASH = BootloaderRequest(
        0x11, 'Erase', ['result'], '<B'
    )
    PROGRAM_FLASH_BARE = BootloaderRequest(
        0x22, 'Flash', [], '', False
    )
    PROGRAM_FLASH = BootloaderRequest(
        0x22, 'Flash', ['checksum', 'count'], '<BI'
    )
    START_APP = BootloaderRequest(
        0x33, 'Start', [], ''
    )
    INIT_LOADER = BootloaderRequest(
        0x44, 'Init', ['result'], '<B'
    )
    GET_INFO = BootloaderRequest(
        0x55, 'Info', ['version', 'start_addr', 'end_addr', 'type_id'], '<iIIB'
    )
    GET_CHECKSUM = BootloaderRequest(
        0x66, 'Checksum', ['checksum'], '<B'
    )
    GET_FLASH_STATE = BootloaderRequest(
        0x77, 'State', ['level'], '<B'
    )
    DISCONNECT = BootloaderRequest(
        0x88, 'Disconnect', [], ''
    )

    def __init__(self):
        """Initialize the BLE Connection for Bootloader service."""
        super().__init__('00001626-1212-efde-1623-785feabcd123')

    async def bootloader_request(self, request, payload=None, delay=0.05, timeout=None):
        """Sends a message to the bootloader and awaits corresponding reply."""

        # Get message command and expected reply length
        self.prepare_reply(request.reply_len)

        # Write message
        data = request.make_request(payload)
        await self.write(data, delay)

        # If we expect a reply, await for it
        if request.reply_len > 0:
            self.logger.debug("Awaiting reply of {0}".format(self.reply_len))
            reply = await self.wait_for_reply(timeout)
            return request.parse_reply(reply)

    async def flash(self, firmware, metadata, delay):

        # Firmware information
        firmware_io = io.BytesIO(firmware)
        firmware_size = len(firmware)

        # Request hub information
        self.logger.info("Getting device info.")
        info = await self.bootloader_request(self.GET_INFO)
        self.logger.debug(info)

        # Verify hub ID against ID in firmware package
        if info.type_id != metadata['device-id']:
            await self.disconnect()
            raise RuntimeError(
                "This firmware {0}, but we are connected to {1}.".format(
                    HUB_NAMES[metadata['device-id']], HUB_NAMES[info.type_id]
                )
            )

        # TODO: Use write with response on CityHub

        # Erase existing firmware
        self.logger.info("Erasing flash.")
        response = await self.bootloader_request(self.ERASE_FLASH)
        self.logger.debug(response)

        # Get the bootloader ready to accept the firmware
        self.logger.info('Request begin update.')
        response = await self.bootloader_request(
            request=self.INIT_LOADER,
            payload=struct.pack('<I', firmware_size)
        )
        self.logger.debug(response)
        self.logger.info('Begin update.')

        # Percentage after which we'll check progress
        verify_progress = 5

        # Maintain progress using tqdm
        with tqdm(total=firmware_size, unit='B', unit_scale=True) as pbar:

            # Repeat until the whole firmware has been processed
            while firmware_io.tell() != firmware_size:

                # Progress percentage
                progress = firmware_io.tell() / firmware_size * 100

                # If progressed beyond next checkpoint, check connection.
                if progress > verify_progress:
                    # Get checksum. This tells us the hub is still operating
                    # normally. If we don't get it, we stop
                    result = await self.bootloader_request(
                        self.GET_CHECKSUM, timeout=2
                    )
                    self.logger.debug(result)

                    # Check again after 20% more progress
                    verify_progress += 20

                # The write address is the starting address plus
                # how much has been written already
                address = info.start_addr + firmware_io.tell()

                # Read the firmware chunk to be sent
                payload = firmware_io.read(PAYLOAD_SIZE[info.type_id])

                # Check if this is the last chunk to be sent
                if firmware_io.tell() == firmware_size:
                    # If so, request flash with confirmation request.
                    request = self.PROGRAM_FLASH
                else:
                    # Otherwise, do not wait for confirmation.
                    request = self.PROGRAM_FLASH_BARE

                # Pack the data in the expected format
                data = struct.pack('<BI' + 'B' * len(payload), len(payload) + 4, address, *payload)
                response = await self.bootloader_request(request, data, delay)
                self.logger.debug(response)
                pbar.update(len(payload))

        # Reboot the hub
        self.logger.info('Request reboot.')
        response = await self.bootloader_request(self.START_APP)
        self.logger.debug(response)
