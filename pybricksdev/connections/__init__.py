# SPDX-License-Identifier: MIT
# Copyright (c) 2023 The Pybricks Authors

import enum


class ConnectionState(enum.Enum):
    """
    Indicates state of a connection.
    """

    CONNECTING = enum.auto()
    """
    The device is in the process of connecting.
    """
    CONNECTED = enum.auto()
    """
    The device is connected.
    """
    DISCONNECTING = enum.auto()
    """
    The device is in the process of disconnecting.
    """
    DISCONNECTED = enum.auto()
    """
    The device is disconnected.
    """
