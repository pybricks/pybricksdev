# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors
# Some portions of the documentation:
# Copyright (c) 2018 LEGO System A/S

"""
The LWP3 :mod:`messages` module contains classes for encoding and decoding
messages used in the `LWP3 protocol`_.

.. _LWP3 protocol: https://lego.github.io/lego-ble-wireless-protocol-docs/
"""

import abc
from enum import IntEnum
import struct
from typing import Any, Dict, NamedTuple, Optional, Type, Union

from .bytecodes import (
    AlertKind,
    AlertOperation,
    AlertStatus,
    BatteryKind,
    BluetoothAddress,
    ErrorCode,
    HubAction,
    HubKind,
    HubProperty,
    HubPropertyOperation,
    HwNetCmd,
    HwNetExtFamily,
    HwNetFamily,
    HwNetSubfamily,
    IODeviceKind,
    IOEvent,
    LWPVersion,
    LastNetwork,
    MAX_NAME_SIZE,
    MessageKind,
    PortID,
    Version,
)


class AbstractMessage(abc.ABC):
    """Common base class for all messages."""

    def __init__(self, length: int, kind: MessageKind) -> None:
        super().__init__()

        if not isinstance(length, int):
            raise TypeError("length must be int")

        if not isinstance(kind, MessageKind):
            raise TypeError("kind must be MessageKind")

        self._data = bytearray(length)
        self._data[0] = length
        self._data[2] = kind

    def __bytes__(self) -> bytes:
        return bytes(self._data)

    @property
    def length(self) -> int:
        """Gets the length of the message in bytes."""
        return self._data[0]

    @property
    def kind(self) -> MessageKind:
        """Gets the kind of message."""
        return MessageKind(self._data[2])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class AbstractHubPropertyMessage(AbstractMessage):
    """Common base class for hub property messages."""

    def __init__(
        self, length: int, prop: HubProperty, op: HubPropertyOperation
    ) -> None:
        """
        Args:
            length: Length of the message in bytes.
            prop: The property.
            op: The operation to perform.

        Raises:
            TypeError:
                ``prop`` is not a :class:`HubProperty` or ``op`` is not a
                :class:`HubPropertyOperation`.
            ValueError:
                ``op`` cannot be applied to ``prop``
        """
        super().__init__(length, MessageKind.HUB_PROPERTY)

        if not isinstance(prop, HubProperty):
            raise TypeError("prop must be HubProperty")

        if op not in _HUB_PROPERTY_OPS_MAP[prop]:
            raise ValueError(f"cannot perform {op} on {prop}")

        if not isinstance(op, HubPropertyOperation):
            raise TypeError("op must be HubPropertyOperation")

        self._data[3] = prop
        self._data[4] = op

    @property
    def prop(self) -> HubProperty:
        """Gets the property that is acted on."""
        return HubProperty(self._data[3])

    @property
    def op(self) -> HubPropertyOperation:
        """Gets the operation."""
        return HubPropertyOperation(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.prop)})"


class _HubPropertyType(NamedTuple):
    type: type
    fmt: str
    max_size: Optional[int] = None


# specifies payload type information for each property
_HUB_PROPERTY_TYPE_MAP = {
    HubProperty.NAME: _HubPropertyType(str, "s", MAX_NAME_SIZE),
    HubProperty.BUTTON: _HubPropertyType(bool, "?"),
    HubProperty.FW_VERSION: _HubPropertyType(Version, "i"),
    HubProperty.HW_VERSION: _HubPropertyType(Version, "i"),
    HubProperty.RSSI: _HubPropertyType(int, "b"),
    HubProperty.BATTERY_VOLTAGE: _HubPropertyType(int, "B"),
    HubProperty.BATTERY_KIND: _HubPropertyType(BatteryKind, "B"),
    HubProperty.MFG_NAME: _HubPropertyType(str, "s", 15),
    HubProperty.RADIO_FW_VERSION: _HubPropertyType(str, "s", 15),
    HubProperty.LWP_VERSION: _HubPropertyType(LWPVersion, "H"),
    HubProperty.HUB_KIND: _HubPropertyType(HubKind, "B"),
    HubProperty.HW_NET_ID: _HubPropertyType(LastNetwork, "B"),
    HubProperty.BDADDR: _HubPropertyType(BluetoothAddress, "6s"),
    HubProperty.BOOTLOADER_BDADDR: _HubPropertyType(BluetoothAddress, "6s"),
    HubProperty.HW_NET_FAMILY: _HubPropertyType(HwNetFamily, "B"),
}

