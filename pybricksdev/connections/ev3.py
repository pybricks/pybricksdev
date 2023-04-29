# SPDX-License-Identifier: MIT
# Copyright (c) 2023 The Pybricks Authors

import asyncio
import enum
import itertools
import struct
from typing import Callable, Optional, Tuple

import hid

from ..tools import chunk

LEGO_VENDOR_ID = 0x0694
EV3_PRODUCT_ID = 0x0005
EV3_BOOTLOADER_PRODUCT_ID = 0x0006


class MessageType(enum.IntEnum):
    SYSTEM_COMMAND_REPLY = 0x01
    SYSTEM_COMMAND_NO_REPLY = 0x81
    SYSTEM_REPLY = 0x03
    SYSTEM_REPLY_ERROR = 0x05


class ReplyStatusCode(enum.IntEnum):
    SUCCESS = 0x00
    UNKNOWN_HANDLE = 0x01
    HANDLE_NOT_READY = 0x02
    CORRUPT_FILE = 0x03
    NO_HANDLES_AVAILABLE = 0x04
    NO_PERMISSION = 0x05
    ILLEGAL_PATH = 0x06
    FILE_EXISTS = 0x07
    END_OF_FILE = 0x08
    SIZE_ERROR = 0x09
    UNKNOWN_ERROR = 0x0A
    ILLEGAL_FILENAME = 0x0B
    ILLEGAL_CONNECTION = 0x0C


class Command(enum.IntEnum):
    BEGIN_DOWNLOAD_WITH_ERASE = 0xF0
    BEGIN_DOWNLOAD = 0xF1
    DOWNLOAD_DATA = 0xF2
    CHIP_ERASE = 0xF3
    START_APP = 0xF4
    GET_CHECKSUM = 0xF5
    GET_VERSION = 0xF6


class ReplyError(Exception):
    def __init__(self, status: ReplyStatusCode):
        super().__init__(status.name, status.value)


class EV3Bootloader:
    """
    Connection to LEGO MINDSTORMS EV3 bootloader for flashing firmware.
    """

    _MAX_DATA_SIZE = 1018
    """Max number of bytes that can be written at one time."""

    def __init__(self):
        self._device = hid.device()
        self._msg_count = itertools.count()

    def open(self) -> None:
        """
        Opens an HID connection to the EV3 bootloader.
        """
        self._device.open(
            vendor_id=LEGO_VENDOR_ID, product_id=EV3_BOOTLOADER_PRODUCT_ID
        )

    def close(self) -> None:
        """
        Closes the underlying HID connection.
        """
        self._device.close()

    def _send_command(self, command: Command, payload: Optional[bytes] = None) -> int:
        length = 4

        if payload is not None:
            if len(payload) > self._MAX_DATA_SIZE:
                raise ValueError("payload is too large")

            length += len(payload)

        message_number = next(self._msg_count)

        message = struct.pack(
            "<HHBB",
            length,
            message_number,
            MessageType.SYSTEM_COMMAND_REPLY,
            command,
        )

        if payload is not None:
            message += payload

        self._device.write(message)

        return message_number

    def _receive_reply(self, command: Command, message_number: int) -> bytes:
        """
        Receive a reply from the EV3 bootloader.

        Args:
            command: The command that was sent.
            message_number: The return value of :meth:`_send_command`.

        Returns:
            The payload of the reply.
        """
        reply = bytes(self._device.read(255))
        length, reply_number, message_type, reply_command, status = struct.unpack_from(
            "<HHBBB", reply
        )

        if reply_number != message_number:
            raise RuntimeError(
                "message sequence number mismatch: {reply_number} != {message_number}"
            )

        if message_type == MessageType.SYSTEM_REPLY_ERROR:
            raise ReplyError(status)

        if message_type != MessageType.SYSTEM_REPLY:
            raise RuntimeError("unexpected message type: {message_type}")

        if reply_command != command:
            raise RuntimeError("command mismatch: {reply_command} != {command}")

        return reply[7 : length + 2]

    def download_sync(
        self,
        address: int,
        data: bytes,
        progress: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        Blocking version of :meth:`download`.
        """
        param_data = struct.pack("<II", address, len(data))
        num = self._send_command(Command.BEGIN_DOWNLOAD, param_data)
        self._receive_reply(Command.BEGIN_DOWNLOAD, num)

        for c in chunk(data, self._MAX_DATA_SIZE):
            num = self._send_command(Command.DOWNLOAD_DATA, c)
            self._receive_reply(Command.DOWNLOAD_DATA, num)

            if progress:
                progress(len(c))

    async def download(
        self,
        address: int,
        data: bytes,
        progress: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        Downloads a firmware blob to the EV3.

        This operation takes about 60 seconds for a full 16MB firmware file.

        Args:
            address: The starting address of where to write the data.
            data: The data to write.
            progress: Optional callback for indicating progress.
        """
        return await asyncio.get_running_loop().run_in_executor(
            None, self.download_sync, address, data, progress
        )

    def erase_chip_sync(self) -> None:
        """
        Blocking version of :meth:`erase_chip`.
        """
        num = self._send_command(Command.CHIP_ERASE)
        self._receive_reply(Command.CHIP_ERASE, num)

    async def erase_chip(self) -> None:
        """
        Erases the external flash memory chip.

        This operation takes about 60 seconds.
        """
        return await asyncio.get_running_loop().run_in_executor(
            None,
            self.erase_chip_sync,
        )

    def start_app_sync(self) -> None:
        """
        Blocking version of :meth:`start_app`.
        """
        num = self._send_command(Command.START_APP)
        self._receive_reply(Command.START_APP, num)

    async def start_app(self) -> None:
        """
        Starts the app from external flash memory.
        """
        return await asyncio.get_running_loop().run_in_executor(
            None,
            self.start_app_sync,
        )

    def get_checksum_sync(self, address: int, size: int) -> int:
        """
        Blocking version of :meth:`get_checksum`.
        """
        payload = struct.pack("<II", address, size)
        num = self._send_command(Command.GET_CHECKSUM, payload)
        payload = self._receive_reply(Command.GET_CHECKSUM, num)
        return struct.unpack("<I", payload)[0]

    async def get_checksum(self, address: int, size: int) -> int:
        """
        Gets the checksum of a memory range.

        Args:
            address: The starting address.
            size: The size of data in bytes used to compute the checksum.

        Returns:
            The checksum.
        """
        return await asyncio.get_running_loop().run_in_executor(
            None, self.get_checksum_sync, address, size
        )

    def get_version_sync(self) -> Tuple[int, int]:
        """
        Blocking version of :meth:`get_version`.
        """
        num = self._send_command(Command.GET_VERSION)
        payload = self._receive_reply(Command.GET_VERSION, num)
        return struct.unpack("<II", payload)

    async def get_version(self) -> Tuple[int, int]:
        """
        Gets the bootloader firmware version and the hardware version.

        Returns:
            Tuple containing the firmware and hardware versions.
        """
        return await asyncio.get_running_loop().run_in_executor(
            None,
            self.get_version_sync,
        )

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self) -> None:
        self.close()
