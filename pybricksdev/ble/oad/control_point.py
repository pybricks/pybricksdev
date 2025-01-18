# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

import asyncio
from enum import IntEnum
from typing import AsyncGenerator

from bleak import BleakClient
from bleak.exc import BleakError

from pybricksdev.ble.oad._common import OADReturn, SoftwareVersion, oad_uuid

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


OAD_LEGO_MARIO_DEVICE_TYPE = 0xFF150409
"""Device type for LEGO Mario and friends."""

OAD_LEGO_TECHNIC_MOVE_DEVICE_TYPE = 0xFF160409
"""Device type for LEGO Technic Move Hub."""


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
        try:
            await self._client.stop_notify(OAD_CONTROL_POINT_CHAR_UUID)
        except BleakError:
            # ignore if already disconnected
            pass

    def _notification_handler(self, sender, data):
        self._queue.put_nowait(data)

    async def _send_command(self, cmd_id: CmdId, payload: bytes = b""):
        await self._client.write_gatt_char(
            OAD_CONTROL_POINT_CHAR_UUID, bytes([cmd_id]) + payload, response=False
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

    async def start_oad_process(self) -> AsyncGenerator[tuple[OADReturn, int], None]:
        """
        Start the OAD process.

        Returns: Block Number
        """
        await self._client.write_gatt_char(
            OAD_CONTROL_POINT_CHAR_UUID,
            bytes([CmdId.START_OAD_PROCESS]),
            response=False,
        )

        while True:
            rsp = await self._queue.get()

            if len(rsp) != 6 or rsp[0] != CmdId.IMAGE_BLOCK_WRITE_CHAR:
                raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

            status = OADReturn(rsp[1])
            block_num = int.from_bytes(rsp[2:], "little")

            yield status, block_num

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

    async def get_software_version(self) -> SoftwareVersion:
        """
        Get the software version.

        Returns: Software Version (tuple of Application and Stack version tuples)
        """
        rsp = await self._send_command(CmdId.GET_SOFTWARE_VERSION)

        if len(rsp) != 4:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return SoftwareVersion.from_bytes(rsp)

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

    async def erase_all_bonds(self) -> OADReturn:
        """
        Erase all bonds.

        Returns: Status
        """
        rsp = await self._send_command(CmdId.ERASE_ALL_BONDS)

        if len(rsp) != 1:
            raise RuntimeError(f"Unexpected response: {rsp.hex(':')}")

        return OADReturn(rsp[0])
