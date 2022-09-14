# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2022 The Pybricks Authors

import asyncio
import hashlib
import json
import logging
import sys
import zipfile
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from packaging.version import Version

from ..ble.lwp3 import (
    LEGO_CID,
    LWP3_BOOTLOADER_SERVICE_UUID,
    LWP3_HUB_CHARACTERISTIC_UUID,
    LWP3_HUB_SERVICE_UUID,
)
from ..ble.lwp3 import AdvertisementData as HubAdvertisementData
from ..ble.lwp3.bootloader import BootloaderAdvertisementData
from ..ble.lwp3.bytecodes import HubKind, HubProperty
from ..ble.lwp3.messages import (
    FirmwareUpdateMessage,
    HubPropertyRequestUpdate,
    HubPropertyUpdate,
    parse_message,
)
from ..ble.nus import NUS_RX_UUID, NUS_TX_UUID
from ..ble.pybricks import (
    FW_REV_UUID,
    PNP_ID_UUID,
    PYBRICKS_SERVICE_UUID,
    unpack_pnp_id,
)
from ..compile import compile_file
from ..connections.lego import REPLHub
from ..dfu import flash_dfu
from ..firmware import create_firmware_blob
from ..flash import BootloaderConnection
from ..tools import chunk
from ..tools.checksum import xor_bytes

logger = logging.getLogger(__name__)


REBOOT_SCRIPT = """
from pybricks.hubs import ThisHub
from pybricks.tools import wait

hub = ThisHub()

# without delay, hub will reboot before we receive last checksum
wait(500)
hub.system.reset(2)
"""


def match_hub(hub_kind: HubKind, adv: AdvertisementData) -> bool:
    """
    Advertisement data matching function for filtering supported hubs.

    Args:
        hub_kind: The hub type ID to match.
        adv: The advertisemet data to check.

    Returns:
        ``True`` if *adv* matches the criteria, otherwise ``False``.
    """
    # LEGO firmware uses manufacturer-specific data

    lego_data = adv.manufacturer_data.get(LEGO_CID)

    if lego_data:
        if LWP3_BOOTLOADER_SERVICE_UUID in adv.service_uuids:
            bl_data = BootloaderAdvertisementData(lego_data)
            return bl_data.hub_kind == hub_kind

        if LWP3_HUB_SERVICE_UUID in adv.service_uuids:
            hub_data = HubAdvertisementData(lego_data)
            return hub_data.hub_kind == hub_kind

    # Pybricks firmware uses Device Information service data

    pnp_id_data = adv.service_data.get(PNP_ID_UUID)

    if pnp_id_data and PYBRICKS_SERVICE_UUID in adv.service_uuids:
        _, _, pid, _ = unpack_pnp_id(pnp_id_data)
        return pid == hub_kind

    return False


async def download_and_run(client: BleakClient, script: str, abi: int) -> None:
    """
    Downloads and runs a script on a hub running Pybricks firmware.

    Args:
        client: The Bluetooth connection to the hub.
        script: The script to be compiled and run.
        abi: The MPY ABI version.
    """
    with NamedTemporaryFile("w", suffix=".py") as temp:
        temp.write(script)

        # file has to be closed so mpy-cross can open it
        temp.file.close()

        mpy = await compile_file(temp.name, abi)

    recv_queue = asyncio.Queue()

    def on_notify(_h, data: bytes):
        recv_queue.put_nowait(data)

    # BOOST Move hub has hardware limit of MTU == 23 so it has to have data
    # split into smaller chunks
    write_size = 20 if client.mtu_size < 100 else 100

    async def write_chunk(data: bytes):
        """
        Writes a chunk of data and waits for a checksum reply.

        Args:
            data: The data.

        Raises:
            RuntimeError: If the returned checksum did not match.
            asyncio.TimeoutError: If no reply was received.
        """
        checksum = xor_bytes(data, 0)

        for c in chunk(data, write_size):
            await client.write_gatt_char(NUS_RX_UUID, c)

        reply: bytes = await asyncio.wait_for(recv_queue.get(), 1)

        if reply[0] != checksum:
            raise RuntimeError(
                f"bad checksum, expecting {checksum:02X} but received {reply[0]:02X}"
            )

    await client.start_notify(NUS_TX_UUID, on_notify)

    # communication protocol is write file size, then send file in 100 byte chunks
    try:
        await write_chunk(len(mpy).to_bytes(4, "little"))

        for c in chunk(mpy, 100):
            await write_chunk(c)

    finally:
        await client.stop_notify(NUS_TX_UUID)


async def reboot_official_to_bootloader(hub_kind: HubKind, device: BLEDevice) -> None:
    """
    Connects to a hub running official LEGO firmware and sends a message to
    reboot in firmware update mode.
    """
    async with BleakClient(device) as client:

        # give bluetooth stack time to settle
        await asyncio.sleep(1)

        fw_ver_future = asyncio.get_running_loop().create_future()

        def on_notify(_h, data: bytes):
            msg = parse_message(data)

            logger.debug("%s", str(msg))

            if (
                isinstance(msg, HubPropertyUpdate)
                and msg.prop == HubProperty.FW_VERSION
            ):
                fw_ver_future.set_result(msg.value)

        await client.start_notify(LWP3_HUB_CHARACTERISTIC_UUID, on_notify)
        await client.write_gatt_char(
            LWP3_HUB_CHARACTERISTIC_UUID,
            HubPropertyRequestUpdate(HubProperty.FW_VERSION),
            # work around city hub bluetooth bug on linux
            response=hub_kind == HubKind.CITY,
        )

        fw_ver = await asyncio.wait_for(fw_ver_future, 5)
        print(f"Hub is running firmware v{fw_ver}.")

        print("Rebooting in update mode...")

        await client.write_gatt_char(
            LWP3_HUB_CHARACTERISTIC_UUID, FirmwareUpdateMessage()
        )


