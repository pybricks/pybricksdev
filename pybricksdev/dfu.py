# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import os
import sys

from . import _dfu_upload, _dfu_create

from .compile import BUILD_DIR

ADDRESS = 0x08008000
VENDOR_ID = 0x0694
PRODUCT_ID_SPIKE_PRIME = 0x0008


def flash_dfu(firmware_bin, metadata):
    # Select product id
    if metadata['device-id'] == 0:
        product_id = PRODUCT_ID_SPIKE_PRIME
    else:
        print('Unknown hub type', file=sys.stderr)
        exit(1)

    # Create dfu file
    outfile = os.path.join(BUILD_DIR, 'firmware.dfu')
    target = {'address': ADDRESS, 'data': firmware_bin}
    device = "0x{0:04x}:0x{1:04x}".format(VENDOR_ID, product_id)
    _dfu_create.build(outfile, [[target]], device)

    # Init dfu tool
    _dfu_upload.__VID = VENDOR_ID
    _dfu_upload.__PID = product_id
    _dfu_upload.init()
    elements = _dfu_upload.read_dfu_file(outfile)

    # Erase flash
    print("Erasing flash...")
    _dfu_upload.mass_erase()

    # Upload dfu file
    print("Writing new firmware...")
    _dfu_upload.write_elements(elements, True, _dfu_upload.cli_progress)
    _dfu_upload.exit_dfu()
    print("Done.")
