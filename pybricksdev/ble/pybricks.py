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

Additional information about the Pybricks Profile can be found at
_`https://github.com/pybricks/technical-info/blob/master/pybricks-ble-profile.md`.
"""

from enum import IntEnum, IntFlag
from struct import unpack
from typing import Literal, Tuple

import semver


def _pybricks_uuid(short: int) -> str:
    return f"c5f5{short:04x}-8280-46da-89f4-6d8051e4aeef"


PYBRICKS_SERVICE_UUID = _pybricks_uuid(0x0001)
"""The Pybricks GATT service UUID."""

PYBRICKS_COMMAND_EVENT_UUID = _pybricks_uuid(0x0002)
"""The Pybricks command/event GATT characteristic UUID.

Commands are written to this characteristic and events are received via notifications.

See :class:`Command` and :class:`Event`.

.. availability:: Since Pybricks protocol v1.0.0.
"""

PYBRICKS_HUB_CAPABILITIES_UUID = _pybricks_uuid(0x0003)
"""The Pybricks hub capabilities GATT characteristic UUID.

.. availability:: Since Pybricks protocol v1.2.0.
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

    START_USER_PROGRAM = 1
    """
    Requests that the user program should be started.

    Hub responds with :attr:`CommandError.BUSY` if a user program is currently running.

    .. availability:: Since Pybricks protocol v1.2.0.
    """

    START_REPL = 2
    """
    Requests that the interactive REPL should be started.

    Hub responds with :attr:`CommandError.INVALID_COMMAND` if the hub does not support the REPL.
    Hub responds with :attr:`CommandError.BUSY` if a user program is currently running.

    .. availability:: Since Pybricks protocol v1.2.0.
    """

    WRITE_USER_PROGRAM_META = 3
    """
    Requests to write user program metadata.

    Parameters:
        size: The size of the user program in bytes (32-bit unsigned integer).

    Hub responds with :attr:`CommandError.BUSY` if a user program is currently running.

    .. availability:: Since Pybricks protocol v1.2.0.
    """

    COMMAND_WRITE_USER_RAM = 4
    """
    Requests to write data to user RAM.

    Parameters:
        offset: The offset from the base user RAM address (32-bit unsigned integer).
        payload: The data to write to this address (0 to ``max_char_size`` - 5 bytes).

    Hub responds with :attr:`CommandError.VALUE_NOT_ALLOWED` if the offset and size exceeded the user RAM area.
    Hub responds with :attr:`CommandError.BUSY` if a user program is currently running.

    .. availability:: Since Pybricks protocol v1.2.0.
    """


class CommandError(IntEnum):
    """
    GATT Attribute error codes that can be sent in response to command write requests.
    """

    # NB: these values are standard BLE protocol values (i.e. Table 3.4 in v5.3 core specification)

    INVALID_HANDLE = 0x01
    """
    The attribute handle given was not valid on this server.
    """
    NOT_SUPPORTED = 0x06
    """
    Attribute server does not support the request received from the client.
    """
    VALUE_NOT_ALLOWED = 0x13
    """
    The attribute parameter value was not allowed.
    """

    # NB: these values are limited to 0x80 – 0x9F as required by the Bluetooth
    # spec (i.e. Table 3.4 in v5.3 core specification)

    INVALID_COMMAND = 0x80
    """
    An invalid command was requested.

    .. availability:: Since Pybricks protocol v1.2.0.
    """

    BUSY = 0x81
    """
    The command cannot be completed now because the required resources are busy.

    .. availability:: Since Pybricks protocol v1.2.0.
    """


class Event(IntEnum):
    """Event for Pybricks BLE protocol.

    Events are received from a device running Pybricks firmware.
    """

    STATUS_REPORT = 0
    """Status report.

    The payload is a 32-bit little-endian unsigned integer containing
    :class:`StatusFlag` flags.

    .. availability:: Since Pybricks protocol v1.0.0.
    """


class StatusFlag(IntFlag):
    """Hub status indicators."""

    BATTERY_LOW_VOLTAGE_WARNING = 1 << 0
    """Battery voltage is low.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BATTERY_LOW_VOLTAGE_SHUTDOWN = 1 << 1
    """Battery voltage is critically low.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BATTERY_HIGH_CURRENT = 1 << 2
    """Battery current is too high.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BLE_ADVERTISING = 1 << 3
    """Bluetooth Low Energy is advertising/discoverable.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    BLE_LOW_SIGNAL = 1 << 4
    """Bluetooth Low Energy has low signal.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    POWER_BUTTON_PRESSED = 1 << 5
    """Power button is currently pressed.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    USER_PROGRAM_RUNNING = 1 << 6
    """User program is currently running.

    .. availability:: Since Pybricks protocol v1.0.0.
    """

    SHUTDOWN = 1 << 7
    """Hub has entered shutdown state.

    .. availability:: Since Pybricks protocol v1.1.0.
    """

    SHUTDOWN_REQUESTED = 1 << 8
    """Hub shutdown was requested.

    .. availability:: Since Pybricks protocol v1.2.0.
    """


class HubCapabilityFlag(IntFlag):
    """
    Hub capability flags.
    """

    HAS_REPL = 1 << 0
    """
    Indicates that the hub has an interactive REPL.

    .. availability:: Since Pybricks protocol v1.2.0.
    """

    USER_PROG_MULTI_FILE_MPY6 = 1 << 1
    """
    Hub supports user programs using a multi-file blob with MicroPython MPY (ABI V6) files.

    .. availability:: Since Pybricks protocol v1.2.0.
    """


def unpack_hub_capabilities(data: bytes) -> Tuple[int, HubCapabilityFlag, int]:
    """
    Unpacks the value read from the hub capabilities characteristic.

    Args:
        data: The raw characteristic value.

    Returns:
        A tuple of the maximum characteristic write size in bytes, the hub capability
        flags and the max user program size in bytes.
    """
    max_char_size, flags, max_user_prog_size = unpack("<HII", data)
    return max_char_size, HubCapabilityFlag(flags), max_user_prog_size


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
