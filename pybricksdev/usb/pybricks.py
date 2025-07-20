# SPDX-License-Identifier: MIT
# Copyright (c) 2025 The Pybricks Authors

"""
Pybricks-specific USB protocol.

This is generally a wrapper around the Pybricks BLE protocol adapted for USB.
"""

from enum import IntEnum


class PybricksUsbInterfaceClassRequest(IntEnum):
    """
    Request type for the Pybricks USB interface class.

    This is passed as bRequest in the USB control transfer where wIndex is the
    interface number of the Pybricks USB interface and bmRequestType has type
    of Class (1) and Recipient of Interface (1).
    """

    GATT_CHARACTERISTIC = 1
    """
    Analogous to standard BLE GATT characteristics.

    bValue is the 16-bit UUID of the characteristic.
    """

    PYBRICKS_CHARACTERISTIC = 2
    """
    Analogous to custom BLE characteristics in the Pybricks Service.

    bValue is the 16-bit UUID of the characteristic (3rd and 4th bytes of the 128-bit UUID).
    """


PYBRICKS_USB_INTERFACE_CLASS_REQUEST_MAX_SIZE = 20
"""
The maximum size of data that can be sent or received in a single control transfer
using the PybricksUsbInterfaceClassRequest interface class requests.

This limit comes from the smallest MTU of BLE (23 bytes) minus the 3-byte ATT header.

The Pybricks interface just uses data and doesn't use USB-style descriptors that
include the length. We can get away with this by limiting the size of the data
for each characteristic to be less than or equal to this value. Then, we can
always pass this as the wLength when reading.
"""


class PybricksUsbInEpMessageType(IntEnum):
    RESPONSE = 1
    """
    Analogous to BLE status response.
    """
    EVENT = 2
    """
    Analogous to BLE notification.
    """


class PybricksUsbOutEpMessageType(IntEnum):
    SUBSCRIBE = 1
    """
    Analogous to BLE Client Characteristic Configuration Descriptor (CCCD).
    """
    COMMAND = 2
    """
    Analogous to BLE write without response.
    """