async def reboot_pybricks_to_bootloader(hub_kind: HubKind, device: BLEDevice) -> None:
    """
    Connects to a hub running Pybricks firmware and sends a message to
    reboot in firmware update mode.
    """
    async with BleakClient(device) as client:
        # Work around BlueZ limitation.
        if client.__class__.__name__ == "BleakClientBlueZDBus":
            client._mtu_size = 23 if hub_kind == HubKind.BOOST else 158

        # give bluetooth stack time to settle
        await asyncio.sleep(1)

        fw_ver = await client.read_gatt_char(FW_REV_UUID)
        fw_ver = fw_ver.decode()
        print(f"Hub is running firmware v{fw_ver}.")

        print("Rebooting in update mode...")

        # HACK: there isn't a proper way to get the MPY ABI version from hub
        # so we use heuristics on the firmware version
        abi = 6 if Version(fw_ver) >= Version("3.2.0b2") else 5

        await download_and_run(client, REBOOT_SCRIPT, abi)


async def flash_ble(hub_kind: HubKind, firmware: bytes, metadata: dict):
    """
    Flashes firmware to the hub using Bluetooth Low Energy.

    The hub has to be advertising and can be running official LEGO firmware,
    Pybricks firmware or be in bootloader mode.

    Args:
        hub_kind: The hub type ID. Only hubs matching this ID will be discovered.
        firmware: The raw firmware binary blob.
        metadata: The firmware metadata from the firmware.zip file.
    """

    print(f"Searching for {hub_kind.name} hub...")

    # scan for hubs in bootloader mode, running official LEGO firmware or
    # running Pybricks firmware

    device = await BleakScanner.find_device_by_filter(
        lambda _d, a: match_hub(hub_kind, a),
        service_uuids=[
            LWP3_BOOTLOADER_SERVICE_UUID,
            LWP3_HUB_SERVICE_UUID,
            PYBRICKS_SERVICE_UUID,
        ],
    )

    if device is None:
        print("timed out", file=sys.stderr)
        return

    # if not already in bootlaoder mode, we need to reboot into bootloader mode
    if LWP3_HUB_SERVICE_UUID in device.metadata["uuids"]:
        print("Found hub running official LEGO firmware.")
        await reboot_official_to_bootloader(hub_kind, device)
    elif PYBRICKS_SERVICE_UUID in device.metadata["uuids"]:
        print("Found hub running Pybricks firmware.")
        await reboot_pybricks_to_bootloader(hub_kind, device)

    # if not previously in bootlaoder mode, scan again, this time only for bootloader
    if LWP3_BOOTLOADER_SERVICE_UUID not in device.metadata["uuids"]:
        device = await BleakScanner.find_device_by_filter(
            lambda _d, a: match_hub(hub_kind, a),
            service_uuids=[
                LWP3_BOOTLOADER_SERVICE_UUID,
            ],
        )

        if device is None:
            print("timed out", file=sys.stderr)
            return

    print("Found:", device)
    updater = BootloaderConnection()
    await updater.connect(device)
    print("Erasing flash and starting update")
    await updater.flash(firmware, metadata)


async def flash_firmware(firmware_zip: BinaryIO, new_name: Optional[str]) -> None:
    """
    Command line tool for flasing firmware.

    Args:
        firmware_zip: The path to the ``firmware.zip`` file.
        new_name: Optional custom hub name to be applied to the firmware image.
    """

    print("Creating firmware...")

    # REVISIT: require accepting license agreement either interactively or by command line option
    firmware, metadata, license = await create_firmware_blob(firmware_zip, new_name)
    hub_kind = HubKind(metadata["device-id"])

    if hub_kind in (HubKind.TECHNIC_SMALL, HubKind.TECHNIC_LARGE):
        try:
            # Connect to the hub and exit the runtime.
            hub = REPLHub()
            await hub.connect()
            await hub.reset_hub()

            # Upload installation script.
            archive = zipfile.ZipFile(firmware_zip)
            await hub.exec_line("import uos; uos.mkdir('_firmware')")
            await hub.upload_file(
                "_firmware/install_pybricks.py",
                bytearray(archive.open("install_pybricks.py").read()),
            )

            extended_metadata = metadata.copy()

            # Add extended metadata needed by install_pybricks.py
            extended_metadata["firmware-sha256"] = hashlib.sha256(firmware).hexdigest()

            # Upload metadata.
            await hub.upload_file(
                "_firmware/firmware.metadata.json",
                json.dumps(extended_metadata, indent=4).encode(),
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
        await flash_ble(hub_kind, firmware, metadata)
