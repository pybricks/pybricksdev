import pytest

from pybricksdev.ble.lwp3.bytecodes import (
    AlertKind,
    AlertOperation,
    AlertStatus,
    BatteryKind,
    BluetoothAddress,
    ErrorCode,
    HubAction,
    HubProperty,
    HubPropertyOperation,
    HwNetCmd,
    HwNetFamily,
    HwNetSubfamily,
    IODeviceKind,
    IOEvent,
    MessageKind,
    PortID,
    Version,
)
from pybricksdev.ble.lwp3.messages import (
    ErrorMessage,
    FirmwareUpdateMessage,
    HubActionMessage,
    HubAlertDisableUpdatesMessage,
    HubAlertEnableUpdatesMessage,
    HubAlertRequestUpdateMessage,
    HubAlertUpdateMessage,
    HubIOAttachedMessage,
    HubIOAttachedVirtualMessage,
    HubIODetachedMessage,
    HubPropertyDisableUpdates,
    HubPropertyEnableUpdates,
    HubPropertyRequestUpdate,
    HubPropertyReset,
    HubPropertySet,
    HubPropertyUpdate,
    HwNetCmdExtendedFamilyMessage,
    HwNetCmdFamilyMessage,
    HwNetCmdGetExtendedFamilyMessage,
    HwNetCmdGetFamilyMessage,
    HwNetCmdGetSubfamilyMessage,
    HwNetCmdJoinDeniedMessage,
    HwNetCmdRequestConnectionMessage,
    HwNetCmdRequestFamilyMessage,
    HwNetCmdResetLongPressMessage,
    HwNetCmdSetExtendedFamilyMessage,
    HwNetCmdSetFamilyMessage,
    HwNetCmdSetSubfamilyMessage,
    HwNetCmdSubfamilyMessage,
    parse_message,
)


class TestHubPropertyMsg:
    class TestHubPropertySet:
        def test_constructor(self):
            msg = HubPropertySet(HubProperty.NAME, "Test")
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.SET
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertySet(<HubProperty.NAME: 1>, 'Test')"

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x01\x01\x01Test")
            assert isinstance(msg, HubPropertySet)
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.SET
            assert msg.value == "Test"

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertySet(
                    HubProperty.BDADDR, BluetoothAddress("00:00:00:00:00:00")
                )

        def test_property_value_too_long(self):
            with pytest.raises(ValueError):
                HubPropertySet(HubProperty.NAME, "This name is too long")

    class TestHubPropertyEnableUpdates:
        def test_constructor(self):
            msg = HubPropertyEnableUpdates(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.ENABLE_UPDATES
            assert repr(msg) == "HubPropertyEnableUpdates(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x02")
            assert isinstance(msg, HubPropertyEnableUpdates)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.ENABLE_UPDATES

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyEnableUpdates(HubProperty.BDADDR)

    class TestHubPropertyDisableUpdates:
        def test_constructor(self):
            msg = HubPropertyDisableUpdates(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.DISABLE_UPDATES
            assert repr(msg) == "HubPropertyDisableUpdates(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x03")
            assert isinstance(msg, HubPropertyDisableUpdates)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.DISABLE_UPDATES

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyDisableUpdates(HubProperty.BDADDR)

    class TestHubPropertyReset:
        def test_constructor(self):
            msg = HubPropertyReset(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.RESET
            assert repr(msg) == "HubPropertyReset(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x04")
            assert isinstance(msg, HubPropertyReset)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.RESET

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyReset(HubProperty.BDADDR)

    class TestHubPropertyRequestUpdate:
        def test_constructor(self):
            msg = HubPropertyRequestUpdate(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.REQUEST_UPDATE
            assert repr(msg) == "HubPropertyRequestUpdate(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x05")
            assert isinstance(msg, HubPropertyRequestUpdate)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.REQUEST_UPDATE

    class TestHubPropertyUpdate:
        def test_constructor_with_string_arg(self):
            msg = HubPropertyUpdate(HubProperty.NAME, "Test")
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.NAME: 1>, 'Test')"

        def test_constructor_with_bool_arg(self):
            msg = HubPropertyUpdate(HubProperty.BUTTON, True)
            assert msg.length == 6
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.BUTTON
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value is True
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.BUTTON: 2>, True)"

        def test_constructor_with_version_arg(self):
            msg = HubPropertyUpdate(HubProperty.FW_VERSION, Version(0x10000000))
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.FW_VERSION
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == Version(0x10000000)
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.FW_VERSION: 3>, Version(0x10000000))"
            )

        def test_constructor_with_signed_int_arg(self):
            msg = HubPropertyUpdate(HubProperty.RSSI, -50)
            assert msg.length == 6
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.RSSI
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == -50
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.RSSI: 5>, -50)"

        def test_constructor_with_int_enum_arg(self):
            msg = HubPropertyUpdate(HubProperty.BATTERY_KIND, BatteryKind.NORMAL)
            assert msg.length == 6
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.BATTERY_KIND
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == BatteryKind.NORMAL
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.BATTERY_KIND: 7>, <BatteryKind.NORMAL: 0>)"
            )

        def test_constructor_with_bluetooth_address_arg(self):
            msg = HubPropertyUpdate(
                HubProperty.BDADDR, BluetoothAddress("00:00:00:00:00:00")
            )
            assert msg.length == 11
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.BDADDR
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == BluetoothAddress("00:00:00:00:00:00")
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.BDADDR: 13>, BluetoothAddress('00:00:00:00:00:00'))"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x01\x01\x06Test")
            assert isinstance(msg, HubPropertyUpdate)
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_PROPERTY
            assert msg.prop == HubProperty.NAME
            assert msg.op == HubPropertyOperation.UPDATE
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.NAME: 1>, 'Test')"


