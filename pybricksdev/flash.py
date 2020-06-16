# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import asyncio
import io
import struct
import sys
import typing
import uuid
from collections import namedtuple
from enum import IntEnum
from tqdm import tqdm
import logging

from pybricksdev.ble import BLEStreamConnection, find_device


class BootloaderRequest():
    """Bootloader request structure."""

    def __init__(self, command, name, request_format, data_format, request_confirm):
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


# Create the static instances
BootloaderRequest.ERASE_FLASH = BootloaderRequest(
    0x11, 'Erase', ['result'], '<B', True
)
BootloaderRequest.PROGRAM_FLASH_BARE = BootloaderRequest(
    0x22, 'Flash', [], '', False
)
BootloaderRequest.PROGRAM_FLASH = BootloaderRequest(
    0x22, 'Flash', ['checksum', 'count'], '<BI', True
)
BootloaderRequest.START_APP = BootloaderRequest(
    0x33, 'Start', [], '', True
)
BootloaderRequest.INIT_LOADER = BootloaderRequest(
    0x44, 'Init', ['result'], '<B', True
)
BootloaderRequest.GET_INFO = BootloaderRequest(
    0x55, 'Info', ['version', 'start_addr', 'end_addr', 'type_id'], '<iIIB', True
)
BootloaderRequest.GET_CHECKSUM = BootloaderRequest(
    0x66, 'Checksum', ['checksum'], '<B', True
)
BootloaderRequest.GET_FLASH_STATE = BootloaderRequest(
    0x77, 'State', ['level'], '<B', True
)
BootloaderRequest.DISCONNECT = BootloaderRequest(
    0x88, 'Disconnect', [], '', True
)


class HubType(IntEnum):
    MOVEHUB = 0x40  # BOOST Move Hub
    CITYHUB = 0x41  # Hub No. 4
    CPLUSHUB = 0x80  # TECHNIC Control+ hub (Hub No. 2)

    # magic methods for argparse compatibility
    # https://stackoverflow.com/q/43968006/1976323

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return HubType[s.upper()]
        except KeyError:
            return s


class BootloaderConnection(BLEStreamConnection):
    """Connect to Powered Up Hub Bootloader and update firmware."""

    UUID = '00001626-1212-efde-1623-785feabcd123'

    def __init__(self):
        """Initialize the BLE Connection for Bootloader service."""
        super().__init__(self.UUID, self.UUID, 40, None)
        self.reply_ready = asyncio.Event()
        self.reply_len = 0
        self.reply = bytearray()

    async def bootloader_message(self, msg, payload=None, delay=0.05):
        """Sends a message to the bootloader and awaits corresponding reply."""

        # Get message command and expected reply length
        self.reply_len = msg.reply_len
        self.reply = bytearray()

        # Write message
        request = msg.make_request(payload)
        await self.write(request, delay)

        # If we expect a reply, await for it
        if self.reply_len > 0:
            self.logger.debug("Awaiting reply of {0}".format(self.reply_len))
            await self.reply_ready.wait()
            return msg.parse_reply(self.reply)

    def char_handler(self, char):
        """Handles new incoming characters. Overrides BLEStreamConnection to
        raise flags when new messages are ready.

        Arguments:
            char (int):
                Character/byte to process.

        Returns:
            int or None: Processed character.

        """
        self.logger.debug("CHAR {0}".format(char))
        # If we are expecting a nonzero reply, save the incoming character
        if self.reply_len > 0:
            self.reply.append(char)

            # If reply is complete, set the reply_ready event
            if len(self.reply) == self.reply_len:
                self.logger.debug("Awaiting reply complete.")
                self.reply_len = 0
                self.reply_ready.set()
                self.reply_ready.clear()

        return char

    async def flash(self, blob, metadata, delay):

        # Firmware information
        fw_io = io.BytesIO(blob)
        fw_len = len(blob)

        print("Getting device info.")
        info = await self.bootloader_message(BootloaderRequest.GET_INFO)
        self.logger.debug(info)

        hub_type = HubType(info.type_id)
        print('Connected to', hub_type)
        fw_hub_type = HubType(metadata['device-id'])
        if hub_type != fw_hub_type:
            await self.disconnect()
            raise RuntimeError(f'Firmware is for {str(fw_hub_type)}' +
                               f' but we are connected to {str(hub_type)}')

        # TODO: Use write with response on CityHub

        print("Erasing flash.")
        response = await self.bootloader_message(BootloaderRequest.ERASE_FLASH)
        self.logger.debug(response)

        print('Validating size.')
        size_payload = struct.pack('<I', fw_len)
        response = await self.bootloader_message(BootloaderRequest.INIT_LOADER, size_payload)
        self.logger.debug(response)

        count = 0

        print('flashing firmware...')
        with tqdm(total=fw_len, unit='B', unit_scale=True) as pbar:
            addr = info.start_addr
            while True:

                count += 1
                if count % 1000 == 0:
                    try:
                        response = await asyncio.wait_for(self.bootloader_message(BootloaderRequest.GET_CHECKSUM), 2)
                        print(response)
                    except (asyncio.exceptions.TimeoutError, ValueError):
                        print("Got stuck, try disconnect")
                        break

                # BLE packet can only handle up to 14 bytes at a time
                payload = fw_io.read(32)
                if not payload:
                    break

                size = len(payload)
                data = struct.pack('<BI' + 'B' * size, size + 4, addr, *payload)
                addr += size
                response = await self.bootloader_message(BootloaderRequest.PROGRAM_FLASH_BARE, data, delay)
                self.logger.debug(response)
                pbar.update(size)
            await asyncio.sleep(5)


def sum_complement(fw, max_size):
    """Calculates the checksum of a firmware file using the sum complement
    method of adding each 32-bit word and the returning the two's complement
    as the checksum.

    Parameters
    ----------
    fw : file
        The firmware file (a binary buffer - e.g. a file opened in 'rb' mode)
    max_size : int
        The maximum size of the firmware file.

    Returns
    -------
    int
        The correction needed to make the checksum of the file == 0.
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


def create_firmware(base, mpy, metadata):
    """Creates a firmware blob from base firmware and main.mpy file.

    Parameters
    ----------
    base : bytes
        base firmware binary blob
    mpy : bytes
        main.mpy binary blob
    metadata : dict
        firmware metadata

    Returns
    -------
    bytes
        composite binary blob with correct padding and checksum
    """
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

    return firmware


async def flash_firmware(address, blob, metadata):
    updater = BootloaderConnection()
    updater.logger.setLevel(logging.WARNING)
    await updater.connect(address)
    await updater.flash(blob, metadata, 0.003)
    await updater.disconnect()