Op = HubPropertyOperation

# specifies supported operations for each property
_HUB_PROPERTY_OPS_MAP = {
    HubProperty.NAME: [
        Op.SET,
        Op.ENABLE_UPDATES,
        Op.DISABLE_UPDATES,
        Op.RESET,
        Op.REQUEST_UPDATE,
        Op.UPDATE,
    ],
    HubProperty.BUTTON: [
        Op.ENABLE_UPDATES,
        Op.DISABLE_UPDATES,
        Op.REQUEST_UPDATE,
        Op.UPDATE,
    ],
    HubProperty.FW_VERSION: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.HW_VERSION: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.RSSI: [
        Op.ENABLE_UPDATES,
        Op.DISABLE_UPDATES,
        Op.REQUEST_UPDATE,
        Op.UPDATE,
    ],
    HubProperty.BATTERY_VOLTAGE: [
        Op.ENABLE_UPDATES,
        Op.DISABLE_UPDATES,
        Op.REQUEST_UPDATE,
        Op.UPDATE,
    ],
    HubProperty.BATTERY_KIND: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.MFG_NAME: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.RADIO_FW_VERSION: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.LWP_VERSION: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.HUB_KIND: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.HW_NET_ID: [Op.SET, Op.RESET, Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.BDADDR: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.BOOTLOADER_BDADDR: [Op.REQUEST_UPDATE, Op.UPDATE],
    HubProperty.HW_NET_FAMILY: [Op.SET, Op.REQUEST_UPDATE, Op.UPDATE],
}

del Op


class AbstractHubPropertyValueMessage(AbstractHubPropertyMessage):
    """Common base class for hub property messages that have a value parameter."""

    _MAX_VALUE_SIZE = 15  # largest known value size

    def __init__(self, prop: HubProperty, op: HubPropertyOperation, value: Any) -> None:
        """
        Args:
            prop: The property.
            value: The new value.

        Raises:
            TypeError: ``value`` is not the correct type for ``prop``.
            ValueError: ``prop`` cannot be set.
        """
        # allocate enough for max size - length will be adjusted later
        super().__init__(5 + self._MAX_VALUE_SIZE, prop, op)

        meta = _HUB_PROPERTY_TYPE_MAP[self.prop]

        if not isinstance(value, meta.type):
            raise TypeError(
                f"expecting value of type {meta.type} but received {type(value)}"
            )

        if meta.max_size is None:
            # fixed size
            fmt = meta.fmt
        else:
            # variable size
            if isinstance(value, str):
                value = value.encode()

            if len(value) > meta.max_size:
                raise ValueError("length of value is too long")

            fmt = f"{len(value)}{meta.fmt}"

        # override the length
        self._data[0] = 5 + struct.calcsize(fmt)
        self._data = memoryview(self._data)[: self.length]

        struct.pack_into(fmt, self._data, 5, value)

    @property
    def value(self) -> Any:
        """Gets the property value."""

        meta = _HUB_PROPERTY_TYPE_MAP[self.prop]

        if meta.max_size is None:
            fmt = meta.fmt
        else:
            fmt = f"{self.length - 5}{meta.fmt}"

        (result,) = struct.unpack_from(fmt, self._data, 5)

        if meta.type == str:
            return result.decode()

        return meta.type(result)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.prop)}, {repr(self.value)})"


