from pybricksdev.ble.nus import NUS_RX_UUID, NUS_SERVICE_UUID, NUS_TX_UUID


def test_service_uuid():
    assert NUS_SERVICE_UUID == "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


def test_rx_char_uuid():
    assert NUS_RX_UUID == "6e400002-b5a3-f393-e0a9-e50e24dcca9e"


def test_tx_char_uuid():
    assert NUS_TX_UUID == "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
