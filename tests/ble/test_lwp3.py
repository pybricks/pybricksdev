from pybricksdev.ble.lwp3 import (
    LWP3_BOOTLOADER_CHARACTERISTIC_UUID,
    LWP3_BOOTLOADER_SERVICE_UUID,
    LWP3_HUB_CHARACTERISTIC_UUID,
    LWP3_HUB_SERVICE_UUID,
    AdvertisementData,
)
from pybricksdev.ble.lwp3.bytecodes import Capabilities, HubKind, LastNetwork, Status


def test_lwp3_hub_service_uuid():
    assert LWP3_HUB_SERVICE_UUID == "00001623-1212-efde-1623-785feabcd123"


def test_lwp3_hub_characteristic_uuid():
    assert LWP3_HUB_CHARACTERISTIC_UUID == "00001624-1212-efde-1623-785feabcd123"


def test_lwp3_bootloader_service_uuid():
    assert LWP3_BOOTLOADER_SERVICE_UUID == "00001625-1212-efde-1623-785feabcd123"


def test_lwp3_bootloader_characteristic_uuid():
    assert LWP3_BOOTLOADER_CHARACTERISTIC_UUID == "00001626-1212-efde-1623-785feabcd123"


def test_advertisement_data():
    adv = AdvertisementData(b"\x01\x40\x02\x05\x03\x00")
    assert adv.is_button_pressed
    assert adv.hub_kind == HubKind.BOOST
    assert adv.hub_capabilities == Capabilities.PERIPHERAL
    assert adv.last_network == LastNetwork(5)
    assert adv.status == Status.PERIPHERAL | Status.CENTRAL