class HubPropertySet(AbstractHubPropertyValueMessage):
    """Hub property set message."""

    def __init__(self, prop: HubProperty, value: Any) -> None:
        """
        Args:
            prop: The property.
            value: The new value.

        Raises:
            TypeError: ``value`` is not the correct type for ``prop``.
            ValueError: ``prop`` cannot be set.
        """
        super().__init__(prop, HubPropertyOperation.SET, value)


class HubPropertyEnableUpdates(AbstractHubPropertyMessage):
    """Hub property enable updates message."""

    def __init__(self, prop: HubProperty) -> None:
        """
        Args:
            prop: The property.

        Raises:
            ValueError: ``prop`` does not allow enabling updates.
        """
        super().__init__(5, prop, HubPropertyOperation.ENABLE_UPDATES)


class HubPropertyDisableUpdates(AbstractHubPropertyMessage):
    """Hub property disable updates message."""

    def __init__(self, prop: HubProperty) -> None:
        """
        Args:
            prop: The property.

        Raises:
            ValueError: ``prop`` does not allow disabling updates.
        """
        super().__init__(5, prop, HubPropertyOperation.DISABLE_UPDATES)


class HubPropertyReset(AbstractHubPropertyMessage):
    """Hub property reset message."""

    def __init__(self, prop: HubProperty) -> None:
        """
        Args:
            prop: The property.

        Raises:
            ValueError: ``prop`` does not allow reset.
        """
        super().__init__(5, prop, HubPropertyOperation.RESET)


class HubPropertyRequestUpdate(AbstractHubPropertyMessage):
    """Hub property request update message."""

    def __init__(self, prop: HubProperty) -> None:
        """
        Args:
            prop: The property.
        """
        super().__init__(5, prop, HubPropertyOperation.REQUEST_UPDATE)


class HubPropertyUpdate(AbstractHubPropertyValueMessage):
    """Hub property update message."""

    def __init__(self, prop: HubProperty, value: Any) -> None:
        """
        Args:
            prop: The property.
            value: The new value.

        Raises:
            TypeError: if ``value`` is not the correct type for ``prop``.
        """
        super().__init__(prop, HubPropertyOperation.UPDATE, value)


class HubActionMessage(AbstractMessage):
    """
    This message allows for performing control actions on the connected Hub.
    """

    def __init__(self, action: HubAction) -> None:
        """
        Args:
            action: The action.
        """
        super().__init__(4, MessageKind.HUB_ACTION)

        self._data[3] = action

    @property
    def action(self) -> HubAction:
        """Gets the action."""
        return HubAction(self._data[3])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.action)})"


class AbstractHubAlertMessage(AbstractMessage):
    """Common base type for all hub alert messages."""

    def __init__(self, length: int, alert: AlertKind, op: AlertOperation) -> None:
        super().__init__(length, MessageKind.HUB_ALERT)

        self._data[3] = alert
        self._data[4] = op

    @property
    def alert(self) -> AlertKind:
        """Gets the kind of alert."""
        return AlertKind(self._data[3])

    @property
    def op(self) -> AlertOperation:
        """Gets the operation to be performed."""
        return AlertOperation(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.alert)})"


class HubAlertEnableUpdatesMessage(AbstractHubAlertMessage):
    """
    Message to subscribe to updates for an alert.
    """

    def __init__(self, alert: AlertKind) -> None:
        super().__init__(5, alert, AlertOperation.ENABLE_UPDATES)


class HubAlertDisableUpdatesMessage(AbstractHubAlertMessage):
    """
    Message to unsubscribe from updates for an alert.
    """

    def __init__(self, alert: AlertKind) -> None:
        super().__init__(5, alert, AlertOperation.DISABLE_UPDATES)


class HubAlertRequestUpdateMessage(AbstractHubAlertMessage):
    """
    Message to request the current status for an alert.
    """

    def __init__(self, alert: AlertKind) -> None:
        super().__init__(5, alert, AlertOperation.REQUEST_UPDATE)


