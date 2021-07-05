# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

"""
This module is used for Bluetooth Low Energy communications with devices
that provide the Pybricks GATT service.

Device identification and connection
------------------------------------

Devices that support this protocol MUST advertise the :data:`PYBRICKS_SERVICE_UUID`.
Connecting devices SHOULD then filter on this UUID to identify compatible devices.

After connecting, programs SHOULD read the Software Revision characteristic of
the Device Information Service to determine the Pybricks protocol version. This
version can be used to determine the capabilities of the device.
"""

from enum import IntEnum
from struct import unpack
from typing import Literal, Tuple

import semver


def _pybricks_uuid(short: int) -> str:
    return f"c5f5{short:04x}-8280-46da-89f4-6d8051e4aeef"


PYBRICKS_SERVICE_UUID = _pybricks_uuid(0x0001)
"""The Pybricks GATT service UUID."""

PYBRICKS_CONTROL_UUID = _pybricks_uuid(0x0002)
"""The Pybricks control GATT characteristic UUID.

.. availability:: Since Pybricks protocol v1.0.0.
"""

PYBRICKS_PROTOCOL_VERSION = semver.VersionInfo(1, 1, 0)
"""The minimum required Pybricks protocol version supported by this library."""

# The Pybricks protocol is defined at:
# https://github.com/pybricks/pybricks-micropython/blob/master/lib/pbio/include/pbio/protocol.h


class Command(IntEnum):
    """Command for Pybricks BLE protocol.

    Commands are sent to a device running Pybricks firmware.
    """

    STOP_USER_PROGRAM = 0
    """Requests that the user program should be stopped.

    .. availability:: Since Pybricks protocol v1.0.0.
    """


class Event(IntEnum):
    """Event for Pybricks BLE protocol.

    Events are received from a device running Pybricks firmware.
    """

    STATUS_REPORT = 0
    """Status report.

    The payload is a 32-bit little-endian unsigned integer containing
    :class:`Status` flags.

    .. availability:: Since Pybricks protocol v1.0.0.
    """


class Status(IntEnum):
    """Hub status indicators.

    Use the :attr:`flag` property to get the value as a bit flag.
    """

    BATTERY_LOW_VOLTAGE_WARNING = 0
    """Battery voltage is low.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BATTERY_LOW_VOLTAGE_SHUTDOWN = 1
    """Battery voltage is critically low.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BATTERY_HIGH_CURRENT = 2
    """Battery current is too high.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BLE_ADVERTISING = 3
    """Bluetooth Low Energy is advertising/discoverable.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BLE_LOW_SIGNAL = 4
    """Bluetooth Low Energy has low signal.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    POWER_BUTTON_PRESSED = 5
    """Power button is currently pressed.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    USER_PROGRAM_RUNNING = 6
    """User program is currently running.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    SHUTDOWN = 7
    """Hub shutdown was requested.

    .. availability:: Since Pybricks protocol v1.1.0.
    """

    @property
    def flag(self) -> int:
        """Gets the value of the enum as a bit flag."""
        return 1 << self.value


# The Pybricks Protocol version also implies certain other services and
# and characteristics are present.

# UUIDs come from:
# https://btprodspecificationrefs.blob.core.windows.net/assigned-values/16-bit%20UUID%20Numbers%20Document.pdf


def _standard_uuid(short: int) -> str:
    """Gets a 128-bit UUID from a ``short`` UUID.

    Args:
        short: a 16-bit or 32-bit UUID.

    Returns:
        A 128-bit UUID as a string.
    """
    return f"{short:08x}-0000-1000-8000-00805f9b34fb"


# Device Information Service: https://www.bluetooth.com/specifications/specs/device-information-service-1-1/

DI_SERVICE_UUID = _standard_uuid(0x180A)
"""Standard Device Information Service UUID.

.. availability:: Since Pybricks protocol v1.0.0.
"""

FW_REV_UUID = _standard_uuid(0x2A26)
"""Standard Firmware Revision String characteristic UUID

.. availability:: Since Pybricks protocol v1.0.0.
"""

SW_REV_UUID = _standard_uuid(0x2A28)
"""Standard Software Revision String UUID (Pybricks protocol version)

.. availability:: Since Pybricks protocol v1.0.0.
"""

PNP_ID_UUID = _standard_uuid(0x2A50)
"""Standard PnP ID UUID

    Vendor ID is :const:`pybricksdev.ble.lwp3.LEGO_CID`. Product ID is one of
    :class:`pybricksdev.ble.lwp3.bytecodes.HubKind`. Revision is ``0`` for most
    hubs or ``1`` for MINDSTORMS Robot Inventor Hub.

.. availability:: Since Pybricks protocol v1.1.0.
"""


def unpack_pnp_id(data: bytes) -> Tuple[Literal["BT", "USB"], int, int, int]:
    """
    Unpacks raw data from the PnP ID characteristic.

    Args:
        data: The raw data

    Returns:
        Tuple containing the vendor ID type (``'BT'`` or ``'USB'``), the vendor
        ID, the product ID and the product revision.
    """
    vid_type, vid, pid, rev = unpack("<BHHH", data)
    vid_type = "BT" if vid_type else "USB"
    return vid_type, vid, pid, rev
