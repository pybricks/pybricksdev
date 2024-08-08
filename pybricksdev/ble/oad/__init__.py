# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

"""
Package for TI OAD (Over-the-Air Download) support.

https://software-dl.ti.com/lprf/sdg-latest/html/oad-ble-stack-3.x/oad_profile.html
"""

from ._common import oad_uuid

__all__ = ["OAD_SERVICE_UUID"]

OAD_SERVICE_UUID = oad_uuid(0xFFC0)
"""OAD service UUID."""