class HubAlertUpdateMessage(AbstractHubAlertMessage):
    """
    Message that contains the current status of an alert.
    """

    def __init__(self, alert: AlertKind, status: AlertStatus) -> None:
        super().__init__(6, alert, AlertOperation.UPDATE)

        self._data[5] = status

    @property
    def status(self) -> AlertStatus:
        """Gets the status of the alert."""
        return AlertStatus(self._data[5])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.alert)}, {repr(self.status)})"


class AbstractHubAttachedIOMessage(AbstractMessage):
    def __init__(self, length: int, port: PortID, event: IOEvent) -> None:
        super().__init__(length, MessageKind.HUB_ATTACHED_IO)

        self._data[3] = port
        self._data[4] = event

    @property
    def port(self) -> PortID:
        """Gets the I/O port ID."""
        return PortID(self._data[3])

    @property
    def event(self) -> IOEvent:
        """Gets the I/O port event."""
        return IOEvent(self._data[4])


class HubIODetachedMessage(AbstractHubAttachedIOMessage):
    def __init__(self, port: PortID) -> None:
        super().__init__(5, port, IOEvent.DETACHED)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.port)})"


class HubIOAttachedMessage(AbstractHubAttachedIOMessage):
    def __init__(
        self, port: PortID, device: IODeviceKind, hw_ver: Version, fw_ver: Version
    ) -> None:
        super().__init__(15, port, IOEvent.ATTACHED)

        struct.pack_into("<Hii", self._data, 5, device, hw_ver, fw_ver)

    @property
    def device(self) -> IODeviceKind:
        """Gets the kind of device that is attached."""
        (result,) = struct.unpack_from("<H", self._data, 5)
        return IODeviceKind(result)

    @property
    def hw_ver(self) -> Version:
        """Gets the hardware version of the device."""
        (result,) = struct.unpack_from("<i", self._data, 7)
        return Version(result)

    @property
    def fw_ver(self) -> Version:
        """Gets the firmware version of the device."""
        (result,) = struct.unpack_from("<i", self._data, 11)
        return Version(result)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.port)}, {repr(self.device)}, {repr(self.hw_ver)}, {repr(self.fw_ver)})"


class HubIOAttachedVirtualMessage(AbstractHubAttachedIOMessage):
    def __init__(
        self, port: PortID, device: IODeviceKind, port_a: PortID, port_b: PortID
    ) -> None:
        super().__init__(9, port, IOEvent.ATTACHED_VIRTUAL)

        struct.pack_into("<HBB", self._data, 5, device, port_a, port_b)

    @property
    def device(self) -> IODeviceKind:
        """Gets the kind of device that is attached."""
        (result,) = struct.unpack_from("<H", self._data, 5)
        return IODeviceKind(result)

    @property
    def port_a(self) -> Version:
        """Gets the first port of the virtual device."""
        return PortID(self._data[7])

    @property
    def port_b(self) -> Version:
        """Gets the second port of the virtual device."""
        return PortID(self._data[8])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.port)}, {repr(self.device)}, {repr(self.port_a)}, {repr(self.port_b)})"


class ErrorMessage(AbstractMessage):
    """Generic error message."""

    def __init__(self, command: MessageKind, code: ErrorCode) -> None:
        """
        Args:
            command: The kind of message that triggered the error.
            code: An error code describing the error.
        """
        super().__init__(5, MessageKind.ERROR)

        self._data[3] = command
        self._data[4] = code

    @property
    def command(self) -> MessageKind:
        """Gets the kind of message that triggered the error."""
        return MessageKind(self._data[3])

    @property
    def code(self) -> ErrorCode:
        """Gets an error code describing the error."""
        return ErrorCode(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.command)}, {repr(self.code)})"


class AbstractHwNetCmdMessage(AbstractMessage):
    def __init__(self, length: int, cmd: HwNetCmd) -> None:
        super().__init__(length, MessageKind.HW_NET_CMD)

        self._data[3] = cmd

    @property
    def cmd(self) -> HwNetCmd:
        return HwNetCmd(self._data[3])


