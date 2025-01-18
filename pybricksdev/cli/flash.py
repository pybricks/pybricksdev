# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2023 The Pybricks Authors

import asyncio
import hashlib
import json
import logging
import os
import struct
import sys
import zipfile
import zlib
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Dict, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from packaging.version import Version
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from pybricksdev.ble.lwp3 import (
    LEGO_CID,
    LWP3_BOOTLOADER_SERVICE_UUID,
    LWP3_HUB_CHARACTERISTIC_UUID,
    LWP3_HUB_SERVICE_UUID,
)
from pybricksdev.ble.lwp3 import AdvertisementData as HubAdvertisementData
from pybricksdev.ble.lwp3.bootloader import BootloaderAdvertisementData
from pybricksdev.ble.lwp3.bytecodes import HubKind, HubProperty
from pybricksdev.ble.lwp3.messages import (
    FirmwareUpdateMessage,
    HubPropertyRequestUpdate,
    HubPropertyUpdate,
    parse_message,
)
from pybricksdev.ble.nus import NUS_RX_UUID, NUS_TX_UUID
from pybricksdev.ble.pybricks import (
    FW_REV_UUID,
    PNP_ID_UUID,
    PYBRICKS_COMMAND_EVENT_UUID,
    PYBRICKS_SERVICE_UUID,
    SW_REV_UUID,
    Command,
    unpack_pnp_id,
)
from pybricksdev.compile import compile_file
from pybricksdev.connections.lego import REPLHub
from pybricksdev.dfu import flash_dfu
from pybricksdev.firmware import create_firmware_blob
from pybricksdev.flash import BootloaderConnection
from pybricksdev.tools import chunk
from pybricksdev.tools.checksum import xor_bytes

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
        adv: The advertisement data to check.

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

        mpy = await compile_file(
            os.path.dirname(temp.name), os.path.basename(temp.name), abi
        )

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

        profile_ver = await client.read_gatt_char(SW_REV_UUID)

        if Version(profile_ver.decode()) >= Version("1.2.0"):
            try:
                await client.write_gatt_char(
                    PYBRICKS_COMMAND_EVENT_UUID,
                    struct.pack(
                        "<B", Command.PBIO_PYBRICKS_COMMAND_REBOOT_TO_UPDATE_MODE
                    ),
                    response=True,
                )
                # This causes the hub to become disconnected before completing
                # the write request, so we expect an exception here.
            except Exception:
                # REVISIT: Should probably check for more specific exception.
                # However, OK for now since code will just timeout later while
                # scanning for bootloader.
                pass
            else:
                raise RuntimeError("hub did not reset")

        else:
            # older protocol doesn't support this command, so we have to
            # download and run a program

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

    # TODO: add upstream feature to Bleak to allow getting device, adv tuple
    # as return value from find_device_by_filter()
    # https://github.com/hbldh/bleak/issues/1277

    device_adv_map: Dict[str, AdvertisementData] = {}

    def map_and_match(device: BLEDevice, adv: AdvertisementData):
        # capture the adv data for later use
        device_adv_map[device.address] = adv
        return match_hub(hub_kind, adv)

    # scan for hubs in bootloader mode, running official LEGO firmware or
    # running Pybricks firmware

    device = await BleakScanner.find_device_by_filter(
        map_and_match,
        service_uuids=[
            LWP3_BOOTLOADER_SERVICE_UUID,
            LWP3_HUB_SERVICE_UUID,
            PYBRICKS_SERVICE_UUID,
        ],
    )

    if device is None:
        print("timed out", file=sys.stderr)
        return

    adv_data = device_adv_map[device.address]

    # if not already in bootlaoder mode, we need to reboot into bootloader mode
    if LWP3_HUB_SERVICE_UUID in adv_data.service_uuids:
        print("Found hub running official LEGO firmware.")
        await reboot_official_to_bootloader(hub_kind, device)
    elif PYBRICKS_SERVICE_UUID in adv_data.service_uuids:
        print("Found hub running Pybricks firmware.")
        await reboot_pybricks_to_bootloader(hub_kind, device)

    # if not previously in bootlaoder mode, scan again, this time only for bootloader
    if LWP3_BOOTLOADER_SERVICE_UUID not in adv_data.service_uuids:
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


async def flash_nxt(firmware: bytes) -> None:
    """
    Flashes firmware to NXT using the Samba bootloader.

    Args:
        firmware:
            A firmware blob with the NxOS header appended to the end.
    """
    from pybricksdev._vendored.pynxt.firmware import Firmware
    from pybricksdev._vendored.pynxt.flash import FlashController
    from pybricksdev._vendored.pynxt.samba import SambaBrick, SambaOpenError

    # parse the header
    info = Firmware(firmware)

    if info.samba:
        raise ValueError("Firmware is not suitable for flashing.")

    s = SambaBrick()

    try:
        print("Looking for the NXT in SAM-BA mode...")
        s.open(timeout=5)
        print("Brick found!")
    except SambaOpenError as e:
        print(e)
        sys.exit(1)

    print("Flashing firmware...")
    f = FlashController(s)
    f.flash(firmware)

    print("Flashing complete, jumping to 0x100000...")
    f._wait_for_flash()
    s.jump(0x100000)

    print("Firmware started.")
    s.close()


async def flash_ev3(firmware: bytes) -> None:
    """
    Flashes firmware to EV3.

    Args:
        firmware:
            A firmware blob.
    """
    from pybricksdev.connections.ev3 import EV3Bootloader

    # TODO: nice error message and exit(1) if EV3 is not found
    with EV3Bootloader() as bootloader:
        fw, hw = await bootloader.get_version()
        print(f"hwid: {hw}")

        # Erasing doesn't have any feedback so we just use time for the progress
        # bar. The operation runs on the EV3, so the time is the same for everyone.
        async def tick(callback):
            CHUNK = 8000
            SPEED = 256000
            for _ in range(len(firmware) // CHUNK):
                await asyncio.sleep(CHUNK / SPEED)
                callback(CHUNK)

        print("Erasing memory and preparing firmware download...")
        with logging_redirect_tqdm(), tqdm(
            total=len(firmware), unit="B", unit_scale=True
        ) as pbar:
            await asyncio.gather(
                bootloader.erase_and_begin_download(len(firmware)), tick(pbar.update)
            )

        print("Downloading firmware...")
        with logging_redirect_tqdm(), tqdm(
            total=len(firmware), unit="B", unit_scale=True
        ) as pbar:
            await bootloader.download(firmware, pbar.update)

        print("Verifying...", end="", flush=True)
        checksum = await bootloader.get_checksum(0, len(firmware))
        expected_checksum = zlib.crc32(firmware)

        if checksum != expected_checksum:
            print("Bad checksum!")
            exit(1)

        print("OK.")

        print("Restarting EV3...", end="", flush=True)
        await bootloader.start_app()
        print("Done.")


async def flash_firmware(firmware_zip: BinaryIO, new_name: Optional[str]) -> None:
    """
    Command line tool for flashing firmware.

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
    elif hub_kind in [HubKind.BOOST, HubKind.CITY, HubKind.TECHNIC]:
        await flash_ble(hub_kind, firmware, metadata)
    elif hub_kind == HubKind.NXT:
        await flash_nxt(firmware)
    elif hub_kind == HubKind.EV3:
        await flash_ev3(firmware)
    else:
        raise ValueError(f"unsupported hub kind: {hub_kind}")
