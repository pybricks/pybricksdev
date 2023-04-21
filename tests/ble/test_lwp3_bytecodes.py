import pytest

from pybricksdev.ble.lwp3.bytecodes import (
    BluetoothAddress,
    HwNetExtFamily,
    HwNetFamily,
    HwNetSubfamily,
    LastNetwork,
    LWPVersion,
    PortID,
    Version,
)


def test_last_network():
    # not a pre-defined value
    assert LastNetwork(1) == 1


class TestVersion:
    def test_components(self):
        version = Version(0x12345678)
        assert version.major == 1
        assert version.minor == 2
        assert version.bug == 34
        assert version.build == 5678

    def test_parse(self):
        version = Version.parse("1.2.34.5678")
        assert version.major == 1
        assert version.minor == 2
        assert version.bug == 34
        assert version.build == 5678

    def test_str(self):
        assert str(Version(0x00000000)) == "0.0.00.0000"
        assert str(Version(0x10000000)) == "1.0.00.0000"
        assert str(Version(0x12345678)) == "1.2.34.5678"

    def test_repr(self):
        assert repr(Version(0x00000000)) == "Version(0x00000000)"
        assert repr(Version(0x10000000)) == "Version(0x10000000)"
        assert repr(Version(0x12345678)) == "Version(0x12345678)"


class TestLWPVersion:
    def test_components(self):
        version = LWPVersion(0x1234)
        assert version.major == 12
        assert version.minor == 34

    def test_parse(self):
        version = LWPVersion.parse("12.34")
        assert version.major == 12
        assert version.minor == 34

    def test_str(self):
        assert str(LWPVersion(0x0000)) == "00.00"
        assert str(LWPVersion(0x0100)) == "01.00"
        assert str(LWPVersion(0x1234)) == "12.34"

    def test_repr(self):
        assert repr(LWPVersion(0x0000)) == "LWPVersion(0x0000)"
        assert repr(LWPVersion(0x0100)) == "LWPVersion(0x0100)"
        assert repr(LWPVersion(0x1234)) == "LWPVersion(0x1234)"


class TestBluetoothAddress:
    def test_constructor_with_str(self):
        assert BluetoothAddress("12:34:56:78:9A:BC") == BluetoothAddress(
            b"\x12\x34\x56\x78\x9a\xbc"
        )

    def test_str(self):
        assert str(BluetoothAddress(b"\x12\x34\x56\x78\x9a\xbc")) == "12:34:56:78:9A:BC"

    def test_repr(self):
        assert (
            repr(BluetoothAddress(b"\x12\x34\x56\x78\x9a\xbc"))
            == "BluetoothAddress('12:34:56:78:9A:BC')"
        )


def test_port_id():
    assert not PortID(0).internal
    assert PortID(50).internal


class TestHwNetExtFamily:
    def test_from_parts(self):
        ext_fam = HwNetExtFamily.from_parts(HwNetFamily.RED, HwNetSubfamily.FLASH_2)
        assert ext_fam.family == HwNetFamily.RED
        assert ext_fam.subfamily == HwNetSubfamily.FLASH_2

    def test_valid_value(self):
        ext_fam = HwNetExtFamily(0x12)
        assert ext_fam.family == HwNetFamily.YELLOW
        assert ext_fam.subfamily == HwNetSubfamily.FLASH_1

    def test_bad_value(self):
        with pytest.raises(ValueError):
            HwNetExtFamily(0x80)
