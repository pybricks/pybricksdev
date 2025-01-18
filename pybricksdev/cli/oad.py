# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

import asyncio
from typing import BinaryIO

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from pybricksdev.ble.lwp3 import LEGO_CID, LWP3_HUB_SERVICE_UUID, HubKind
from pybricksdev.ble.oad import (
    OADControlPoint,
    OADImageBlock,
    OADImageIdentify,
    OADReturn,
)
from pybricksdev.ble.oad.control_point import (
    OAD_LEGO_MARIO_DEVICE_TYPE,
    OAD_LEGO_TECHNIC_MOVE_DEVICE_TYPE,
)
from pybricksdev.ble.oad.firmware import parse_oad_header

__all__ = ["dump_oad_info", "flash_oad_image"]

# hubs known to use TI OAD
_OAD_HUBS = [HubKind.MARIO, HubKind.LUIGI, HubKind.PEACH, HubKind.TECHNIC_MOVE]

_KNOWN_DEVICE_TYPES = {
    OAD_LEGO_MARIO_DEVICE_TYPE: "LEGO Mario",
    OAD_LEGO_TECHNIC_MOVE_DEVICE_TYPE: "LEGO Technic Move Hub",
}


def _match_oad_hubs(dev: BLEDevice, adv: AdvertisementData):
    """
    Matches BLE advertisement data that has LEGO manufacturer data and
    is a known OAD hub.
    """
    if LEGO_CID not in adv.manufacturer_data:
        return False

    # maybe not necessary but helps ensure that mfg data is the expected layout
    if LWP3_HUB_SERVICE_UUID not in adv.service_uuids:
        return False

    kind = HubKind(adv.manufacturer_data[LEGO_CID][1])

    return kind in _OAD_HUBS


async def flash_oad_image(firmware: BinaryIO) -> None:
    """
    Connects to an OAD hub and flashes a firmware image to it.
    """

    firmware_bytes = firmware.read()

    header = parse_oad_header(firmware_bytes)

    print("Scanning for hubs...")
    device = await BleakScanner.find_device_by_filter(_match_oad_hubs)

    if device is None:
        print("No OAD device found")
        return

    disconnect_event = asyncio.Event()

    def on_disconnect(_):
        disconnect_event.set()

    # long timeout in case pairing is needed
    async with asyncio.timeout(60), BleakClient(
        device, on_disconnect
    ) as client, OADImageIdentify(client) as image_identify, OADControlPoint(
        client
    ) as control_point:
        image_block = OADImageBlock(client)

        print(f"Connected to {device.name}")

        dev_type = await control_point.get_device_type()

        # TODO: match this based on firmware image target
        if dev_type not in _KNOWN_DEVICE_TYPES:
            print(f"Unsupported device type: {dev_type:08X}")
            return

        block_size = await control_point.get_oad_block_size()

        status = await image_identify.validate(
            header.image_id,
            header.bmi_version,
            header.header_version,
            header.image_info,
            header.image_length,
            header.software_version,
        )
        if status != OADReturn.SUCCESS:
            print(f"Failed to validate image: {status.name}")
            return

        sent_blocks = set()

        print("Flashing...")

        with logging_redirect_tqdm(), tqdm(
            total=header.image_length, unit="B", unit_scale=True
        ) as pbar:
            async with asyncio.TaskGroup() as group:
                try:
                    async for (
                        status,
                        block_num,
                    ) in control_point.start_oad_process():
                        if status == OADReturn.SUCCESS:
                            data = firmware_bytes[
                                block_num
                                * (block_size - 4) : (block_num + 1)
                                * (block_size - 4)
                            ]

                            task = group.create_task(image_block.write(block_num, data))

                            if block_num not in sent_blocks:
                                task.add_done_callback(lambda _: pbar.update(len(data)))
                                sent_blocks.add(block_num)

                        elif status == OADReturn.DL_COMPLETE:
                            break
                        elif status == OADReturn.CRC_ERR:
                            raise RuntimeError("Failed CRC check")
                        else:
                            raise RuntimeError(
                                f"Block {block_num} with unhandled status: {status.name}"
                            )
                except BaseException:
                    await control_point.cancel_oad()
                    raise

        # This causes hub to reset and disconnect
        await control_point.enable_oad_image()
        print("Done.")

        # avoid race condition of requesting disconnect while hub is initiating
        # disconnect itself - this can leave BlueZ in a a bad state
        await disconnect_event.wait()


async def dump_oad_info():
    """
    Connects to an OAD hub and prints some information about it.
    """
    device = await BleakScanner.find_device_by_filter(_match_oad_hubs)

    if device is None:
        print("No OAD device found")
        return

    # long timeout in case pairing is needed
    async with asyncio.timeout(30), BleakClient(device) as client, OADControlPoint(
        client
    ) as control_point:
        sw_ver = await control_point.get_software_version()
        print(
            f"Software version: app={sw_ver.app.major}.{sw_ver.app.minor}, stack={sw_ver.stack.major}.{sw_ver.stack.minor}"
        )

        profile_ver = await control_point.get_profile_version()
        print(f"Profile version: {profile_ver}")

        dev_type = await control_point.get_device_type()
        print(
            f"Device type: {dev_type:08X} ({_KNOWN_DEVICE_TYPES.get(dev_type, 'Unknown')})"
        )

        block_size = await control_point.get_oad_block_size()
        print(f"Block size: {block_size}")

        image_status = await control_point.get_oad_image_status()
        print(f"Image status: {image_status.name}")
