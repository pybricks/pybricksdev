# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

"""
TI OAD (Over-the-Air Download) Image Block characteristic.

https://software-dl.ti.com/lprf/sdg-latest/html/oad-ble-stack-3.x/oad_profile.html#oad-image-block-characteristic-0xffc2
"""


from bleak import BleakClient

from pybricksdev.ble.oad._common import oad_uuid

__all__ = ["OADImageBlock"]

OAD_IMAGE_BLOCK_CHAR_UUID = oad_uuid(0xFFC2)


class OADImageBlock:
    def __init__(self, client: BleakClient):
        self._client = client

    async def write(self, block_num: int, data: bytes) -> None:
        """
        Write an image block.

        Args:
            offset: Offset of the block.
            data: Block data.

        Returns: None.
        """
        await self._client.write_gatt_char(
            OAD_IMAGE_BLOCK_CHAR_UUID,
            block_num.to_bytes(4, "little") + data,
            response=False,
        )
