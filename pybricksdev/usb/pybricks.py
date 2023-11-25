# SPDX-License-Identifier: MIT
# Copyright (c) 2025 The Pybricks Authors

"""
Pybricks-specific USB protocol.
"""

from enum import IntEnum


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
