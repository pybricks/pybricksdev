# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

"""This module and its submodules are used for Bluetooth Low Energy
communications with devices that provide the LEGO Wireless Protocol v3.
"""

from enum import IntEnum

# LEGO Wireless Protocol v3 is defined at:
# https://lego.github.io/lego-ble-wireless-protocol-docs/


LEGO_CID = 0x0397
"""LEGO System A/S company identifier.

This number is assigned by the Bluetooth SIG.

https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/
"""


def _lwp3_uuid(short: int) -> str:
    """Get a 128-bit UUID from a ``short`` UUID.

    Args:
        short: The 16-bit UUID.

    Returns:
        The 128-bit UUID as a string.
    """
    return f"0000{short:04x}-1212-efde-1623-785feabcd123"


LWP3_HUB_SERVICE_UUID = _lwp3_uuid(0x1623)
"""LEGO wireless protocol v3 hub service UUID."""

LWP3_HUB_CHARACTERISTIC_UUID = _lwp3_uuid(0x1624)
"""LEGO wireless protocol v3 hub characteristic UUID."""

LWP3_BOOTLOADER_SERVICE_UUID = _lwp3_uuid(0x1625)
"""LEGO wireless protocol v3 bootloader service UUID."""

LWP3_BOOTLOADER_CHARACTERISTIC_UUID = _lwp3_uuid(0x1626)
"""LEGO wireless protocol v3 bootloader characteristic UUID."""


# Bootloader characteristic bytecodes


class BootloaderCommand(IntEnum):
    """Commands that are sent to the bootloader GATT characteristic."""

    ERASE_FLASH = 0x11
    """Erases the flash memory."""

    PROGRAM_FLASH = 0x22
    """Writes to a segment of the flash memory."""

    START_APP = 0x33
    """Starts running the firmware (causes Bluetooth to disconnect)."""

    INIT_LOADER = 0x44
    """Initializes the firmware flasher."""

    GET_INFO = 0x55
    """Gets info about the hub and flash memory layout."""

    GET_CHECKSUM = 0x66
    """Gets the current checksum for the data that has been written so far."""

    GET_FLASH_STATE = 0x77
    """Gets the STM32 flash memory debug protection state.

    Not all bootloaders support this command.
    """

    DISCONNECT = 0x88
    """Causes the remote device to disconnect from Bluetooth."""


class BootloaderMessageKind(IntEnum):
    """Type for messages received from bootlaoder GATT characteristic notifications.

    Messages that are a response to a command will have the same value as
    :class:`BootloaderCommand` instead of a value from this enum.
    """

    ERROR = 0x05
    """Indicates that an error occurred."""


class BootloaderResult(IntEnum):
    """Status returned by certain bootloader commands."""

    OK = 0x00
    """The command was successful."""

    ERROR = 0xFF
    """The command failed."""


class BootloaderError(IntEnum):
    """Error type returned by bootloader error messages."""

    UNKNOWN_COMMAND = 0x05
    """The command was not recognized."""
