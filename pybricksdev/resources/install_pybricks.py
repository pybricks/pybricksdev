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


FLASH_START = 0x8000000
FLASH_END = FLASH_START + 1024 * 1024

FLASH_LEGO_START = 0x8008000
FLASH_PYBRICKS_START = 0x80C0000

BLOCK_READ_SIZE = 32
BLOCK_WRITE_SIZE = BLOCK_READ_SIZE * 4

FF = b'\xFF'


def read_flash(address, length):
    """Read a given number of bytes from a given absolute address."""
    return firmware.flash_read(address - FLASH_LEGO_START)[0:length]


def read_flash_int(address):
    """Gets a little endian uint32 integer from the internal flash."""
    return int.from_bytes(read_flash(address, 4), 'little')


def get_pybricks_reset_vector():
    """Gets the boot vector of the pybricks firmware."""

    # Extract reset vector from dual boot firmware.
    with open("_pybricks/firmware.bin") as pybricks_bin_file:
        pybricks_bin_file.seek(4)
        return pybricks_bin_file.read(4)


def get_lego_reset_vector():
    """Gets the boot vector of the original firmware."""

    # Read from lego firmware location.
    reset_vector = read_flash(FLASH_LEGO_START + 4, 4)

    # If it's not pointing at Pybricks, return as is.
    if int.from_bytes(reset_vector, 'little') < FLASH_PYBRICKS_START:
        return reset_vector

    # Otherwise read the reset vector in the dual-booted Pybricks that is
    # already installed, which points to the LEGO firmware.
    return read_flash(FLASH_PYBRICKS_START + 4, 4)


def get_lego_firmware(size, reset_vector):
    """Gets the LEGO firmware with an updated reset vector."""

    bytes_read = 0

    # Yield new blocks until done.
    while bytes_read < size:

        # Read several chunks of 32 bytes into one block.
        block = b''
        for i in range(BLOCK_WRITE_SIZE // BLOCK_READ_SIZE):
            block += firmware.flash_read(bytes_read)
            bytes_read += BLOCK_READ_SIZE

        # The first block is updated with the desired boot vector.
        if bytes_read == BLOCK_WRITE_SIZE:
            block = block[0:4] + reset_vector + block[8:]

        # If we read past the end, cut off the extraneous bytes.
        if bytes_read > size:
            block = block[0: size % BLOCK_WRITE_SIZE]

        # Yield the resulting block.
        yield block


def install(pybricks_hash):
    """Main installation routine."""

    # Start firmware binary verification.
    print("Starting installation script.")
    print("Checking uploaded firmware file.")
    pybricks_hash_calc = uhashlib.sha256()
    pybricks_size = 0

    with open("_pybricks/firmware.bin") as pybricks_bin_file:
        data = b'START'
        while len(data) > 0:
            data = pybricks_bin_file.read(128)
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
    lego_checksum_position = read_flash_int(FLASH_LEGO_START + 0x204)
    lego_size = lego_checksum_position + 4 - FLASH_LEGO_START

    lego_version_position = read_flash_int(FLASH_LEGO_START + 0x200)
    lego_version = read_flash(lego_version_position, 20)
    print("LEGO Firmware version:", lego_version)

    # Verify firmware sizes
    if FLASH_LEGO_START + lego_size >= FLASH_PYBRICKS_START:
        print("LEGO firmware too big.")
        return

    if FLASH_PYBRICKS_START + pybricks_size >= FLASH_END:
        print("Pybricks firmware too big.")
        return

    for block in get_lego_firmware(lego_size, get_pybricks_reset_vector()):
        pass
