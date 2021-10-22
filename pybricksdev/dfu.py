# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2021 The Pybricks Authors

import errno
import os
import platform
import sys

from contextlib import nullcontext
from importlib.resources import path
from subprocess import DEVNULL, PIPE, call, check_call, run
from tempfile import TemporaryDirectory
from typing import BinaryIO, ContextManager

from usb.core import NoBackendError, USBError

from . import _dfu_upload, _dfu_create, resources
from .ble.lwp3.bytecodes import HubKind

FIRMWARE_ADDRESS = 0x08008000
FIRMWARE_SIZE = 1 * 1024 * 1024 - 32 * 1024  # 1MiB - 32KiB
LEGO_VID = 0x0694
SPIKE_PRIME_PID = 0x0008
SPIKE_ESSENTIAL_PID = 0x000C
MINDSTORMS_INVENTOR_PID = 0x0011

ALL_PIDS = {
    MINDSTORMS_INVENTOR_PID: HubKind.TECHNIC_LARGE,
    SPIKE_ESSENTIAL_PID: HubKind.TECHNIC_SMALL,
    SPIKE_PRIME_PID: HubKind.TECHNIC_LARGE,
}
ALL_DEVICES = [f"{LEGO_VID:04x}:{pid:04x}" for pid in ALL_PIDS.keys()]


def _get_dfu_util() -> ContextManager[os.PathLike]:
    """Gets ``dfu-util`` command line tool path.

    Returns: Context manager containing the path. The path may no longer be
        valid after the context manager exits.
    """
    # Use embedded .exe for Windows
    if platform.system() == "Windows":
        return path(resources, resources.DFU_UTIL_EXE)

    # otherwise use system provided dfu-util
    dfu_util = "dfu-util"

    try:
        check_call([dfu_util, "--version"], stdout=DEVNULL)
    except FileNotFoundError:
        print(
            "No working DFU found.",
            "Please install libusb or ensure dfu-util is in PATH.",
            file=sys.stderr,
        )
        exit(1)

    return nullcontext(dfu_util)


def _get_vid_pid(dfu_util: os.PathLike) -> str:
    """
    Gets the VID and PID of a connected LEGO DFU device.

    Returns: The first matching LEGO DFU device from ``dfu-util --list``

    Raises: RuntimeError: No matching hubs found.
    """
    proc = run([dfu_util, "--list"], stdout=PIPE, check=True)

    for line in proc.stdout.splitlines():
        if not line.startswith(b"Found DFU:"):
            continue

        dev_id = line[line.index(b"[") + 1 : line.index(b"]")].decode()

        if dev_id in ALL_DEVICES:
            return dev_id

    raise RuntimeError("No LEGO DFU USB device found")


def backup_dfu(file: BinaryIO) -> None:
    """Backs up device data via DFU.

    Args:
        file:
            file where firmware (MCU flash memory) will be saved
    """
    try:
        # TODO: implement this using pydfu
        raise NoBackendError
    except NoBackendError:
        # if libusb was not found, try using dfu-util command line tool

        with _get_dfu_util() as dfu_util:

            file.close()

            # dfu-util won't overwrite existing files so we have to do that first
            os.remove(file.name)

            exit(
                call(
                    [
                        dfu_util,
                        "--device",
                        f",{_get_vid_pid(dfu_util)}",
                        "--alt",
                        "0",
                        "--dfuse-address",
                        f"{FIRMWARE_ADDRESS}:{FIRMWARE_SIZE}",
                        "--upload",
                        file.name,
                    ]
                )
            )


def restore_dfu(file: BinaryIO) -> None:
    """Restores flash memory from a file (raw data, not .dfu file).

    Args:
        file: the file that contains the firmware data
    """
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0, os.SEEK_SET)

    if size < 512:
        raise ValueError("File is too small to be a valid firmware file")

    try:
        # TODO: implement this using pydfu
        raise NoBackendError
    except NoBackendError:
        # if libusb was not found, try using dfu-util command line tool

        with _get_dfu_util() as dfu_util:

            file.close()

            exit(
                call(
                    [
                        dfu_util,
                        "--device",
                        f",{_get_vid_pid(dfu_util)}",
                        "--alt",
                        "0",
                        "--dfuse-address",
                        f"{FIRMWARE_ADDRESS}:leave",
                        "--download",
                        file.name,
                    ]
                )
            )


def flash_dfu(firmware_bin: bytes, metadata: dict) -> None:
    """Flashes a firmware file using DFU."""

    with TemporaryDirectory() as out_dir:
        outfile = os.path.join(out_dir, "firmware.dfu")
        target = {"address": FIRMWARE_ADDRESS, "data": firmware_bin}

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
            if product_id not in ALL_PIDS:
                print(f"Unknown USB product ID: {product_id:04X}", file=sys.stderr)
                exit(1)

            if ALL_PIDS[product_id] != metadata["device-id"]:
                print("Incorrect firmware type for this hub", file=sys.stderr)
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
            if e.errno != errno.EACCES or platform.system() != "Linux":
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

            with _get_dfu_util() as dfu_util:

                dev_id = _get_vid_pid(dfu_util)

                _dfu_create.build(outfile, [[target]], dev_id)

                exit(
                    call(
                        [
                            dfu_util,
                            "--device",
                            f",{dev_id}",
                            "--alt",
                            "0",
                            "--download",
                            outfile,
                        ]
                    )
                )
