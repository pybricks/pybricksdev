# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

import asyncio
import struct
from enum import IntEnum

from bleak import BleakClient

from ._common import oad_uuid

__all__ = ["OADControlPoint"]


OAD_CONTROL_POINT_CHAR_UUID = oad_uuid(0xFFC5)
"""OAD Control Point characteristic UUID."""


class CmdId(IntEnum):
    GET_OAD_BLOCK_SIZE = 0x01
    SET_IMAGE_COUNT = 0x02
    START_OAD_PROCESS = 0x03
    ENABLE_OAD_IMAGE = 0x04
    CANCEL_OAD = 0x05
    DISABLE_OAD_IMAGE_BLOCK_WRITE = 0x06
    GET_SOFTWARE_VERSION = 0x07
    GET_OAD_IMAGE_STATUS = 0x08
    GET_PROFILE_VERSION = 0x09
    GET_DEVICE_TYPE = 0x10
    IMAGE_BLOCK_WRITE_CHAR = 0x12
    ERASE_ALL_BONDS = 0x13


class OADReturn(IntEnum):
    SUCCESS = 0
    """OAD succeeded"""
    CRC_ERR = 1
    """The downloaded image’s CRC doesn’t match the one expected from the metadata"""
    FLASH_ERR = 2
    """Flash function failure such as flashOpen/flashRead/flash write/flash erase"""
    BUFFER_OFL = 3
    """The block number of the received packet doesn’t match the one requested, an overflow has occurred."""
    ALREADY_STARTED = 4
    """OAD start command received, while OAD is already is progress"""
    NOT_STARTED = 5
    """OAD data block received with OAD start process"""
    DL_NOT_COMPLETE = 6
    """OAD enable command received without complete OAD image download"""
    NO_RESOURCES = 7
    """Memory allocation fails/ used only for backward compatibility"""
    IMAGE_TOO_BIG = 8
    """Image is too big"""
    INCOMPATIBLE_IMAGE = 9
    """Stack and flash boundary mismatch, program entry mismatch"""
    INVALID_FILE = 10
    """Invalid image ID received"""
    INCOMPATIBLE_FILE = 11
    """BIM/image header/firmware version mismatch"""
    AUTH_FAIL = 12
    """Start OAD process / Image Identify message/image payload authentication/validation fail"""
    EXT_NOT_SUPPORTED = 13
    """Data length extension or OAD control point characteristic not supported"""
    DL_COMPLETE = 14
    """OAD image payload download complete"""
    CCCD_NOT_ENABLED = 15
    """Internal (target side) error code used to halt the process if a CCCD has not been enabled"""
    IMG_ID_TIMEOUT = 16
    """OAD Image ID has been tried too many times and has timed out. Device will disconnect."""


def _decode_version(v: int) -> int:
    return (v >> 4) * 10 + (v & 0x0F)


class OADControlPoint:
    def __init__(self, client: BleakClient):
        self._client = client
        self._queue = asyncio.Queue[bytes]()

    async def __aenter__(self):
        await self._client.start_notify(
            OAD_CONTROL_POINT_CHAR_UUID, self._notification_handler
        )
        return self

    async def __aexit__(self, *exc_info):
        await self._client.stop_notify(OAD_CONTROL_POINT_CHAR_UUID)

    def _notification_handler(self, sender, data):
        self._queue.put_nowait(data)

    async def _send_command(self, cmd_id: CmdId, payload: bytes = b""):
        await self._client.write_gatt_char(
            OAD_CONTROL_POINT_CHAR_UUID, bytes([cmd_id]) + payload
        )
        rsp = await self._queue.get()

        if rsp[0] != cmd_id:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return rsp[1:]

    async def get_oad_block_size(self) -> int:
        """
        Get the OAD block size.

        Returns: OAD_BLOCK_SIZE
        """
        rsp = await self._send_command(CmdId.GET_OAD_BLOCK_SIZE)

        if len(rsp) != 2:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return int.from_bytes(rsp, "little")

    async def set_image_count(self, count: int) -> OADReturn:
        """
        Set the number of images to be downloaded.

        Args:
            count: Number of images to be downloaded.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.SET_IMAGE_COUNT, bytes([count]))

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])

    async def start_oad_process(self) -> int:
        """
        Start the OAD process.

        Returns: Block Number
        """
        rsp = await self._send_command(CmdId.START_OAD_PROCESS)

        if len(rsp) != 4:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return int.from_bytes(rsp, "little")

    async def enable_oad_image(self) -> OADReturn:
        """
        Enable the OAD image.

        Returns: Status
        """
        # REVISIT: this command can also take an optional payload
        rsp = await self._send_command(CmdId.ENABLE_OAD_IMAGE)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])

    async def cancel_oad(self) -> OADReturn:
        """
        Cancel the OAD process.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.CANCEL_OAD)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])

    async def disable_oad_image_block_write(self) -> OADReturn:
        """
        Disable OAD image block write.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.DISABLE_OAD_IMAGE_BLOCK_WRITE)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])

    async def get_software_version(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        Get the software version.

        Returns: Software Version (tuple of Application and Stack version tuples)
        """
        rsp = await self._send_command(CmdId.GET_SOFTWARE_VERSION)

        if len(rsp) != 4:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return (
            (_decode_version(rsp[0]), _decode_version(rsp[1])),
            (_decode_version(rsp[2]), _decode_version(rsp[3])),
        )

    async def get_oad_image_status(self) -> OADReturn:
        """
        Get the OAD image status.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.GET_OAD_IMAGE_STATUS)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])

    async def get_profile_version(self) -> int:
        """
        Get the profile version.

        Returns: Version of OAD profile supported by target
        """
        rsp = await self._send_command(CmdId.GET_PROFILE_VERSION)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return rsp[0]

    async def get_device_type(self) -> int:
        """
        Get the device type.

        Returns: Value of Device ID register
        """
        rsp = await self._send_command(CmdId.GET_DEVICE_TYPE)

        if len(rsp) != 4:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return int.from_bytes(rsp, "little")

    async def image_block_write(self, prev_status: int, block_num: int) -> None:
        """
        Write an image block.

        Args:
            prev_status: Status of the previous block received
            block_num: Block number
        """
        rsp = await self._send_command(
            CmdId.IMAGE_BLOCK_WRITE_CHAR, struct.pack("<BI", prev_status, block_num)
        )

        if len(rsp) != 0:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

    async def erase_all_bonds(self) -> OADReturn:
        """
        Erase all bonds.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.ERASE_ALL_BONDS)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])