class HwNetCmdRequestConnectionMessage(AbstractHwNetCmdMessage):
    def __init__(self, button_pressed: bool) -> None:
        super().__init__(5, HwNetCmd.CONNECTION_REQUEST)

        self._data[4] = button_pressed

    @property
    def button_pressed(self) -> bool:
        return bool(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.button_pressed)})"


class HwNetCmdRequestFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.FAMILY_REQUEST)


class HwNetCmdSetFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, family: HwNetFamily) -> None:
        super().__init__(5, HwNetCmd.FAMILY_SET)

        self._data[4] = family

    @property
    def family(self) -> HwNetFamily:
        return HwNetFamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.family)})"


class HwNetCmdJoinDeniedMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.JOIN_DENIED)


class HwNetCmdGetFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.GET_FAMILY)


class HwNetCmdFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, family: HwNetFamily) -> None:
        super().__init__(5, HwNetCmd.FAMILY)

        self._data[4] = family

    @property
    def family(self) -> HwNetFamily:
        return HwNetFamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.family)})"


class HwNetCmdGetSubfamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.GET_SUBFAMILY)


class HwNetCmdSubfamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, subfamily: HwNetSubfamily) -> None:
        super().__init__(5, HwNetCmd.SUBFAMILY)

        self._data[4] = subfamily

    @property
    def subfamily(self) -> HwNetSubfamily:
        return HwNetSubfamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.subfamily)})"


class HwNetCmdSetSubfamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, subfamily: HwNetSubfamily) -> None:
        super().__init__(5, HwNetCmd.SUBFAMILY_SET)

        self._data[4] = subfamily

    @property
    def subfamily(self) -> HwNetSubfamily:
        return HwNetSubfamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.subfamily)})"


class HwNetCmdGetExtendedFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.GET_EXTENDED_FAMILY)


class HwNetCmdExtendedFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, family: HwNetFamily, subfamily: HwNetSubfamily) -> None:
        super().__init__(5, HwNetCmd.EXTENDED_FAMILY)

        self._data[4] = family + subfamily

    @property
    def ext_family(self) -> HwNetExtFamily:
        return HwNetExtFamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.ext_family.family)}, {repr(self.ext_family.subfamily)})"


class HwNetCmdSetExtendedFamilyMessage(AbstractHwNetCmdMessage):
    def __init__(self, family: HwNetFamily, subfamily: HwNetSubfamily) -> None:
        super().__init__(5, HwNetCmd.EXTENDED_FAMILY_SET)

        self._data[4] = family + subfamily

    @property
    def ext_family(self) -> HwNetExtFamily:
        return HwNetExtFamily(self._data[4])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.ext_family.family)}, {repr(self.ext_family.subfamily)})"


class HwNetCmdResetLongPressMessage(AbstractHwNetCmdMessage):
    def __init__(self) -> None:
        super().__init__(4, HwNetCmd.RESET_LONG_PRESS)


class FirmwareUpdateMessage(AbstractMessage):
    """
    Instructs the hub to reboot in firmware update mode.
    """

    def __init__(self) -> None:
        super().__init__(12, MessageKind.FW_UPDATE)

        self._data[3:] = b"LPF2-Boot"

    @property
    def key(self) -> bytes:
        """Safety string."""
        return self._data[3:]


###############################################################################
# Message parsing
###############################################################################


class _Lookup(NamedTuple):
    """Type descriminator."""

    index: int
    """The index of the bytecode that determines the type."""

    value: Union[Dict[IntEnum, Type[AbstractMessage]], Dict[IntEnum, "_Lookup"]]
    """
    A dictionary mapping a bytecode to the cooresponding Python type if the type can be determined or
    a dictionary mapping a bytecode to another lookup if more discrimination is required.
    """


