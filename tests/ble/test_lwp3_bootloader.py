from pybricksdev.ble.lwp3.bootloader import BootloaderAdvertisementData
from pybricksdev.ble.lwp3.bytecodes import Capabilities, HubKind


def test_bootloader_advertisement_data():
    adv = BootloaderAdvertisementData(b"\x78\x56\x34\x12\x40\x02")
    assert adv.version == 0x12345678
    assert adv.hub_kind == HubKind.BOOST
    assert adv.hub_capabilities == Capabilities.PERIPHERAL
