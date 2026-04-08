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

from pybricksdev import resources
from pybricksdev._vendored import dfu_create, dfu_upload
from pybricksdev.ble.lwp3.bytecodes import HubKind
from pybricksdev.firmware import AnyFirmwareMetadata
from pybricksdev.usb import (
    LEGO_USB_VID,
    MINDSTORMS_INVENTOR_DFU_USB_PID,
    SPIKE_ESSENTIAL_DFU_USB_PID,
    SPIKE_PRIME_DFU_USB_PID,
)

BOOTLOADER_SIZE_32K = 32 * 1024
BOOTLOADER_SIZE_64K = 64 * 1024
FLASH_BASE_ADDRESS = 0x08000000
FLASH_SIZE = 1 * 1024 * 1024


ALL_PIDS = {
    MINDSTORMS_INVENTOR_DFU_USB_PID: HubKind.TECHNIC_LARGE,
    SPIKE_ESSENTIAL_DFU_USB_PID: HubKind.TECHNIC_SMALL,
    SPIKE_PRIME_DFU_USB_PID: HubKind.TECHNIC_LARGE,
}
ALL_DEVICES = [f"{LEGO_USB_VID:04x}:{pid:04x}" for pid in ALL_PIDS.keys()]


def _get_bootloader_size(pid: int, bcd_device: int | None) -> int:
    """Gets bootloader size for the connected DFU device."""
    # New hardware revision of SPIKE Prime released in 2026 has a larger bootloader.
    if pid == SPIKE_PRIME_DFU_USB_PID and bcd_device == 0x0300:
        return BOOTLOADER_SIZE_64K

    return BOOTLOADER_SIZE_32K


def _get_firmware_region(bootloader_size: int) -> tuple[int, int]:
    """Gets firmware flash address and size from bootloader size."""
    return FLASH_BASE_ADDRESS + bootloader_size, FLASH_SIZE - bootloader_size


def _get_dfu_util() -> ContextManager[os.PathLike[str] | str]:
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


def _get_dfu_device_info(dfu_util: os.PathLike[str] | str) -> tuple[str, int]:
    """
    Gets the VID:PID and bootloader size of a connected LEGO DFU device.

    Returns: The first matching LEGO DFU device from ``dfu-util --list``

    Raises: RuntimeError: No matching hubs found.
    """
    proc = run([dfu_util, "--list"], stdout=PIPE, check=True)

    for line in proc.stdout.splitlines():
        if not line.startswith(b"Found DFU:"):
            continue

        dev_id = line[line.index(b"[") + 1 : line.index(b"]")].decode()

        if dev_id in ALL_DEVICES:
            pid = int(dev_id.split(":", maxsplit=1)[1], 16)
            bcd_device = None

            try:
                i = line.index(b"ver=") + 4
                bcd_device = int(line[i : i + 4].decode(), 16)
            except (ValueError, IndexError):
                pass

            return dev_id, _get_bootloader_size(pid, bcd_device)

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
            dev_id, bootloader_size = _get_dfu_device_info(dfu_util)
            firmware_address, firmware_size = _get_firmware_region(bootloader_size)
            file.close()

            # dfu-util won't overwrite existing files so we have to do that first
            os.remove(file.name)

            exit(
                call(
                    [
                        dfu_util,
                        "--device",
                        f",{dev_id}",
                        "--alt",
                        "0",
                        "--dfuse-address",
                        f"{firmware_address}:{firmware_size}",
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
            dev_id, bootloader_size = _get_dfu_device_info(dfu_util)
            firmware_address, _ = _get_firmware_region(bootloader_size)
            file.close()

            exit(
                call(
                    [
                        dfu_util,
                        "--device",
                        f",{dev_id}",
                        "--alt",
                        "0",
                        "--dfuse-address",
                        f"{firmware_address}:leave",
                        "--download",
                        file.name,
                    ]
                )
            )


def flash_dfu(firmware_bin: bytes, metadata: AnyFirmwareMetadata) -> None:
    """Flashes a firmware file using DFU."""

    with TemporaryDirectory() as out_dir:
        outfile = os.path.join(out_dir, "firmware.dfu")

        try:
            # Determine correct product ID

            devices = dfu_upload.get_dfu_devices(idVendor=LEGO_USB_VID)
            if not devices:
                print(
                    "No DFU devices found.",
                    "Make sure hub is in DFU mode and connected with USB.",
                    file=sys.stderr,
                )
                exit(1)

            product_id = int(devices[0].idProduct)
            bcd_device = int(devices[0].bcdDevice)
            if product_id not in ALL_PIDS:
                print(f"Unknown USB product ID: {product_id:04X}", file=sys.stderr)
                exit(1)

            if ALL_PIDS[product_id] != metadata["device-id"]:
                print("Incorrect firmware type for this hub", file=sys.stderr)
                exit(1)

            bootloader_size = _get_bootloader_size(product_id, bcd_device)
            firmware_address, _ = _get_firmware_region(bootloader_size)
            target: dfu_create.Image = {
                "address": firmware_address,
                "data": firmware_bin,
            }

            # Create dfu file
            device = "0x{0:04x}:0x{1:04x}".format(LEGO_USB_VID, product_id)
            dfu_create.build(outfile, [[target]], device)

            # Init dfu tool
            dfu_upload.__VID = LEGO_USB_VID
            dfu_upload.__PID = product_id
            dfu_upload.init()
            elements = dfu_upload.read_dfu_file(outfile)
            assert elements is not None

            # Erase flash
            print("Erasing flash...")
            dfu_upload.mass_erase()

            # Upload dfu file
            print("Writing new firmware...")
            dfu_upload.write_elements(elements, True, dfu_upload.cli_progress)
            dfu_upload.exit_dfu()
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
                dev_id, bootloader_size = _get_dfu_device_info(dfu_util)
                firmware_address, _ = _get_firmware_region(bootloader_size)

                with open(os.path.join(out_dir, "firmware.bin"), "wb") as bin_file:
                    bin_file.write(firmware_bin)

                exit(
                    call(
                        [
                            dfu_util,
                            "--device",
                            f",{dev_id}",
                            "--alt",
                            "0",
                            # We have to use dfuse option to be able to use
                            # "leave" to exit DFU mode after flashing. --reset
                            # doesn't work on Windows, so we can't use a .dfu file
                            "--dfuse-address",
                            f"{firmware_address}:leave",
                            "--download",
                            bin_file.name,
                        ]
                    )
                )
