# SPDX-License-Identifier: MIT
# Copyright (c) 2024 The Pybricks Authors

import asyncio

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ..ble.lwp3 import LEGO_CID, LWP3_HUB_SERVICE_UUID, HubKind
from ..ble.oad.control_point import OADControlPoint

__all__ = ["dump_oad_info"]

# hubs known to use TI OAD
_OAD_HUBS = [HubKind.MARIO, HubKind.LUIGI, HubKind.PEACH, HubKind.TECHNIC_MOVE]


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


async def dump_oad_info():
    """
    Connects to an OAD hub and prints some information about it.
    """
    device = await BleakScanner.find_device_by_filter(_match_oad_hubs)

    if device is None:
        print("No OAD device found")
        return

    async with BleakClient(device) as client, OADControlPoint(client) as control_point:
        # long timeout in case pairing is needed
        async with asyncio.timeout(30):
            sw_ver = await control_point.get_software_version()
            print(f"Software version: {sw_ver}")

            profile_ver = await control_point.get_profile_version()
            print(f"Profile version: {profile_ver}")

            dev_type = await control_point.get_device_type()
            print(f"Device type: {dev_type:08X}")

            block_size = await control_point.get_oad_block_size()
            print(f"Block size: {block_size}")

            image_status = await control_point.get_oad_image_status()
            print(f"Image status: {image_status.name}")
