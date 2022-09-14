from pybricksdev.firmware import _firmware_metadata_is_v1, _firmware_metadata_is_v2


def test_firmware_v1():
    assert _firmware_metadata_is_v1({"metadata-version": "1.0.0"})
    assert _firmware_metadata_is_v1({"metadata-version": "1.1.0"})
    assert not _firmware_metadata_is_v1({"metadata-version": "2.0.0"})
    assert not _firmware_metadata_is_v1({"metadata-version": "2.1.0"})
    assert not _firmware_metadata_is_v1({"metadata-version": "3.0.0"})
    assert not _firmware_metadata_is_v1({"metadata-version": "3.1.0"})


def test_firmware_v2():
    assert not _firmware_metadata_is_v2({"metadata-version": "1.0.0"})
    assert not _firmware_metadata_is_v2({"metadata-version": "1.1.0"})
    assert _firmware_metadata_is_v2({"metadata-version": "2.0.0"})
    assert _firmware_metadata_is_v2({"metadata-version": "2.1.0"})
    assert not _firmware_metadata_is_v2({"metadata-version": "3.0.0"})
    assert not _firmware_metadata_is_v2({"metadata-version": "3.1.0"})
