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

ErrorReply = namedtuple('ErrorReply', ['msg_type', 'error'])
EraseReply = namedtuple('EraseReply', ['result'])
FlashReply = namedtuple('FlashReply', ['checksum', 'count'])
InitReply = namedtuple('InitReply', ['result'])
InfoReply = namedtuple('InfoReply',
                       ['version', 'start_addr', 'end_addr', 'type_id'])
ChecksumReply = namedtuple('ChecksumReply', ['checksum'])
FlashStateReply = namedtuple('FlashStateReply', ['level'])


class FlashLoaderFunction():
    ERASE_FLASH = (0x11, 1)
    PROGRAM_FLASH = (0x22, 1+4)
    START_APP = (0x33, 0)
    INIT_LOADER = (0x44, 1)
    GET_INFO = (0x55, 4+4+4+1)
    GET_CHECKSUM = (0x66, 1)
    GET_FLASH_STATE = (0x77, 1)
    DISCONNECT = (0x88, 0)


def parse(msg):
    # ignore fake message from BLEventQ.get_messages()
    if msg[0] == 15:
        return

    # error
    elif msg[0] == 0x05 and msg[2] == 0x05:
        reply = ErrorReply(*struct.unpack('<BB', msg[3:]))

    elif msg[0] == FlashLoaderFunction.ERASE_FLASH[0]:
        reply = EraseReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.PROGRAM_FLASH[0]:
        reply = FlashReply(*struct.unpack('<BI', msg[1:]))
    elif msg[0] == FlashLoaderFunction.INIT_LOADER[0]:
        reply = InitReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_INFO[0]:
        reply = InfoReply(*struct.unpack('<iIIB', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_CHECKSUM[0]:
        reply = ChecksumReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_FLASH_STATE[0]:
        reply = FlashStateReply(*struct.unpack('<B', msg[1:]))
    else:
        raise RuntimeError('Unknown message type {}'.format(hex(msg[0])))
    return reply


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

    UART_UUID = '00001625-1212-efde-1623-785feabcd123'
    CHAR_UUID = '00001626-1212-efde-1623-785feabcd123'

    def __init__(self):
        """Initialize the BLE Connection for Bootloader service."""
        super().__init__(self.CHAR_UUID, self.CHAR_UUID, 20, None)
        self.reply_ready = asyncio.Event()
        self.reply_len = 0
        self.reply = bytearray()

    async def send_bootloader_message(self, msg):
        """Sends a message to the bootloader and awaits corresponding reply."""

        # Get message command and expected reply length
        cmd, self.reply_len = msg
        self.reply = bytearray()

        # Write message
        await self.write(bytes((cmd,)))

        # If we expect a reply, await for it
        if self.reply_len > 0:
            await self.reply_ready.wait()
            self.reply_len = 0
            return parse(self.reply)

    def char_handler(self, char):
        """Handles new incoming characters. Overrides BLEStreamConnection to
        raise flags when new messages are ready.

        Arguments:
            char (int):
                Character/byte to process.

        Returns:
            int or None: Processed character.

        """

        if self.reply_len > 0:
            self.reply.append(char)

            self.logger.debug(
                "Received reply byte {0}/{1}".format(
                    len(self.reply), self.reply_len
                )
            )

            if len(self.reply) == self.reply_len:
                self.logger.debug("Reply complete.")
                self.reply_ready.set()
                self.reply_ready.clear()

        return char


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


async def flash_firmware(blob):
    address = await find_device("LEGO Bootloader", 15)
    print("Found: ", address)
    updater = BootloaderConnection()
    updater.logger.setLevel(logging.DEBUG)
    await updater.connect(address)
    r = await updater.send_bootloader_message(FlashLoaderFunction.GET_FLASH_STATE)
    q = await updater.send_bootloader_message(FlashLoaderFunction.GET_INFO)
    print(r, q)
    await asyncio.sleep(3)
    await updater.disconnect()
