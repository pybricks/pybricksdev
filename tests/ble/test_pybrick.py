from pybricksdev.ble.pybricks import (
    DI_SERVICE_UUID,
    FW_REV_UUID,
    PYBRICKS_COMMAND_EVENT_UUID,
    PYBRICKS_SERVICE_UUID,
    SW_REV_UUID,
)


def test_pybricks_service_uuid():
    assert PYBRICKS_SERVICE_UUID == "c5f50001-8280-46da-89f4-6d8051e4aeef"


def test_pybricks_control_characteristic_uuid():
    assert PYBRICKS_COMMAND_EVENT_UUID == "c5f50002-8280-46da-89f4-6d8051e4aeef"


def test_device_information_service_uuid():
    assert DI_SERVICE_UUID == "0000180a-0000-1000-8000-00805f9b34fb"


def test_device_information_service_firmware_revision_characteristic_uuid():
    assert FW_REV_UUID == "00002a26-0000-1000-8000-00805f9b34fb"


def test_device_information_service_software_revision_characteristic_uuid():
    assert SW_REV_UUID == "00002a28-0000-1000-8000-00805f9b34fb"
