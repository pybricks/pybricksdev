# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors


def oad_uuid(uuid16: int) -> str:
    """
    Converts a 16-bit UUID to the TI OAD 128-bit UUID format.
    """
    return "f000{:04x}-0451-4000-b000-000000000000".format(uuid16)
