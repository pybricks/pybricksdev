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

FLASH_SIZE = 0x8000000 + 1024 * 1024 - FLASH_LEGO_START

FF = b'\xFF'


def read_flash(address, length):
    """Read a given number of bytes from a given absolute address."""
    return firmware.flash_read(address - FLASH_READ_OFFSET)[0:length]


def read_flash_int(address):
    """Gets a little endian uint32 integer from the internal flash."""
    return int.from_bytes(read_flash(address, 4), 'little')


def get_base_firmware_reset_vector():
    """Gets the boot vector of the original firmware."""

    # Read from base firmware location.
    firmware_reset_vector = read_flash(FLASH_LEGO_START + 4, 4)

    # If it's not pointing at Pybricks, return as is.
    if int.from_bytes(firmware_reset_vector, 'little') < FLASH_PYBRICKS_START:
        return firmware_reset_vector

    # Otherwise read the boot vector in Pybricks.
    return read_flash(FLASH_PYBRICKS_START + 4, 4)


def install(pybricks_hash):
    """Main installation routine."""

    # Start firmware binary verification.
    print("Starting installation script.")
    print("Checking uploaded firmware file.")
    pybricks_hash_calc = uhashlib.sha256()
    pybricks_size = 0

    with open("_pybricks/firmware.bin") as fw:
        data = b'START'
        while len(data) > 0:
            data = fw.read(128)
            pybricks_size += len(data)
            pybricks_hash_calc.update(data)

    # Compare hash against given value.
    if pybricks_hash_calc.digest() == pybricks_hash:
        print("Firmware checksum is correct!")
    else:
        print("Bad firmware file. Stopping.")
        return

    # Get firmware information.
    print("Getting firmware info.")
    version_position = read_flash_int(FLASH_LEGO_START + 0x200)
    checksum_position = read_flash_int(FLASH_LEGO_START + 0x204)
    base_firmware_size = checksum_position + 4 - FLASH_READ_OFFSET
    version = read_flash(version_position, 20)

    # DEBUG
    print(version)
    print(base_firmware_size)
    print(get_base_firmware_reset_vector())
