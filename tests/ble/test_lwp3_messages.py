import inspect

import pytest

from pybricksdev.ble.lwp3.bytecodes import (
    AlertKind,
    AlertOperation,
    AlertStatus,
    BatteryKind,
    BluetoothAddress,
    DataFormat,
    EndInfo,
    ErrorCode,
    Feedback,
    HubAction,
    HubProperty,
    HubPropertyOperation,
    HwNetCmd,
    HwNetFamily,
    HwNetSubfamily,
    InfoKind,
    IODeviceCapabilities,
    IODeviceKind,
    IODeviceMapping,
    IOEvent,
    MessageKind,
    ModeCapabilities,
    ModeInfoKind,
    PortID,
    PortInfoFormatSetupCommand,
    PortOutputCommand,
    StartInfo,
    Version,
    VirtualPortSetupCommand,
)
from pybricksdev.ble.lwp3.messages import (
    AbstractHubAlertMessage,
    AbstractHubAttachedIOMessage,
    AbstractHubPropertyMessage,
    AbstractHwNetCmdMessage,
    AbstractMessage,
    AbstractPortInfoMessage,
    AbstractPortModeInfoMessage,
    AbstractPortOutputCommandMessage,
    AbstractVirtualPortSetupMessage,
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
    PortFormatSetupComboLockMessage,
    PortFormatSetupComboMessage,
    PortFormatSetupComboResetMessage,
    PortFormatSetupComboUnlockDisabledMessage,
    PortFormatSetupComboUnlockEnabledMessage,
    PortInfoCombosMessage,
    PortInfoModeInfoMessage,
    PortInfoRequestMessage,
    PortInputFormatComboMessage,
    PortInputFormatMessage,
    PortInputFormatSetupMessage,
    PortModeInfoCapabilitiesMessage,
    PortModeInfoFormatMessage,
    PortModeInfoMappingMessage,
    PortModeInfoMotorBiasMessage,
    PortModeInfoNameMessage,
    PortModeInfoPercentMessage,
    PortModeInfoRawMessage,
    PortModeInfoRequestMessage,
    PortModeInfoSIMessage,
    PortModeInfoSymbolMessage,
    PortOutputCommandFeedbackMessage,
    PortOutputCommandWriteDirectMessage,
    PortOutputCommandWriteDirectModeDataMessage,
    PortValueComboMessage,
    PortValueMessage,
    VirtualPortSetupConnectMessage,
    VirtualPortSetupDisconnectMessage,
    parse_message,
)


def test_is_abstract():
    assert inspect.isabstract(AbstractMessage)


