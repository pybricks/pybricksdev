# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2022 The Pybricks Authors

import asyncio
import json
import zipfile
from typing import BinaryIO, Optional

from ..ble import find_device
from ..ble.lwp3 import LWP3_BOOTLOADER_SERVICE_UUID
from ..ble.lwp3.bytecodes import HubKind
from ..connections import REPLHub
from ..dfu import flash_dfu
from ..flash import BootloaderConnection, create_firmware


async def flash_firmware(firmware_zip: BinaryIO, hub_name: Optional[str]) -> None:
    """
    Command line tool for flasing firmware.

    Args:
        firmware_zip: The path to the ``firmware.zip`` file.
        hub_name: Optional custom hub name.
    """

    print("Creating firmware...")

    firmware, metadata = await create_firmware(firmware_zip, hub_name)

    if metadata["device-id"] in (HubKind.TECHNIC_SMALL, HubKind.TECHNIC_LARGE):
        try:
            # Connect to the hub and exit the runtime.
            hub = REPLHub()
            await hub.connect()
            await hub.reset_hub()

            # Upload installation script.
            archive = zipfile.ZipFile(firmware)
            await hub.exec_line("import uos; uos.mkdir('_firmware')")
            await hub.upload_file(
                "_firmware/install_pybricks.py",
                bytearray(archive.open("install_pybricks.py").read()),
            )

            # Upload metadata.
            await hub.upload_file(
                "_firmware/firmware.metadata.json",
                json.dumps(metadata, indent=4).encode(),
            )

            # Upload Pybricks firmware
            await hub.upload_file("_firmware/firmware.bin", firmware)

            # Run installation script
            print("Installing firmware")
            await hub.exec_line("from _firmware.install_pybricks import install")
            await hub.exec_paste_mode("install()")

        except OSError:
            print("Could not find hub in standard firmware mode. Trying DFU.")
            flash_dfu(firmware, metadata)
    else:
        print("Searching for LEGO Bootloader...")

        try:
            device = await find_device(service=LWP3_BOOTLOADER_SERVICE_UUID)
        except asyncio.TimeoutError:
            print("timed out")
            return

        print("Found:", device)
        updater = BootloaderConnection()
        await updater.connect(device)
        print("Erasing flash and starting update")
        await updater.flash(firmware, metadata)
