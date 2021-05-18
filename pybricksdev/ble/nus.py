# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

"""This module is used for Bluetooth Low Energy communications with devices
that provide the Nordic UART Service (NUS).
"""


def _nus_uuid(short: int) -> str:
    """Get a 128-bit UUID from a ``short`` UUID.

    Args:
        short: The 16-bit UUID.

    Returns:
        The 128-bit UUID as a string.
    """
    return f"6e40{short:04x}-b5a3-f393-e0a9-e50e24dcca9e"


NUS_SERVICE_UUID = _nus_uuid(0x0001)
"""The Nordic UART service UUID."""

NUS_RX_UUID = _nus_uuid(0x0002)
"""The Nordic UART receive characteristic UUID.

This is Rx from the point of view of the peripheral and Tx from the point of view
of the central. The central will write to this characteristic.
"""

NUS_TX_UUID = _nus_uuid(0x0003)
"""The Nordic UART transmit characteristic UUID.

This is Tx from the point of view of the peripheral and Rx from the point of view
of the central. The central will receive notifications from this characteristic.
"""