# type descriminator for hub property message types
_HUB_PROPERTY_OP_CLASS_MAP = {
    HubPropertyOperation.SET: HubPropertySet,
    HubPropertyOperation.ENABLE_UPDATES: HubPropertyEnableUpdates,
    HubPropertyOperation.DISABLE_UPDATES: HubPropertyDisableUpdates,
    HubPropertyOperation.RESET: HubPropertyReset,
    HubPropertyOperation.REQUEST_UPDATE: HubPropertyRequestUpdate,
    HubPropertyOperation.UPDATE: HubPropertyUpdate,
}

# type descriminator for hub alert message types
_HUB_ALERT_OP_CLASS_MAP = {
    AlertOperation.ENABLE_UPDATES: HubAlertEnableUpdatesMessage,
    AlertOperation.DISABLE_UPDATES: HubAlertDisableUpdatesMessage,
    AlertOperation.REQUEST_UPDATE: HubAlertRequestUpdateMessage,
    AlertOperation.UPDATE: HubAlertUpdateMessage,
}

# type descriminator for hub attached I/O message types
_HUB_ATTACHED_IO_EVENT_CLASS_MAP = {
    IOEvent.DETACHED: HubIODetachedMessage,
    IOEvent.ATTACHED: HubIOAttachedMessage,
    IOEvent.ATTACHED_VIRTUAL: HubIOAttachedVirtualMessage,
}

# type descriminator for hardware network command message types
_HW_NET_CMD_CLASS_MAP = {
    HwNetCmd.CONNECTION_REQUEST: HwNetCmdRequestConnectionMessage,
    HwNetCmd.FAMILY_REQUEST: HwNetCmdRequestFamilyMessage,
    HwNetCmd.FAMILY_SET: HwNetCmdSetFamilyMessage,
    HwNetCmd.JOIN_DENIED: HwNetCmdJoinDeniedMessage,
    HwNetCmd.GET_FAMILY: HwNetCmdGetFamilyMessage,
    HwNetCmd.FAMILY: HwNetCmdFamilyMessage,
    HwNetCmd.GET_SUBFAMILY: HwNetCmdGetSubfamilyMessage,
    HwNetCmd.SUBFAMILY: HwNetCmdSubfamilyMessage,
    HwNetCmd.SUBFAMILY_SET: HwNetCmdSetSubfamilyMessage,
    HwNetCmd.GET_EXTENDED_FAMILY: HwNetCmdGetExtendedFamilyMessage,
    HwNetCmd.EXTENDED_FAMILY: HwNetCmdExtendedFamilyMessage,
    HwNetCmd.EXTENDED_FAMILY_SET: HwNetCmdSetExtendedFamilyMessage,
    HwNetCmd.RESET_LONG_PRESS: HwNetCmdResetLongPressMessage,
}

# base type descriminator for messages
_MESSAGE_CLASS_MAP = {
    MessageKind.HUB_PROPERTY: _Lookup(4, _HUB_PROPERTY_OP_CLASS_MAP),
    MessageKind.HUB_ACTION: HubActionMessage,
    MessageKind.HUB_ALERT: _Lookup(4, _HUB_ALERT_OP_CLASS_MAP),
    MessageKind.HUB_ATTACHED_IO: _Lookup(4, _HUB_ATTACHED_IO_EVENT_CLASS_MAP),
    MessageKind.ERROR: ErrorMessage,
    MessageKind.HW_NET_CMD: _Lookup(3, _HW_NET_CMD_CLASS_MAP),
    MessageKind.FW_UPDATE: FirmwareUpdateMessage,
}


def parse_message(data: bytes) -> AbstractMessage:
    """
    Parses ``data`` and returns a message object.

    Args:
        data: Raw binary data of the message.

    Returns:
        A new message object whose type corresponds to the message data.
    """
    cls = _Lookup(2, _MESSAGE_CLASS_MAP)
    while isinstance(cls, _Lookup):
        kind = data[cls.index]
        cls = cls.value[kind]

    # bypass __init__() since we already have the encoded data
    msg = object.__new__(cls)
    msg._data = data

    return msg
