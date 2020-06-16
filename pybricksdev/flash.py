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

from pybricksdev.ble import BLEStreamConnection, find_device

ErrorReply = namedtuple('ErrorReply', ['msg_type', 'error'])
EraseReply = namedtuple('EraseReply', ['result'])
FlashReply = namedtuple('FlashReply', ['checksum', 'count'])
InitReply = namedtuple('InitReply', ['result'])
InfoReply = namedtuple('InfoReply',
                       ['version', 'start_addr', 'end_addr', 'type_id'])
ChecksumReply = namedtuple('ChecksumReply', ['checksum'])
FlashStateReply = namedtuple('FlashStateReply', ['level'])


class FlashLoaderFunction(IntEnum):
    ERASE_FLASH = 0x11
    PROGRAM_FLASH = 0x22
    START_APP = 0x33
    INIT_LOADER = 0x44
    GET_INFO = 0x55
    GET_CHECKSUM = 0x66
    GET_FLASH_STATE = 0x77
    DISCONNECT = 0x88


def parse(self, msg: bytearray):
    # ignore fake message from BLEventQ.get_messages()
    if msg[0] == 15:
        return

    # error
    elif msg[0] == 0x05 and msg[2] == 0x05:
        reply = ErrorReply(*struct.unpack('<BB', msg[3:]))

    elif msg[0] == FlashLoaderFunction.ERASE_FLASH:
        reply = EraseReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.PROGRAM_FLASH:
        reply = FlashReply(*struct.unpack('<BI', msg[1:]))
    elif msg[0] == FlashLoaderFunction.INIT_LOADER:
        reply = InitReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_INFO:
        reply = InfoReply(*struct.unpack('<iIIB', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_CHECKSUM:
        reply = ChecksumReply(*struct.unpack('<B', msg[1:]))
    elif msg[0] == FlashLoaderFunction.GET_FLASH_STATE:
        reply = FlashStateReply(*struct.unpack('<B', msg[1:]))
    else:
        raise RuntimeError('Unknown message type {}'.format(hex(msg[0])))

    self.hub.peripheral_queue.put(('reply', reply))
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


class FirmwareUpdateHub(BLEStreamConnection):
    uart_uuid = uuid.UUID('00001625-1212-efde-1623-785feabcd123')
    char_uuid = uuid.UUID('00001626-1212-efde-1623-785feabcd123')
    query_port_info = None

    def __init__(self, firmware: typing.io.BinaryIO, firmware_size: int,
                 metadata: dict, delay: int):

        self.firmware = firmware
        self.firmware_size = firmware_size
        self.metadata = metadata
        self.delay = delay

    async def run(self):
        print('getting device info...')
        await self.send_message('info', [FlashLoaderFunction.GET_INFO])
        _, info = await self.peripheral_queue.get()
        if not isinstance(info, InfoReply):
            raise RuntimeError('Failed to get device info')

        hub_type = HubType(info.type_id)
        print('Connected to', hub_type)

        fw_hub_type = HubType(self.metadata['device-id'])
        if hub_type != fw_hub_type:
            raise RuntimeError(f'Firmware is for {str(fw_hub_type)}' +
                               f' but we are connected to {str(hub_type)}')

        # HACK for cityhub bootloader bug. BlueZ will disconnect on certain
        # commands if we don't request a response.
        response = hub_type == HubType.CITYHUB

        print('erasing flash...')
        await self.send_message('erase', [FlashLoaderFunction.ERASE_FLASH],
                                response)
        _, result = await self.peripheral_queue.get()
        if not isinstance(result, EraseReply) or result.result:
            raise RuntimeError('Failed to erase flash')

        print('validating size...')
        size = list(struct.pack('<I', self.firmware_size))
        await self.send_message('init',
                                [FlashLoaderFunction.INIT_LOADER] + size,
                                response)
        _, result = await self.peripheral_queue.get()
        if not isinstance(result, InitReply) or result.result:
            raise RuntimeError('Failed to init')

        print('flashing firmware...')
        with tqdm(total=self.firmware_size, unit='B', unit_scale=True) as pbar:
            addr = info.start_addr
            while True:
                if not self.peripheral_queue.empty():
                    # we were not expecting a reply yet, this is probably an
                    # error, e.g. we overflowed the buffer
                    _, result = await self.peripheral_queue.get()
                    if isinstance(result, ErrorReply):
                        print('Received error reply', result)
                    else:
                        print('Unexpected message from hub. Please try again.')
                    return

                # BLE packet can only handle up to 14 bytes at a time
                payload = self.firmware.read(14)
                if not payload:
                    break

                size = len(payload)
                data = list(
                    struct.pack('<BI' + 'B' * size, size + 4, addr, *payload))
                addr += size
                await self.send_message(
                    'flash', [FlashLoaderFunction.PROGRAM_FLASH] + data)
                # If we send data too fast, we can overrun the Bluetooth
                # buffer on the hub
                await sleep(self.delay / 1000)
                pbar.update(size)

        _, result = await self.peripheral_queue.get()
        if not isinstance(result,
                          FlashReply) or result.count != self.firmware_size:
            raise RuntimeError('Failed to flash firmware')

        print('rebooting hub...')
        await self.send_message('reboot', [FlashLoaderFunction.START_APP])
        # This command does not get a reply

    async def send_message(self, msg_name, msg_bytes, response=False):
        while not self.tx:
            await sleep(0.1)
        await self.message_queue.put(
            (msg_name, self, bytearray(msg_bytes), response))


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
    print(address)
