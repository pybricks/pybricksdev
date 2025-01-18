# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

import struct
from typing import NamedTuple

from pybricksdev.ble.oad._common import ImageInfo, SoftwareVersion

# More info at:
# https://github.com/TexasInstruments/simplelink-lowpower-f3-sdk/blob/main/tools/common/oad/oad_image_tool.py


class ODAHeader(NamedTuple):
    image_id: str
    image_crc: int
    bmi_version: int
    header_version: int
    wireless_tech: int
    image_info: ImageInfo
    image_validation: int
    image_length: int
    program_entry_address: int
    software_version: int
    image_end_address: int
    image_header_length: int
    rfu2: int


def parse_oad_header(firmware: bytes) -> ODAHeader:
    (
        image_id,
        image_crc,
        bmi_version,
        header_version,
        wireless_tech,
        image_info,
        image_validation,
        image_length,
        program_entry_address,
        software_version,
        image_end_address,
        image_header_length,
        rfu2,
    ) = struct.unpack_from(
        "<8sI2BH4s3I4sI2H",
        firmware,
    )

    return ODAHeader(
        image_id.decode("ascii"),
        image_crc,
        bmi_version,
        header_version,
        wireless_tech,
        ImageInfo.from_bytes(image_info),
        image_validation,
        image_length,
        program_entry_address,
        SoftwareVersion.from_bytes(software_version),
        image_end_address,
        image_header_length,
        rfu2,
    )
