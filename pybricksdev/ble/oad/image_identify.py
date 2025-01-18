# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

"""
TI OAD (Over-the-Air Download) Image Identify characteristic.

https://software-dl.ti.com/lprf/sdg-latest/html/oad-ble-stack-3.x/oad_profile.html#oad-image-identify-0xffc1
"""

import asyncio
import struct

from bleak import BleakClient
from bleak.exc import BleakError

from pybricksdev.ble.oad._common import ImageInfo, OADReturn, SoftwareVersion, oad_uuid

__all__ = ["OADImageIdentify"]

OAD_IMAGE_IDENTIFY_CHAR_UUID = oad_uuid(0xFFC1)
"""OAD Image Identify characteristic UUID."""


class OADImageIdentify:
    def __init__(self, client: BleakClient):
        self._client = client
        self._queue = asyncio.Queue[bytes]()

    def _notification_handler(self, sender, data):
        self._queue.put_nowait(data)

    async def __aenter__(self):
        await self._client.start_notify(
            OAD_IMAGE_IDENTIFY_CHAR_UUID, self._notification_handler
        )
        return self

    async def __aexit__(self, *exc_info):
        try:
            await self._client.stop_notify(OAD_IMAGE_IDENTIFY_CHAR_UUID)
        except BleakError:
            # ignore if already disconnected
            pass

    async def validate(
        self,
        img_id: str,
        bmi_ver: int,
        header_ver: int,
        image_info: ImageInfo,
        image_len: int,
        sw_ver: SoftwareVersion,
    ) -> OADReturn:
        """
        Validate the image header.

        Returns: True if the image header is valid.
        """
        data = struct.pack(
            "<8s2B4sI4s",
            bytes(img_id, "ascii"),
            bmi_ver,
            header_ver,
            bytes(image_info),
            image_len,
            bytes(sw_ver),
        )

        await self._client.write_gatt_char(
            OAD_IMAGE_IDENTIFY_CHAR_UUID, data, response=False
        )
        rsp = await self._queue.get()

        return OADReturn(rsp[0])
