# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors

"""
Utilities for working with Pybricks ``firmware.zip`` files.
"""

from typing import Literal, TypedDict


class FirmwareMetadataV100(
    TypedDict(
        "V100",
        {
            "metadata-version": Literal["1.0.0"],
            "firmware-version": str,
            "device-id": Literal[0x40] | Literal[0x41] | Literal[0x80] | Literal[0x81],
            "checksum-type": Literal["sum"] | Literal["crc32"],
            "mpy-abi-version": int,
            "mpy-cross-options": list[str],
            "user-mpy-offset": int,
            "max-firmware-size": int,
        },
    )
):
    """
    Type for data contained in v1.0.0 ``firmware.metadata.json`` files.
    """


class FirmwareMetadataV110(
    FirmwareMetadataV100,
    TypedDict(
        "V110",
        {
            # changed
            "metadata-version": Literal["1.1.0"],
            # added
            "hub-name-offset": int,
            "max-hub-name-size": int,
        },
    ),
):
    """
    Type for data contained in v1.1.0 ``firmware.metadata.json`` files.
    """


AnyFirmwareMetadata = FirmwareMetadataV100 | FirmwareMetadataV110
"""
Type for data contained in ``firmware.metadata.json`` files of any version.
"""


class ExtendedFirmwareMetadata(
    FirmwareMetadataV110, TypedDict("Extended", {"firmware-sha256": str})
):
    # NB: Ideally, this should inherit from AnyFirmwareMetadata instead of
    # FirmwareMetadataV110 but that is not technically possible because being
    # a Union it has a different meta class from TypedDict
    """
    Type for data contained in ``firmware.metadata.json`` files of any version
    with extended data added.

    The extended data is used by the ``install_pybricks.py`` script.
    """