class TestHubActionMsg:
    def test_constructor(self):
        msg = HubActionMessage(HubAction.POWER_OFF)
        assert msg.length == 4
        assert msg.kind == MessageKind.HUB_ACTION
        assert msg.action == HubAction.POWER_OFF
        assert repr(msg) == "HubActionMessage(<HubAction.POWER_OFF: 1>)"

    def test_parse_message(self):
        msg = parse_message(b"\x04\x00\x02\x01")
        assert isinstance(msg, HubActionMessage)
        assert msg.length == 4
        assert msg.kind == MessageKind.HUB_ACTION
        assert msg.action == HubAction.POWER_OFF


class TestHubAlertMessage:
    class TestHubAlertEnableUpdatesMessage:
        def test_constructor(self):
            msg = HubAlertEnableUpdatesMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.ENABLE_UPDATES
            assert (
                repr(msg) == "HubAlertEnableUpdatesMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x01")
            assert isinstance(msg, HubAlertEnableUpdatesMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.ENABLE_UPDATES

    class TestHubAlertDisableUpdatesMessage:
        def test_constructor(self):
            msg = HubAlertDisableUpdatesMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.DISABLE_UPDATES
            assert (
                repr(msg) == "HubAlertDisableUpdatesMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x02")
            assert isinstance(msg, HubAlertDisableUpdatesMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.DISABLE_UPDATES

    class TestHubAlertRequestUpdateMessage:
        def test_constructor(self):
            msg = HubAlertRequestUpdateMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.REQUEST_UPDATE
            assert (
                repr(msg) == "HubAlertRequestUpdateMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x03")
            assert isinstance(msg, HubAlertRequestUpdateMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.REQUEST_UPDATE

    class TestHubAlertUpdateMessage:
        def test_constructor(self):
            msg = HubAlertUpdateMessage(AlertKind.LOW_VOLTAGE, AlertStatus.ALERT)
            assert msg.length == 6
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.UPDATE
            assert msg.status == AlertStatus.ALERT
            assert (
                repr(msg)
                == "HubAlertUpdateMessage(<AlertKind.LOW_VOLTAGE: 1>, <AlertStatus.ALERT: 255>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x06\x00\x03\x01\x04\xff")
            assert isinstance(msg, HubAlertUpdateMessage)
            assert msg.length == 6
            assert msg.kind == MessageKind.HUB_ALERT
            assert msg.alert == AlertKind.LOW_VOLTAGE
            assert msg.op == AlertOperation.UPDATE
            assert msg.status == AlertStatus.ALERT


class TestHubAttachedIOMessages:
    class TestHubIODetachedMessage:
        def test_constructor(self):
            msg = HubIODetachedMessage(PortID(9))
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.DETACHED
            assert repr(msg) == "HubIODetachedMessage(<PortID.9: 9>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x04\x09\x00")
            assert isinstance(msg, HubIODetachedMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.DETACHED

    class TestHubIOAttachedMessage:
        def test_constructor(self):
            msg = HubIOAttachedMessage(
                PortID(9),
                IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR,
                Version(0x10000000),
                Version(0x20000000),
            )
            assert msg.length == 15
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.ATTACHED
            assert msg.device == IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.hw_ver == Version(0x10000000)
            assert msg.fw_ver == Version(0x20000000)
            assert (
                repr(msg)
                == "HubIOAttachedMessage(<PortID.9: 9>, <IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR: 76>, Version(0x10000000), Version(0x20000000))"
            )

        def test_parse_message(self):
            msg = parse_message(
                b"\x0f\x00\x04\x09\x01\x4c\x00\x00\x00\x00\x10\x00\x00\x00\x20"
            )
            assert isinstance(msg, HubIOAttachedMessage)
            assert msg.length == 15
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.ATTACHED
            assert msg.device == IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.hw_ver == Version(0x10000000)
            assert msg.fw_ver == Version(0x20000000)

    class TestHubIOAttachedVirtualMessage:
        def test_constructor(self):
            msg = HubIOAttachedVirtualMessage(
                PortID(9),
                IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR,
                PortID(10),
                PortID(11),
            )
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.ATTACHED_VIRTUAL
            assert msg.device == IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.port_a == PortID(10)
            assert msg.port_b == PortID(11)
            assert (
                repr(msg)
                == "HubIOAttachedVirtualMessage(<PortID.9: 9>, <IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR: 76>, <PortID.10: 10>, <PortID.11: 11>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x04\x09\x02\x4c\x00\x0a\x0b")
            assert isinstance(msg, HubIOAttachedVirtualMessage)
            assert msg.length == 9
            assert msg.kind == MessageKind.HUB_ATTACHED_IO
            assert msg.port == PortID(9)
            assert msg.event == IOEvent.ATTACHED_VIRTUAL
            assert msg.device == IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.port_a == PortID(10)
            assert msg.port_b == PortID(11)


class TestErrorMsg:
    def test_constructor(self):
        msg = ErrorMessage(MessageKind.HUB_PROPERTY, ErrorCode.INVALID)
        assert msg.length == 5
        assert msg.kind == MessageKind.ERROR
        assert msg.command == MessageKind.HUB_PROPERTY
        assert msg.code == ErrorCode.INVALID
        assert (
            repr(msg)
            == "ErrorMessage(<MessageKind.HUB_PROPERTY: 1>, <ErrorCode.INVALID: 6>)"
        )

    def test_parse_message(self):
        msg = parse_message(b"\x05\x00\x05\x01\x06")
        assert isinstance(msg, ErrorMessage)
        assert msg.length == 5
        assert msg.kind == MessageKind.ERROR
        assert msg.command == MessageKind.HUB_PROPERTY
        assert msg.code == ErrorCode.INVALID


class TestHwNetCmdMsg:
    class TestHwNetCmdRequestConnectionMessage:
        def test_constructor(self):
            msg = HwNetCmdRequestConnectionMessage(True)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.CONNECTION_REQUEST
            assert msg.button_pressed is True
            assert repr(msg) == "HwNetCmdRequestConnectionMessage(True)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x02\x01")
            assert isinstance(msg, HwNetCmdRequestConnectionMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.CONNECTION_REQUEST
            assert msg.button_pressed is True

    class TestHwNetCmdRequestFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdRequestFamilyMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY_REQUEST
            assert repr(msg) == "HwNetCmdRequestFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x03")
            assert isinstance(msg, HwNetCmdRequestFamilyMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY_REQUEST

    class TestHwNetCmdSetFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetFamilyMessage(HwNetFamily.GREEN)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY_SET
            assert msg.family == HwNetFamily.GREEN
            assert repr(msg) == "HwNetCmdSetFamilyMessage(<HwNetFamily.GREEN: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x04\x01")
            assert isinstance(msg, HwNetCmdSetFamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY_SET
            assert msg.family == HwNetFamily.GREEN

    class TestHwNetCmdJoinDeniedMessage:
        def test_constructor(self):
            msg = HwNetCmdJoinDeniedMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.JOIN_DENIED
            assert repr(msg) == "HwNetCmdJoinDeniedMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x05")
            assert isinstance(msg, HwNetCmdJoinDeniedMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.JOIN_DENIED

    class TestHwNetCmdGetFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetFamilyMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_FAMILY
            assert repr(msg) == "HwNetCmdGetFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x06")
            assert isinstance(msg, HwNetCmdGetFamilyMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_FAMILY

    class TestHwNetCmdFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdFamilyMessage(HwNetFamily.GREEN)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY
            assert msg.family == HwNetFamily.GREEN
            assert repr(msg) == "HwNetCmdFamilyMessage(<HwNetFamily.GREEN: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x07\x01")
            assert isinstance(msg, HwNetCmdFamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.FAMILY
            assert msg.family == HwNetFamily.GREEN

    class TestHwNetCmdGetSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetSubfamilyMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_SUBFAMILY
            assert repr(msg) == "HwNetCmdGetSubfamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x08")
            assert isinstance(msg, HwNetCmdGetSubfamilyMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_SUBFAMILY

    class TestHwNetCmdSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSubfamilyMessage(HwNetSubfamily.FLASH_2)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.SUBFAMILY
            assert msg.subfamily == HwNetSubfamily.FLASH_2
            assert repr(msg) == "HwNetCmdSubfamilyMessage(<HwNetSubfamily.FLASH_2: 2>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x09\x02")
            assert isinstance(msg, HwNetCmdSubfamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.SUBFAMILY
            assert msg.subfamily == HwNetSubfamily.FLASH_2

    class TestHwNetCmdSetSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetSubfamilyMessage(HwNetSubfamily.FLASH_2)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.SUBFAMILY_SET
            assert msg.subfamily == HwNetSubfamily.FLASH_2
            assert (
                repr(msg) == "HwNetCmdSetSubfamilyMessage(<HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0a\x02")
            assert isinstance(msg, HwNetCmdSetSubfamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.SUBFAMILY_SET
            assert msg.subfamily == HwNetSubfamily.FLASH_2

    class TestHwNetCmdGetExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetExtendedFamilyMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_EXTENDED_FAMILY
            assert repr(msg) == "HwNetCmdGetExtendedFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x0b")
            assert isinstance(msg, HwNetCmdGetExtendedFamilyMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.GET_EXTENDED_FAMILY

    class TestHwNetCmdExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdExtendedFamilyMessage(
                HwNetFamily.GREEN, HwNetSubfamily.FLASH_2
            )
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.EXTENDED_FAMILY
            assert msg.ext_family.family == HwNetFamily.GREEN
            assert msg.ext_family.subfamily == HwNetSubfamily.FLASH_2
            assert (
                repr(msg)
                == "HwNetCmdExtendedFamilyMessage(<HwNetFamily.GREEN: 1>, <HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0c\x21")
            assert isinstance(msg, HwNetCmdExtendedFamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.EXTENDED_FAMILY
            assert msg.ext_family.family == HwNetFamily.GREEN
            assert msg.ext_family.subfamily == HwNetSubfamily.FLASH_2

    class TestHwNetCmdSetExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetExtendedFamilyMessage(
                HwNetFamily.GREEN, HwNetSubfamily.FLASH_2
            )
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.EXTENDED_FAMILY_SET
            assert msg.ext_family.family == HwNetFamily.GREEN
            assert msg.ext_family.subfamily == HwNetSubfamily.FLASH_2
            assert (
                repr(msg)
                == "HwNetCmdSetExtendedFamilyMessage(<HwNetFamily.GREEN: 1>, <HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0d\x21")
            assert isinstance(msg, HwNetCmdSetExtendedFamilyMessage)
            assert msg.length == 5
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.EXTENDED_FAMILY_SET
            assert msg.ext_family.family == HwNetFamily.GREEN
            assert msg.ext_family.subfamily == HwNetSubfamily.FLASH_2

    class TestHwNetCmdResetLongPressMessage:
        def test_constructor(self):
            msg = HwNetCmdResetLongPressMessage()
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.RESET_LONG_PRESS
            assert repr(msg) == "HwNetCmdResetLongPressMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x0e")
            assert isinstance(msg, HwNetCmdResetLongPressMessage)
            assert msg.length == 4
            assert msg.kind == MessageKind.HW_NET_CMD
            assert msg.cmd == HwNetCmd.RESET_LONG_PRESS


class TestFirmwareMessages:
    class TestFirmwareUpdateMessage:
        def test_constructor(self):
            msg = FirmwareUpdateMessage()
            assert msg.length == 12
            assert msg.kind == MessageKind.FW_UPDATE
            assert msg.key == b"LPF2-Boot"
            assert repr(msg) == "FirmwareUpdateMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x0c\x00\x10LPF2-Boot")
            assert isinstance(msg, FirmwareUpdateMessage)
            assert msg.length == 12
            assert msg.kind == MessageKind.FW_UPDATE
            assert msg.key == b"LPF2-Boot"
