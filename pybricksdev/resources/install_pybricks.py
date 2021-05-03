# SPDX-License-Identifier: MIT
# Copyright (c) 2018-2020 The Pybricks Authors
#
# Pybricks installer for SPIKE Prime and MINDSTORMS Robot Inventor.


import firmware
import ubinascii
import umachine
import utime
import uhashlib
import uos

def install(pybricks_firmware_hash):
    print("Starting installation script.")

    print("Checking uploaded firmware file.")
    fw_hash = uhashlib.sha256()
    fw_size = 0

    with open("_pybricks/firmware.bin") as fw:
        data = b'START'
        while len(data) > 0:
            data = fw.read(128)
            fw_size += len(data)
            fw_hash.update(data)

    if fw_hash.digest() == pybricks_firmware_hash:
        print("Firmware checksum is correct!")
    else:
        print("Bad firmware file. Stopping.")
        return

    print("Removing installation files.")
    uos.remove("_pybricks/__init__.py")
    uos.remove("_pybricks/install.py")
    uos.remove("_pybricks/firmware.bin")
