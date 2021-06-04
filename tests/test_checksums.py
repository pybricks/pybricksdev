from pybricksdev.tools.checksum import xor_bytes


def test_xor_bytes():
    assert xor_bytes(b"\x00") == 0xFF ^ 0x00
    assert xor_bytes(b"\x00", 0x00) == 0x00 ^ 0x00
    assert xor_bytes(b"\xFF") == 0xFF ^ 0xFF
    assert xor_bytes(b"\xFF", 0x00) == 0x00 ^ 0xFF
    assert xor_bytes(b"\x01\x02\x03\x04") == 0xFF ^ 0x01 ^ 0x02 ^ 0x03 ^ 0x04
