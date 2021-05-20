from pybricksdev.ble.lwp3 import (
    LWP3_BOOTLOADER_CHARACTERISTIC_UUID,
    LWP3_BOOTLOADER_SERVICE_UUID,
    LWP3_HUB_CHARACTERISTIC_UUID,
    LWP3_HUB_SERVICE_UUID,
)


def test_lwp3_hub_service_uuid():
    assert LWP3_HUB_SERVICE_UUID == "00001623-1212-efde-1623-785feabcd123"


def test_lwp3_hub_characteristic_uuid():
    assert LWP3_HUB_CHARACTERISTIC_UUID == "00001624-1212-efde-1623-785feabcd123"


def test_lwp3_bootloader_service_uuid():
    assert LWP3_BOOTLOADER_SERVICE_UUID == "00001625-1212-efde-1623-785feabcd123"


def test_lwp3_bootloader_characteristic_uuid():
    assert LWP3_BOOTLOADER_CHARACTERISTIC_UUID == "00001626-1212-efde-1623-785feabcd123"
