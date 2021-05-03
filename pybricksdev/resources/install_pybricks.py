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


FLASH_LEGO_START = 0x8008000
FLASH_PYBRICKS_START = 0x80C0000
FLASH_READ_OFFSET = FLASH_LEGO_START


FF = b'\xFF'


def read_flash(address, length):
    """Read a given number of bytes from a given absolute address."""
    return firmware.flash_read(address - FLASH_READ_OFFSET)[0:length]


def get_base_firmware_reset_vector():
    """Gets the boot vector of the original firmware."""

    # Read from base firmware location.
    firmware_reset_vector = read_flash(FLASH_LEGO_START + 4, 4)

    # If it's not pointing at Pybricks, return as is.
    if int.from_bytes(firmware_reset_vector, 'little') < FLASH_PYBRICKS_START:
        return firmware_reset_vector

    # Otherwise read the boot vector in Pybricks.
    return read_flash(FLASH_PYBRICKS_START + 4, 4)


def install(pybricks_firmware_hash):
    """Main installation routine."""

    # Start firmware binary verification.
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

    # Compare hash against given value.
    if fw_hash.digest() == pybricks_firmware_hash:
        print("Firmware checksum is correct!")
    else:
        print("Bad firmware file. Stopping.")
        return

    # Get firmware information.
    print("Getting firmware info.")
    print(get_base_firmware_reset_vector())
