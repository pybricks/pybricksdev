# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors


import struct
from enum import IntEnum
from typing import NamedTuple


def oad_uuid(uuid16: int) -> str:
    """
    Converts a 16-bit UUID to the TI OAD 128-bit UUID format.
    """
    return "f000{:04x}-0451-4000-b000-000000000000".format(uuid16)


IMAGE_ID_TI = " OAD IMG"  # leading space is intentional
IMAGE_ID_LEGO = "LEGO 132"


class ImageType(IntEnum):
    PERSISTENT_APP = 0x00
    APPLICATION = 0x01
    STACK = 0x02
    APP_AND_STACK = 0x03
    NETWORK_PROCESSOR = 0x04
    BLE_FACTORY_IMAGE = 0x05
    BIM = 0x06
    MERGED = 0x07

    USER_0F = 0x0F
    USER_10 = 0x10
    USER_11 = 0x11
    USER_12 = 0x12
    USER_13 = 0x13
    USER_14 = 0x14
    USER_15 = 0x15
    USER_16 = 0x16
    USER_17 = 0x17
    USER_18 = 0x18
    USER_19 = 0x19
    USER_1A = 0x1A
    USER_1B = 0x1B
    USER_1C = 0x1C
    USER_1D = 0x1D
    USER_1E = 0x1E
    USER_1F = 0x1F

    HOST_20 = 0x20
    HOST_21 = 0x21
    HOST_22 = 0x22
    HOST_23 = 0x23
    HOST_24 = 0x24
    HOST_25 = 0x25
    HOST_26 = 0x26
    HOST_27 = 0x27
    HOST_28 = 0x28
    HOST_29 = 0x29
    HOST_2A = 0x2A
    HOST_2B = 0x2B
    HOST_2C = 0x2C
    HOST_2D = 0x2D
    HOST_2E = 0x2E
    HOST_2F = 0x2F
    HOST_30 = 0x30
    HOST_31 = 0x31
    HOST_32 = 0x32
    HOST_33 = 0x33
    HOST_34 = 0x34
    HOST_35 = 0x35
    HOST_36 = 0x36
    HOST_37 = 0x37
    HOST_38 = 0x38
    HOST_39 = 0x39
    HOST_3A = 0x3A
    HOST_3B = 0x3B
    HOST_3C = 0x3C
    HOST_3D = 0x3D
    HOST_3E = 0x3E
    HOST_3F = 0x3F


class ImageCopyStatus(IntEnum):
    DEFAULT_STATUS = 0xFF
    IMAGE_TO_BE_COPIED = 0xFE
    IMAGE_COPIED = 0xFC


class CRCStatus(IntEnum):
    INVALID = 0b00
    VALID = 0b01
    NOT_CALCULATED = 0b11

    UNKNOWN = 0xFF


DEFAULT_IMAGE_NUMBER = 0xFF


class ImageInfo(NamedTuple):
    copy_status: ImageCopyStatus
    crc_status: CRCStatus
    image_type: ImageType
    image_num: int

    @staticmethod
    def from_bytes(data: bytes) -> "ImageInfo":
        if len(data) != 4:
            raise ValueError("Expected 4 bytes")

        return ImageInfo(
            ImageCopyStatus(data[0]),
            CRCStatus(data[1]),
            ImageType(data[2]),
            data[3],
        )

    def __bytes__(self):
        return struct.pack(
            "<BBBB",
            self.copy_status,
            self.crc_status,
            self.image_type,
            self.image_num,
        )


class Version(NamedTuple):
    major: int
    minor: int


def _encode_version(version: int) -> int:
    return ((version // 10) << 4) | (version % 10)


def _decode_version(v: int) -> int:
    return (v >> 4) * 10 + (v & 0x0F)


class SoftwareVersion(NamedTuple):
    app: Version
    stack: Version

    @staticmethod
    def from_bytes(data: bytes) -> "SoftwareVersion":
        if len(data) != 4:
            raise ValueError("Expected 4 bytes")

        return SoftwareVersion(
            Version(_decode_version(data[0]), _decode_version(data[1])),
            Version(_decode_version(data[2]), _decode_version(data[3])),
        )

    def __bytes__(self):
        return struct.pack(
            "<4B",
            _encode_version(self.app.major),
            _encode_version(self.app.minor),
            _encode_version(self.stack.major),
            _encode_version(self.stack.minor),
        )


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