class TestHubPropertyMsg:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractHubPropertyMessage)

    class TestHubPropertySet:
        def test_constructor(self):
            msg = HubPropertySet(HubProperty.NAME, "Test")
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.SET
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertySet(<HubProperty.NAME: 1>, 'Test')"

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x01\x01\x01Test")
            assert isinstance(msg, HubPropertySet)
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.SET
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
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.ENABLE_UPDATES
            assert repr(msg) == "HubPropertyEnableUpdates(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x02")
            assert isinstance(msg, HubPropertyEnableUpdates)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.ENABLE_UPDATES

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyEnableUpdates(HubProperty.BDADDR)

    class TestHubPropertyDisableUpdates:
        def test_constructor(self):
            msg = HubPropertyDisableUpdates(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.DISABLE_UPDATES
            assert repr(msg) == "HubPropertyDisableUpdates(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x03")
            assert isinstance(msg, HubPropertyDisableUpdates)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.DISABLE_UPDATES

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyDisableUpdates(HubProperty.BDADDR)

    class TestHubPropertyReset:
        def test_constructor(self):
            msg = HubPropertyReset(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.RESET
            assert repr(msg) == "HubPropertyReset(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x04")
            assert isinstance(msg, HubPropertyReset)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.RESET

        def test_invalid_property(self):
            with pytest.raises(ValueError):
                HubPropertyReset(HubProperty.BDADDR)

    class TestHubPropertyRequestUpdate:
        def test_constructor(self):
            msg = HubPropertyRequestUpdate(HubProperty.NAME)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.REQUEST_UPDATE
            assert repr(msg) == "HubPropertyRequestUpdate(<HubProperty.NAME: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x01\x01\x05")
            assert isinstance(msg, HubPropertyRequestUpdate)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.REQUEST_UPDATE

    class TestHubPropertyUpdate:
        def test_constructor_with_string_arg(self):
            msg = HubPropertyUpdate(HubProperty.NAME, "Test")
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.NAME: 1>, 'Test')"

        def test_constructor_with_bool_arg(self):
            msg = HubPropertyUpdate(HubProperty.BUTTON, True)
            assert msg.length == 6
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.BUTTON
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value is True
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.BUTTON: 2>, True)"

        def test_constructor_with_version_arg(self):
            msg = HubPropertyUpdate(HubProperty.FW_VERSION, Version(0x10000000))
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.FW_VERSION
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value == Version(0x10000000)
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.FW_VERSION: 3>, Version(0x10000000))"
            )

        def test_constructor_with_signed_int_arg(self):
            msg = HubPropertyUpdate(HubProperty.RSSI, -50)
            assert msg.length == 6
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.RSSI
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value == -50
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.RSSI: 5>, -50)"

        def test_constructor_with_int_enum_arg(self):
            msg = HubPropertyUpdate(HubProperty.BATTERY_KIND, BatteryKind.NORMAL)
            assert msg.length == 6
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.BATTERY_KIND
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value is BatteryKind.NORMAL
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.BATTERY_KIND: 7>, <BatteryKind.NORMAL: 0>)"
            )

        def test_constructor_with_bluetooth_address_arg(self):
            msg = HubPropertyUpdate(
                HubProperty.BDADDR, BluetoothAddress("00:00:00:00:00:00")
            )
            assert msg.length == 11
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.BDADDR
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value == BluetoothAddress("00:00:00:00:00:00")
            assert (
                repr(msg)
                == "HubPropertyUpdate(<HubProperty.BDADDR: 13>, BluetoothAddress('00:00:00:00:00:00'))"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x01\x01\x06Test")
            assert isinstance(msg, HubPropertyUpdate)
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_PROPERTY
            assert msg.prop is HubProperty.NAME
            assert msg.op is HubPropertyOperation.UPDATE
            assert msg.value == "Test"
            assert repr(msg) == "HubPropertyUpdate(<HubProperty.NAME: 1>, 'Test')"


class TestHubActionMsg:
    def test_constructor(self):
        msg = HubActionMessage(HubAction.POWER_OFF)
        assert msg.length == 4
        assert msg.kind is MessageKind.HUB_ACTION
        assert msg.action is HubAction.POWER_OFF
        assert repr(msg) == "HubActionMessage(<HubAction.POWER_OFF: 1>)"

    def test_parse_message(self):
        msg = parse_message(b"\x04\x00\x02\x01")
        assert isinstance(msg, HubActionMessage)
        assert msg.length == 4
        assert msg.kind is MessageKind.HUB_ACTION
        assert msg.action is HubAction.POWER_OFF


class TestHubAlertMessage:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractHubAlertMessage)

    class TestHubAlertEnableUpdatesMessage:
        def test_constructor(self):
            msg = HubAlertEnableUpdatesMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.ENABLE_UPDATES
            assert (
                repr(msg) == "HubAlertEnableUpdatesMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x01")
            assert isinstance(msg, HubAlertEnableUpdatesMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.ENABLE_UPDATES

    class TestHubAlertDisableUpdatesMessage:
        def test_constructor(self):
            msg = HubAlertDisableUpdatesMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.DISABLE_UPDATES
            assert (
                repr(msg) == "HubAlertDisableUpdatesMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x02")
            assert isinstance(msg, HubAlertDisableUpdatesMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.DISABLE_UPDATES

    class TestHubAlertRequestUpdateMessage:
        def test_constructor(self):
            msg = HubAlertRequestUpdateMessage(AlertKind.LOW_VOLTAGE)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.REQUEST_UPDATE
            assert (
                repr(msg) == "HubAlertRequestUpdateMessage(<AlertKind.LOW_VOLTAGE: 1>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x03\x01\x03")
            assert isinstance(msg, HubAlertRequestUpdateMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.REQUEST_UPDATE

    class TestHubAlertUpdateMessage:
        def test_constructor(self):
            msg = HubAlertUpdateMessage(AlertKind.LOW_VOLTAGE, AlertStatus.ALERT)
            assert msg.length == 6
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.UPDATE
            assert msg.status == AlertStatus.ALERT
            assert (
                repr(msg)
                == "HubAlertUpdateMessage(<AlertKind.LOW_VOLTAGE: 1>, <AlertStatus.ALERT: 255>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x06\x00\x03\x01\x04\xff")
            assert isinstance(msg, HubAlertUpdateMessage)
            assert msg.length == 6
            assert msg.kind is MessageKind.HUB_ALERT
            assert msg.alert is AlertKind.LOW_VOLTAGE
            assert msg.op is AlertOperation.UPDATE
            assert msg.status == AlertStatus.ALERT


class TestHubAttachedIOMessages:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractHubAttachedIOMessage)

    class TestHubIODetachedMessage:
        def test_constructor(self):
            msg = HubIODetachedMessage(PortID(9))
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.DETACHED
            assert repr(msg) == "HubIODetachedMessage(<PortID.9: 9>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x04\x09\x00")
            assert isinstance(msg, HubIODetachedMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.DETACHED

    class TestHubIOAttachedMessage:
        def test_constructor(self):
            msg = HubIOAttachedMessage(
                PortID(9),
                IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR,
                Version(0x10000000),
                Version(0x20000000),
            )
            assert msg.length == 15
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.ATTACHED
            assert msg.device is IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
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
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.ATTACHED
            assert msg.device is IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
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
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.ATTACHED_VIRTUAL
            assert msg.device is IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.port_a is PortID(10)
            assert msg.port_b is PortID(11)
            assert (
                repr(msg)
                == "HubIOAttachedVirtualMessage(<PortID.9: 9>, <IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR: 76>, <PortID.10: 10>, <PortID.11: 11>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x04\x09\x02\x4c\x00\x0a\x0b")
            assert isinstance(msg, HubIOAttachedVirtualMessage)
            assert msg.length == 9
            assert msg.kind is MessageKind.HUB_ATTACHED_IO
            assert msg.port is PortID(9)
            assert msg.event is IOEvent.ATTACHED_VIRTUAL
            assert msg.device is IODeviceKind.TECHNIC_LARGE_ANGULAR_MOTOR
            assert msg.port_a is PortID(10)
            assert msg.port_b is PortID(11)


class TestErrorMsg:
    def test_constructor(self):
        msg = ErrorMessage(MessageKind.HUB_PROPERTY, ErrorCode.INVALID)
        assert msg.length == 5
        assert msg.kind is MessageKind.ERROR
        assert msg.command is MessageKind.HUB_PROPERTY
        assert msg.code is ErrorCode.INVALID
        assert (
            repr(msg)
            == "ErrorMessage(<MessageKind.HUB_PROPERTY: 1>, <ErrorCode.INVALID: 6>)"
        )

    def test_parse_message(self):
        msg = parse_message(b"\x05\x00\x05\x01\x06")
        assert isinstance(msg, ErrorMessage)
        assert msg.length == 5
        assert msg.kind is MessageKind.ERROR
        assert msg.command is MessageKind.HUB_PROPERTY
        assert msg.code is ErrorCode.INVALID


class TestHwNetCmdMsg:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractHwNetCmdMessage)

    class TestHwNetCmdRequestConnectionMessage:
        def test_constructor(self):
            msg = HwNetCmdRequestConnectionMessage(True)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.CONNECTION_REQUEST
            assert msg.button_pressed is True
            assert repr(msg) == "HwNetCmdRequestConnectionMessage(True)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x02\x01")
            assert isinstance(msg, HwNetCmdRequestConnectionMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.CONNECTION_REQUEST
            assert msg.button_pressed is True

    class TestHwNetCmdRequestFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdRequestFamilyMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY_REQUEST
            assert repr(msg) == "HwNetCmdRequestFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x03")
            assert isinstance(msg, HwNetCmdRequestFamilyMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY_REQUEST

    class TestHwNetCmdSetFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetFamilyMessage(HwNetFamily.GREEN)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY_SET
            assert msg.family is HwNetFamily.GREEN
            assert repr(msg) == "HwNetCmdSetFamilyMessage(<HwNetFamily.GREEN: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x04\x01")
            assert isinstance(msg, HwNetCmdSetFamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY_SET
            assert msg.family is HwNetFamily.GREEN

    class TestHwNetCmdJoinDeniedMessage:
        def test_constructor(self):
            msg = HwNetCmdJoinDeniedMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.JOIN_DENIED
            assert repr(msg) == "HwNetCmdJoinDeniedMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x05")
            assert isinstance(msg, HwNetCmdJoinDeniedMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.JOIN_DENIED

    class TestHwNetCmdGetFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetFamilyMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_FAMILY
            assert repr(msg) == "HwNetCmdGetFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x06")
            assert isinstance(msg, HwNetCmdGetFamilyMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_FAMILY

    class TestHwNetCmdFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdFamilyMessage(HwNetFamily.GREEN)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY
            assert msg.family is HwNetFamily.GREEN
            assert repr(msg) == "HwNetCmdFamilyMessage(<HwNetFamily.GREEN: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x07\x01")
            assert isinstance(msg, HwNetCmdFamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.FAMILY
            assert msg.family is HwNetFamily.GREEN

    class TestHwNetCmdGetSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetSubfamilyMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_SUBFAMILY
            assert repr(msg) == "HwNetCmdGetSubfamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x08")
            assert isinstance(msg, HwNetCmdGetSubfamilyMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_SUBFAMILY

    class TestHwNetCmdSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSubfamilyMessage(HwNetSubfamily.FLASH_2)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.SUBFAMILY
            assert msg.subfamily is HwNetSubfamily.FLASH_2
            assert repr(msg) == "HwNetCmdSubfamilyMessage(<HwNetSubfamily.FLASH_2: 2>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x09\x02")
            assert isinstance(msg, HwNetCmdSubfamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.SUBFAMILY
            assert msg.subfamily is HwNetSubfamily.FLASH_2

    class TestHwNetCmdSetSubfamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetSubfamilyMessage(HwNetSubfamily.FLASH_2)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.SUBFAMILY_SET
            assert msg.subfamily is HwNetSubfamily.FLASH_2
            assert (
                repr(msg) == "HwNetCmdSetSubfamilyMessage(<HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0a\x02")
            assert isinstance(msg, HwNetCmdSetSubfamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.SUBFAMILY_SET
            assert msg.subfamily is HwNetSubfamily.FLASH_2

    class TestHwNetCmdGetExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdGetExtendedFamilyMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_EXTENDED_FAMILY
            assert repr(msg) == "HwNetCmdGetExtendedFamilyMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x0b")
            assert isinstance(msg, HwNetCmdGetExtendedFamilyMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.GET_EXTENDED_FAMILY

    class TestHwNetCmdExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdExtendedFamilyMessage(
                HwNetFamily.GREEN, HwNetSubfamily.FLASH_2
            )
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.EXTENDED_FAMILY
            assert msg.ext_family.family is HwNetFamily.GREEN
            assert msg.ext_family.subfamily is HwNetSubfamily.FLASH_2
            assert (
                repr(msg)
                == "HwNetCmdExtendedFamilyMessage(<HwNetFamily.GREEN: 1>, <HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0c\x21")
            assert isinstance(msg, HwNetCmdExtendedFamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.EXTENDED_FAMILY
            assert msg.ext_family.family is HwNetFamily.GREEN
            assert msg.ext_family.subfamily is HwNetSubfamily.FLASH_2

    class TestHwNetCmdSetExtendedFamilyMessage:
        def test_constructor(self):
            msg = HwNetCmdSetExtendedFamilyMessage(
                HwNetFamily.GREEN, HwNetSubfamily.FLASH_2
            )
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.EXTENDED_FAMILY_SET
            assert msg.ext_family.family is HwNetFamily.GREEN
            assert msg.ext_family.subfamily is HwNetSubfamily.FLASH_2
            assert (
                repr(msg)
                == "HwNetCmdSetExtendedFamilyMessage(<HwNetFamily.GREEN: 1>, <HwNetSubfamily.FLASH_2: 2>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x08\x0d\x21")
            assert isinstance(msg, HwNetCmdSetExtendedFamilyMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.EXTENDED_FAMILY_SET
            assert msg.ext_family.family is HwNetFamily.GREEN
            assert msg.ext_family.subfamily is HwNetSubfamily.FLASH_2

    class TestHwNetCmdResetLongPressMessage:
        def test_constructor(self):
            msg = HwNetCmdResetLongPressMessage()
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.RESET_LONG_PRESS
            assert repr(msg) == "HwNetCmdResetLongPressMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x04\x00\x08\x0e")
            assert isinstance(msg, HwNetCmdResetLongPressMessage)
            assert msg.length == 4
            assert msg.kind is MessageKind.HW_NET_CMD
            assert msg.cmd is HwNetCmd.RESET_LONG_PRESS


class TestFirmwareMessages:
    class TestFirmwareUpdateMessage:
        def test_constructor(self):
            msg = FirmwareUpdateMessage()
            assert msg.length == 12
            assert msg.kind is MessageKind.FW_UPDATE
            assert msg.key == b"LPF2-Boot"
            assert repr(msg) == "FirmwareUpdateMessage()"

        def test_parse_message(self):
            msg = parse_message(b"\x0c\x00\x10LPF2-Boot")
            assert isinstance(msg, FirmwareUpdateMessage)
            assert msg.length == 12
            assert msg.kind is MessageKind.FW_UPDATE
            assert msg.key == b"LPF2-Boot"


class TestPortInfoMessages:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractPortInfoMessage)

    class TestPortInfoRequestMessage:
        def test_constructor(self):
            msg = PortInfoRequestMessage(PortID(1), InfoKind.PORT_VALUE)
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_INFO_REQ
            assert msg.port is PortID(1)
            assert msg.info_kind is InfoKind.PORT_VALUE
            assert (
                repr(msg)
                == "PortInfoRequestMessage(<PortID.1: 1>, <InfoKind.PORT_VALUE: 0>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x21\x01\x00")
            assert isinstance(msg, PortInfoRequestMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_INFO_REQ
            assert msg.port is PortID(1)
            assert msg.info_kind is InfoKind.PORT_VALUE

    class TestModePortInfoRequestMessage:
        def test_constructor(self):
            msg = PortModeInfoRequestMessage(PortID(1), 2, ModeInfoKind.NAME)
            assert msg.length == 6
            assert msg.kind is MessageKind.PORT_MODE_INFO_REQ
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.info_kind is ModeInfoKind.NAME
            assert (
                repr(msg)
                == "PortModeInfoRequestMessage(<PortID.1: 1>, 2, <ModeInfoKind.NAME: 0>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x06\x00\x22\x01\x02\x00")
            assert isinstance(msg, PortModeInfoRequestMessage)
            assert msg.length == 6
            assert msg.kind is MessageKind.PORT_MODE_INFO_REQ
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.info_kind is ModeInfoKind.NAME

    class TestPortInputFormatSetupMessage:
        def test_constructor(self):
            msg = PortInputFormatSetupMessage(PortID(1), 2, 5, True)
            assert msg.length == 10
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.delta == 5
            assert msg.notify is True
            assert repr(msg) == "PortInputFormatSetupMessage(<PortID.1: 1>, 2, 5, True)"

        def test_parse_message(self):
            msg = parse_message(b"\x0a\x00\x41\x01\x02\x05\x00\x00\x00\x01")
            assert isinstance(msg, PortInputFormatSetupMessage)
            assert msg.length == 10
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.delta == 5
            assert msg.notify is True

    class TestPortFormatSetupComboMessage:
        def test_constructor(self):
            msg = PortFormatSetupComboMessage(PortID(1), [(1, 2), (3, 4)])
            assert msg.length == 7
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
            assert msg.port is PortID(1)
            assert msg.command is PortInfoFormatSetupCommand.SET
            assert msg.modes_and_datasets == [(1, 2), (3, 4)]
            assert (
                repr(msg)
                == "PortFormatSetupComboMessage(<PortID.1: 1>, [(1, 2), (3, 4)])"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x07\x00\x42\x01\x01\x12\x34")
            assert isinstance(msg, PortFormatSetupComboMessage)
            assert msg.length == 7
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
            assert msg.port is PortID(1)
            assert msg.command is PortInfoFormatSetupCommand.SET
            assert msg.modes_and_datasets == [(1, 2), (3, 4)]

    class TestPortFormatSetupComboLockMessage:
        def test_constructor(self):
            msg = PortFormatSetupComboLockMessage(PortID(1))
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
            assert msg.port is PortID(1)
            assert msg.command is PortInfoFormatSetupCommand.LOCK
            assert repr(msg) == "PortFormatSetupComboLockMessage(<PortID.1: 1>)"

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x42\x01\x02")
            assert isinstance(msg, PortFormatSetupComboLockMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
            assert msg.port is PortID(1)
            assert msg.command is PortInfoFormatSetupCommand.LOCK

    class TestPortFormatSetupComboMessages:
        def test_is_abstract(self):
            assert inspect.isabstract(AbstractPortInfoMessage)

        class TestPortFormatSetupComboUnlockEnabledMessage:
            def test_constructor(self):
                msg = PortFormatSetupComboUnlockEnabledMessage(PortID(1))
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.UNLOCK_ENABLED
                assert (
                    repr(msg)
                    == "PortFormatSetupComboUnlockEnabledMessage(<PortID.1: 1>)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x05\x00\x42\x01\x03")
                assert isinstance(msg, PortFormatSetupComboUnlockEnabledMessage)
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.UNLOCK_ENABLED

        class TestPortFormatSetupComboUnlockDisabledMessage:
            def test_constructor(self):
                msg = PortFormatSetupComboUnlockDisabledMessage(PortID(1))
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.UNLOCK_DISABLED
                assert (
                    repr(msg)
                    == "PortFormatSetupComboUnlockDisabledMessage(<PortID.1: 1>)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x05\x00\x42\x01\x04")
                assert isinstance(msg, PortFormatSetupComboUnlockDisabledMessage)
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.UNLOCK_DISABLED

        class TestPortFormatSetupComboResetMessage:
            def test_constructor(self):
                msg = PortFormatSetupComboResetMessage(PortID(1))
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.RESET
                assert repr(msg) == "PortFormatSetupComboResetMessage(<PortID.1: 1>)"

            def test_parse_message(self):
                msg = parse_message(b"\x05\x00\x42\x01\x06")
                assert isinstance(msg, PortFormatSetupComboResetMessage)
                assert msg.length == 5
                assert msg.kind is MessageKind.PORT_INPUT_FMT_SETUP_COMBO
                assert msg.port is PortID(1)
                assert msg.command is PortInfoFormatSetupCommand.RESET

    class TestPortInfoMessages:
        def test_is_abstract(self):
            assert inspect.isabstract(AbstractPortInfoMessage)

        class TestPortInfoModeInfoMessage:
            def test_constructor(self):
                msg = PortInfoModeInfoMessage(
                    PortID(1),
                    ModeCapabilities.INPUT | ModeCapabilities.OUTPUT,
                    num_modes=5,
                    input_modes=[0, 1, 2],
                    output_modes=[3, 4],
                )
                assert msg.length == 11
                assert msg.kind is MessageKind.PORT_INFO
                assert msg.port is PortID(1)
                assert msg.info_kind is InfoKind.MODE_INFO
                assert (
                    msg.capabilities == ModeCapabilities.INPUT | ModeCapabilities.OUTPUT
                )
                assert msg.num_modes == 5
                assert msg.input_modes == [0, 1, 2]
                assert msg.output_modes == [3, 4]
                assert (
                    repr(msg)
                    == "PortInfoModeInfoMessage(<PortID.1: 1>, <ModeCapabilities.INPUT|OUTPUT: 3>, 5, [0, 1, 2], [3, 4])"
                    or repr(msg)
                    == "PortInfoModeInfoMessage(<PortID.1: 1>, <ModeCapabilities.OUTPUT|INPUT: 3>, 5, [0, 1, 2], [3, 4])"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x0b\x00\x43\x01\x01\x03\x05\x07\x00\x18\x00")
                assert isinstance(msg, PortInfoModeInfoMessage)
                assert msg.length == 11
                assert msg.kind is MessageKind.PORT_INFO
                assert msg.port is PortID(1)
                assert msg.info_kind is InfoKind.MODE_INFO
                assert (
                    msg.capabilities == ModeCapabilities.INPUT | ModeCapabilities.OUTPUT
                )
                assert msg.num_modes == 5
                assert msg.input_modes == [0, 1, 2]
                assert msg.output_modes == [3, 4]

        class TestPortInfoCombosMessage:
            def test_constructor(self):
                msg = PortInfoCombosMessage(PortID(1), [[1, 2, 3], [4, 5]])
                assert msg.length == 9
                assert msg.kind is MessageKind.PORT_INFO
                assert msg.port is PortID(1)
                assert msg.info_kind is InfoKind.COMBOS
                assert msg.combos == [[1, 2, 3], [4, 5]]
                assert (
                    repr(msg)
                    == "PortInfoCombosMessage(<PortID.1: 1>, [[1, 2, 3], [4, 5]])"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x09\x00\x43\x01\x02\x0e\x00\x30\x00")
                assert isinstance(msg, PortInfoCombosMessage)
                assert msg.length == 9
                assert msg.kind is MessageKind.PORT_INFO
                assert msg.port is PortID(1)
                assert msg.info_kind is InfoKind.COMBOS
                assert msg.combos == [[1, 2, 3], [4, 5]]

    class TestPortModeInfoMessages:
        def test_is_abstract(self):
            assert inspect.isabstract(AbstractPortModeInfoMessage)

        class TestPortModeInfoNameMessage:
            def test_constructor(self):
                msg = PortModeInfoNameMessage(PortID(1), 2, "MODE")
                assert msg.length == 10
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.NAME
                assert msg.name == "MODE"
                assert repr(msg) == "PortModeInfoNameMessage(<PortID.1: 1>, 2, 'MODE')"

            def test_parse_message(self):
                msg = parse_message(b"\x0a\x00\x44\x01\x02\x00MODE")
                assert isinstance(msg, PortModeInfoNameMessage)
                assert msg.length == 10
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.NAME
                assert msg.name == "MODE"

        class TestPortModeInfoRawMessage:
            def test_constructor(self):
                msg = PortModeInfoRawMessage(PortID(1), 2, 0.0, 255.0)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.RAW
                assert msg.min == 0.0
                assert msg.max == 255.0
                assert (
                    repr(msg) == "PortModeInfoRawMessage(<PortID.1: 1>, 2, 0.0, 255.0)"
                )

            def test_parse_message(self):
                msg = parse_message(
                    b"\x0e\x00\x44\x01\x02\x01\x00\x00\x00\x00\x00\x00\x7f\x43"
                )
                assert isinstance(msg, PortModeInfoRawMessage)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.RAW
                assert msg.min == 0.0
                assert msg.max == 255.0

        class TestPortModeInfoPercentMessage:
            def test_constructor(self):
                msg = PortModeInfoPercentMessage(PortID(1), 2, -100.0, 100.0)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.PCT
                assert msg.min == -100.0
                assert msg.max == 100.0
                assert (
                    repr(msg)
                    == "PortModeInfoPercentMessage(<PortID.1: 1>, 2, -100.0, 100.0)"
                )

            def test_parse_message(self):
                msg = parse_message(
                    b"\x0e\x00\x44\x01\x02\x02\x00\x00\xc8\xc2\x00\x00\xc8\x42"
                )
                assert isinstance(msg, PortModeInfoPercentMessage)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.PCT
                assert msg.min == -100.0
                assert msg.max == 100.0

        class TestPortModeInfoSIMessage:
            def test_constructor(self):
                msg = PortModeInfoSIMessage(PortID(1), 2, 0.0, 1.0)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.SI
                assert msg.min == 0.0
                assert msg.max == 1.0
                assert repr(msg) == "PortModeInfoSIMessage(<PortID.1: 1>, 2, 0.0, 1.0)"

            def test_parse_message(self):
                msg = parse_message(
                    b"\x0e\x00\x44\x01\x02\x03\x00\x00\x00\x00\x00\x00\x80\x3f"
                )
                assert isinstance(msg, PortModeInfoSIMessage)
                assert msg.length == 14
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.SI
                assert msg.min == 0.0
                assert msg.max == 1.0

        class TestPortModeInfoSymbolMessage:
            def test_constructor(self):
                msg = PortModeInfoSymbolMessage(PortID(1), 2, "SYM")
                assert msg.length == 9
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.SYMBOL
                assert msg.symbol == "SYM"
                assert repr(msg) == "PortModeInfoSymbolMessage(<PortID.1: 1>, 2, 'SYM')"

            def test_parse_message(self):
                msg = parse_message(b"\x09\x00\x44\x01\x02\x04SYM")
                assert isinstance(msg, PortModeInfoSymbolMessage)
                assert msg.length == 9
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.SYMBOL
                assert msg.symbol == "SYM"

        class TestPortModeInfoMappingMessage:
            def test_constructor(self):
                msg = PortModeInfoMappingMessage(
                    PortID(1), 2, IODeviceMapping.DISCRETE, IODeviceMapping.RELATIVE
                )
                assert msg.length == 8
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.MAPPING
                assert msg.input_mapping is IODeviceMapping.DISCRETE
                assert msg.output_mapping is IODeviceMapping.RELATIVE
                assert (
                    repr(msg)
                    == "PortModeInfoMappingMessage(<PortID.1: 1>, 2, <IODeviceMapping.DISCRETE: 4>, <IODeviceMapping.RELATIVE: 8>)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x08\x00\x44\x01\x02\x05\x04\x08")
                assert isinstance(msg, PortModeInfoMappingMessage)
                assert msg.length == 8
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.MAPPING
                assert msg.input_mapping is IODeviceMapping.DISCRETE
                assert msg.output_mapping is IODeviceMapping.RELATIVE

        class TestPortModeInfoMotorBiasMessage:
            def test_constructor(self):
                msg = PortModeInfoMotorBiasMessage(PortID(1), 2, 100)
                assert msg.length == 7
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.MOTOR_BIAS
                assert msg.bias == 100
                assert (
                    repr(msg) == "PortModeInfoMotorBiasMessage(<PortID.1: 1>, 2, 100)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x07\x00\x44\x01\x02\x07\x64")
                assert isinstance(msg, PortModeInfoMotorBiasMessage)
                assert msg.length == 7
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.MOTOR_BIAS
                assert msg.bias == 100

        class TestPortModeInfoCapabilitiesMessage:
            def test_constructor(self):
                msg = PortModeInfoCapabilitiesMessage(
                    PortID(1), 2, IODeviceCapabilities(1)
                )
                assert msg.length == 12
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.CAPABILITIES
                assert msg.capabilities is IODeviceCapabilities(1)
                assert (
                    repr(msg)
                    == "PortModeInfoCapabilitiesMessage(<PortID.1: 1>, 2, <IODeviceCapabilities.1: 1>)"
                    or repr(msg)
                    == "PortModeInfoCapabilitiesMessage(<PortID.1: 1>, 2, <IODeviceCapabilities: 1>)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x0c\x00\x44\x01\x02\x08\x01\x00\x00\x00\x00\x00")
                assert isinstance(msg, PortModeInfoCapabilitiesMessage)
                assert msg.length == 12
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.CAPABILITIES
                assert msg.capabilities is IODeviceCapabilities(1)

        class TestPortModeInfoFormatMessage:
            def test_constructor(self):
                msg = PortModeInfoFormatMessage(PortID(1), 2, 1, DataFormat.DATA8, 3, 0)
                assert msg.length == 10
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.FORMAT
                assert msg.datasets == 1
                assert msg.format == DataFormat.DATA8
                assert msg.figures == 3
                assert msg.decimals == 0
                assert (
                    repr(msg)
                    == "PortModeInfoFormatMessage(<PortID.1: 1>, 2, 1, <DataFormat.DATA8: 0>, 3, 0)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x0a\x00\x44\x01\x02\x80\x01\x00\x03\x00")
                assert isinstance(msg, PortModeInfoFormatMessage)
                assert msg.length == 10
                assert msg.kind is MessageKind.PORT_MODE_INFO
                assert msg.port is PortID(1)
                assert msg.mode == 2
                assert msg.info_kind is ModeInfoKind.FORMAT
                assert msg.datasets == 1
                assert msg.format == DataFormat.DATA8
                assert msg.figures == 3
                assert msg.decimals == 0

    class TestPortValueMessage:
        def test_constructor(self):
            msg = PortValueMessage(PortID(1), "<bhi", 2, 3, 4)
            assert msg.length == 11
            assert msg.kind is MessageKind.PORT_VALUE
            assert msg.port is PortID(1)
            assert msg.unpack("<bhi") == (2, 3, 4)
            assert (
                repr(msg)
                == "PortValueMessage(<PortID.1: 1>, '<7b', 2, 3, 0, 4, 0, 0, 0)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x0b\x00\x45\x01\x02\x03\x00\x04\x00\x00\x00")
            assert isinstance(msg, PortValueMessage)
            assert msg.length == 11
            assert msg.kind is MessageKind.PORT_VALUE
            assert msg.port is PortID(1)
            assert msg.unpack("<bhi") == (2, 3, 4)

    class TestPortValueComboMessage:
        def test_constructor(self):
            msg = PortValueComboMessage(PortID(1), [1, 2], "<bhi", 2, 3, 4)
            assert msg.length == 13
            assert msg.kind is MessageKind.PORT_VALUE_COMBO
            assert msg.port is PortID(1)
            assert msg.modes == [1, 2]
            assert msg.unpack("<bhi") == (2, 3, 4)
            assert (
                repr(msg)
                == "PortValueComboMessage(<PortID.1: 1>, [1, 2], '<7b', 2, 3, 0, 4, 0, 0, 0)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x0d\x00\x46\x01\x06\x00\x02\x03\x00\x04\x00\x00\x00")
            assert isinstance(msg, PortValueComboMessage)
            assert msg.length == 13
            assert msg.kind is MessageKind.PORT_VALUE_COMBO
            assert msg.port is PortID(1)
            assert msg.modes == [1, 2]
            assert msg.unpack("<bhi") == (2, 3, 4)

    class TestPortInputFormatMessage:
        def test_constructor(self):
            msg = PortInputFormatMessage(PortID(1), 2, 5, True)
            assert msg.length == 10
            assert msg.kind is MessageKind.PORT_INPUT_FMT
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.delta == 5
            assert msg.notify is True
            assert repr(msg) == "PortInputFormatMessage(<PortID.1: 1>, 2, 5, True)"

        def test_parse_message(self):
            msg = parse_message(b"\x0a\x00\x47\x01\x02\x05\x00\x00\x00\x01")
            assert isinstance(msg, PortInputFormatMessage)
            assert msg.length == 10
            assert msg.kind is MessageKind.PORT_INPUT_FMT
            assert msg.port is PortID(1)
            assert msg.mode == 2
            assert msg.delta == 5
            assert msg.notify is True

    class TestPortInputFormatComboMessage:
        def test_constructor(self):
            msg = PortInputFormatComboMessage(PortID(1), 2, True, [0, 1])
            assert msg.length == 7
            assert msg.kind is MessageKind.PORT_INPUT_FMT_COMBO
            assert msg.port is PortID(1)
            assert msg.combo == 2
            assert msg.multi_update is True
            assert msg.modes_and_datasets == [0, 1]
            assert (
                repr(msg)
                == "PortInputFormatComboMessage(<PortID.1: 1>, 2, True, [0, 1])"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x07\x00\x48\x01\x82\x03\x00")
            assert isinstance(msg, PortInputFormatComboMessage)
            assert msg.length == 7
            assert msg.kind is MessageKind.PORT_INPUT_FMT_COMBO
            assert msg.port is PortID(1)
            assert msg.combo == 2
            assert msg.multi_update is True
            assert msg.modes_and_datasets == [0, 1]


class TestVirtualPortMessages:
    class TestVirtualPortSetupMessages:
        def test_is_abstract(self):
            assert inspect.isabstract(AbstractVirtualPortSetupMessage)

        class TestVirtualPortSetupDisconnectMessage:
            def test_constructor(self):
                msg = VirtualPortSetupDisconnectMessage(PortID(3))
                assert msg.length == 5
                assert msg.kind is MessageKind.VIRTUAL_PORT_SETUP
                assert msg.command is VirtualPortSetupCommand.DISCONNECT
                assert msg.port is PortID(3)
                assert repr(msg) == "VirtualPortSetupDisconnectMessage(<PortID.3: 3>)"

            def test_parse_message(self):
                msg = parse_message(b"\x05\x00\x61\x00\x03")
                assert isinstance(msg, VirtualPortSetupDisconnectMessage)
                assert msg.length == 5
                assert msg.kind is MessageKind.VIRTUAL_PORT_SETUP
                assert msg.command is VirtualPortSetupCommand.DISCONNECT
                assert msg.port is PortID(3)

        class TestVirtualPortSetupConnectMessage:
            def test_constructor(self):
                msg = VirtualPortSetupConnectMessage(PortID(1), PortID(2))
                assert msg.length == 6
                assert msg.kind is MessageKind.VIRTUAL_PORT_SETUP
                assert msg.command is VirtualPortSetupCommand.CONNECT
                assert msg.port_a is PortID(1)
                assert msg.port_b is PortID(2)
                assert (
                    repr(msg)
                    == "VirtualPortSetupConnectMessage(<PortID.1: 1>, <PortID.2: 2>)"
                )

            def test_parse_message(self):
                msg = parse_message(b"\x06\x00\x61\x01\x01\x02")
                assert isinstance(msg, VirtualPortSetupConnectMessage)
                assert msg.length == 6
                assert msg.kind is MessageKind.VIRTUAL_PORT_SETUP
                assert msg.command is VirtualPortSetupCommand.CONNECT
                assert msg.port_a is PortID(1)
                assert msg.port_b is PortID(2)


class TestPortOutputCommandMessages:
    def test_is_abstract(self):
        assert inspect.isabstract(AbstractPortOutputCommandMessage)

    class TestPortOutputCommandWriteDirectMessage:
        def test_constructor(self):
            msg = PortOutputCommandWriteDirectMessage(
                PortID(1), StartInfo.IMMEDIATE, EndInfo.FEEDBACK, b"\xd4\x11\x3a"
            )
            assert msg.length == 9
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD
            assert msg.port is PortID(1)
            assert msg.start is StartInfo.IMMEDIATE
            assert msg.end is EndInfo.FEEDBACK
            assert msg.command is PortOutputCommand.WRITE_DIRECT
            assert msg.payload == b"\xd4\x11\x3a"
            assert (
                repr(msg)
                == "PortOutputCommandWriteDirectMessage(<PortID.1: 1>, <StartInfo.IMMEDIATE: 16>, <EndInfo.FEEDBACK: 1>, b'\\xd4\\x11:')"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x09\x00\x81\x01\x11\x50\xd4\x11\x3a")
            assert isinstance(msg, PortOutputCommandWriteDirectMessage)
            assert msg.length == 9
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD
            assert msg.port is PortID(1)
            assert msg.start is StartInfo.IMMEDIATE
            assert msg.end is EndInfo.FEEDBACK
            assert msg.command is PortOutputCommand.WRITE_DIRECT
            assert msg.payload == b"\xd4\x11\x3a"

    class TestPortOutputCommandWriteDirectModeDataMessage:
        def test_constructor(self):
            msg = PortOutputCommandWriteDirectModeDataMessage(
                PortID(1), StartInfo.IMMEDIATE, EndInfo.FEEDBACK, 2, "<i", 100
            )
            assert msg.length == 11
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD
            assert msg.port is PortID(1)
            assert msg.start is StartInfo.IMMEDIATE
            assert msg.end is EndInfo.FEEDBACK
            assert msg.command is PortOutputCommand.WRITE_DIRECT_MODE_DATA
            assert msg.mode == 2
            assert msg.unpack("<i") == (100,)
            assert (
                repr(msg)
                == "PortOutputCommandWriteDirectModeDataMessage(<PortID.1: 1>, <StartInfo.IMMEDIATE: 16>, <EndInfo.FEEDBACK: 1>, 2, '<4b', 100, 0, 0, 0)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x0b\x00\x81\x01\x11\x51\x02\x64\x00\x00\x00")
            assert isinstance(msg, PortOutputCommandWriteDirectModeDataMessage)
            assert msg.length == 11
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD
            assert msg.port is PortID(1)
            assert msg.start is StartInfo.IMMEDIATE
            assert msg.end is EndInfo.FEEDBACK
            assert msg.command is PortOutputCommand.WRITE_DIRECT_MODE_DATA
            assert msg.mode == 2
            assert msg.unpack("<i") == (100,)

    class TestPortOutputCommandFeedbackMessage:
        def test_constructor_1(self):
            msg = PortOutputCommandFeedbackMessage(
                PortID(1), Feedback.BUFFER_EMPTY_IN_PROGRESS
            )
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD_FEEDBACK
            assert msg.port1 is PortID(1)
            assert msg.feedback1 is Feedback.BUFFER_EMPTY_IN_PROGRESS
            assert msg.port2 is None
            assert msg.feedback2 is None
            assert msg.port3 is None
            assert msg.feedback3 is None
            assert (
                repr(msg)
                == "PortOutputCommandFeedbackMessage(<PortID.1: 1>, <Feedback.BUFFER_EMPTY_IN_PROGRESS: 1>, None, None, None, None)"
            )

        def test_constructor_2(self):
            msg = PortOutputCommandFeedbackMessage(
                PortID(1),
                Feedback.BUFFER_EMPTY_COMPLETED,
                PortID(2),
                Feedback.BUFFER_EMPTY_IN_PROGRESS,
            )
            assert msg.length == 7
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD_FEEDBACK
            assert msg.port1 is PortID(1)
            assert msg.feedback1 is Feedback.BUFFER_EMPTY_COMPLETED
            assert msg.port2 is PortID(2)
            assert msg.feedback2 is Feedback.BUFFER_EMPTY_IN_PROGRESS
            assert msg.port3 is None
            assert msg.feedback3 is None
            assert (
                repr(msg)
                == "PortOutputCommandFeedbackMessage(<PortID.1: 1>, <Feedback.BUFFER_EMPTY_COMPLETED: 2>, <PortID.2: 2>, <Feedback.BUFFER_EMPTY_IN_PROGRESS: 1>, None, None)"
            )

        def test_constructor_3(self):
            msg = PortOutputCommandFeedbackMessage(
                PortID(1),
                Feedback.BUFFER_EMPTY_COMPLETED,
                PortID(2),
                Feedback.BUFFER_EMPTY_IN_PROGRESS,
                PortID(3),
                Feedback.BUSY,
            )
            assert msg.length == 9
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD_FEEDBACK
            assert msg.port1 is PortID(1)
            assert msg.feedback1 is Feedback.BUFFER_EMPTY_COMPLETED
            assert msg.port2 is PortID(2)
            assert msg.feedback2 is Feedback.BUFFER_EMPTY_IN_PROGRESS
            assert msg.port3 is PortID(3)
            assert msg.feedback3 is Feedback.BUSY
            assert (
                repr(msg)
                == "PortOutputCommandFeedbackMessage(<PortID.1: 1>, <Feedback.BUFFER_EMPTY_COMPLETED: 2>, <PortID.2: 2>, <Feedback.BUFFER_EMPTY_IN_PROGRESS: 1>, <PortID.3: 3>, <Feedback.BUSY: 16>)"
            )

        def test_parse_message(self):
            msg = parse_message(b"\x05\x00\x82\x01\x01")
            assert isinstance(msg, PortOutputCommandFeedbackMessage)
            assert msg.length == 5
            assert msg.kind is MessageKind.PORT_OUTPUT_CMD_FEEDBACK
            assert msg.port1 is PortID(1)
            assert msg.feedback1 is Feedback.BUFFER_EMPTY_IN_PROGRESS
            assert msg.port2 is None
            assert msg.feedback2 is None
            assert msg.port3 is None
            assert msg.feedback3 is None
