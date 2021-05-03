# SPDX-License-Identifier: MIT
# Copyright (c) 2018-2020 The Pybricks Authors
#
# Pybricks installer for SPIKE Prime and MINDSTORMS Robot Inventor.


import firmware
import ubinascii
import umachine
import utime

def install(pybricks_firmware_size, pybricks_boot_vector):
    print(pybricks_firmware_size, pybricks_boot_vector)
