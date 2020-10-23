# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import errno
import os
import platform
import sys

from subprocess import DEVNULL, call, check_call
from tempfile import TemporaryDirectory

from usb.core import NoBackendError, USBError

from . import _dfu_upload, _dfu_create
from .hubs import HubTypeId

ADDRESS = 0x08008000
LEGO_VID = 0x0694
SPIKE_PRIME_PID = 0x0008
MINDSTORMS_INVENTOR_PID = 0x0011


def flash_dfu(firmware_bin: bytes, metadata: dict) -> None:
    """Flashes a firmware file using DFU."""

    if metadata["device-id"] != HubTypeId.PRIME_HUB:
        print('Unknown hub type:', metadata["device-id"], file=sys.stderr)
        exit(1)

    with TemporaryDirectory() as out_dir:
        outfile = os.path.join(out_dir, 'firmware.dfu')
        target = {'address': ADDRESS, 'data': firmware_bin}

        try:
            # Determine correct product ID

            devices = _dfu_upload.get_dfu_devices(idVendor=LEGO_VID)
            if not devices:
                print(
                    "No DFU devices found.",
                    "Make sure hub is in DFU mode and connected with USB.",
                    file=sys.stderr,
                )
                exit(1)

            product_id = devices[0].idProduct
            if (product_id != SPIKE_PRIME_PID and
                    product_id != MINDSTORMS_INVENTOR_PID):
                print(f"Unknown USB product ID: {product_id:04X}", file=sys.stderr)
                exit(1)

            # Create dfu file
            device = "0x{0:04x}:0x{1:04x}".format(LEGO_VID, product_id)
            _dfu_create.build(outfile, [[target]], device)

            # Init dfu tool
            _dfu_upload.__VID = LEGO_VID
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
        except USBError as e:
            if e.errno != errno.EACCES or platform.system() != 'Linux':
                # not expecting other errors
                raise

            print(
                "Permission to access USB device denied. Did you install udev rules?",
                file=sys.stderr,
            )
            print(
                "Run `pybricksdev udev | sudo tee /etc/udev/rules.d/99-pybricksdev.rules` then try again.",
                file=sys.stderr,
            )
            exit(1)
        except NoBackendError:
            # if libusb was not found, try using dfu-util command line tool

            # prefer dfu-util-static for Windows
            dfu_util = "dfu-util-static"

            try:
                check_call([dfu_util, "--version"], stdout=DEVNULL)
            except FileNotFoundError:
                # fall back to dfu-util if dfu-util-static was not found
                dfu_util = "dfu-util"
                try:
                    check_call([dfu_util, "--version"], stdout=DEVNULL)
                except FileNotFoundError:
                    print("No working DFU found.",
                          "Please install libusb or ensure dfu-util is in PATH.",
                          file=sys.stderr)
                    exit(1)

            spike_device = f"0x{LEGO_VID:04x}:0x{SPIKE_PRIME_PID:04x}"
            inventor_device = f"0x{LEGO_VID:04x}:0x{MINDSTORMS_INVENTOR_PID:04x}"

            # device product ID doesn't matter here since we are using the
            # --device command line option below.
            _dfu_create.build(outfile, [[target]], spike_device)

            exit(call([
                dfu_util,
                "--device",
                f"{spike_device},{inventor_device}",
                "--alt",
                "0",
                "--download",
                outfile
            ]))
