# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

"""
Package for TI OAD (Over-the-Air Download) support.

https://software-dl.ti.com/lprf/sdg-latest/html/oad-ble-stack-3.x/oad_profile.html
"""

from pybricksdev.ble.oad._common import OADReturn, oad_uuid
from pybricksdev.ble.oad.control_point import OADControlPoint
from pybricksdev.ble.oad.image_block import OADImageBlock
from pybricksdev.ble.oad.image_identify import OADImageIdentify

__all__ = [
    "OAD_SERVICE_UUID",
    "OADReturn",
    "OADImageBlock",
    "OADControlPoint",
    "OADImageIdentify",
]

OAD_SERVICE_UUID = oad_uuid(0xFFC0)
"""OAD service UUID."""
