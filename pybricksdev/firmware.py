# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors

"""
Utilities for working with Pybricks ``firmware.zip`` files.
"""

import sys
from typing import Literal, TypedDict, Union

if sys.version_info < (3, 10):
    from typing_extensions import TypeGuard
else:
    from typing import TypeGuard


class FirmwareMetadataV100(
    TypedDict(
        "V100",
        {
            "metadata-version": Literal["1.0.0"],
            "firmware-version": str,
            "device-id": Literal[0x40, 0x41, 0x80, 0x81],
            "checksum-type": Literal["sum", "crc32"],
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


class FirmwareMetadataV200(
    TypedDict(
        "V200",
        {
            "metadata-version": Literal["2.0.0"],
            "firmware-version": str,
            "device-id": Literal[0x40, 0x41, 0x80, 0x81, 83],
            "checksum-type": Literal["sum", "crc32"],
            "checksum-size": int,
            "hub-name-offset": int,
            "hub-name-size": int,
        },
    )
):
    """
    Type for data contained in v2.0.0 ``firmware.metadata.json`` files.
    """


AnyFirmwareV1Metadata = Union[FirmwareMetadataV100, FirmwareMetadataV110]
"""
Type for data contained in ``firmware.metadata.json`` files of any 1.x version.
"""

AnyFirmwareV2Metadata = FirmwareMetadataV200
"""
Type for data contained in ``firmware.metadata.json`` files of any 2.x version.
"""

AnyFirmwareMetadata = Union[AnyFirmwareV1Metadata, AnyFirmwareV2Metadata]
"""
Type for data contained in ``firmware.metadata.json`` files of any version.
"""


def firmware_metadata_is_v1(
    metadata: AnyFirmwareMetadata,
) -> TypeGuard[AnyFirmwareV1Metadata]:
    return metadata["metadata-version"].startswith("1.")


def firmware_metadata_is_v2(
    metadata: AnyFirmwareMetadata,
) -> TypeGuard[AnyFirmwareV2Metadata]:
    return metadata["metadata-version"].startswith("2.")


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
