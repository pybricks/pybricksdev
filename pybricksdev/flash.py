# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2021 The Pybricks Authors

import asyncio
import io
import json
import logging
import os
import platform
import struct
import sys
import zipfile
from collections import namedtuple
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

import semver
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from .ble import BLERequestsConnection
from .ble.lwp3 import BootloaderCommand
from .ble.lwp3.bytecodes import HubKind
from .compile import compile_file, save_script
from .tools.checksum import crc32_checksum, sum_complement

logger = logging.getLogger(__name__)


async def create_firmware(
    firmware_zip: Union[str, os.PathLike, BinaryIO], name: Optional[str] = None
) -> Tuple[bytes, dict]:
    """Creates a firmware blob from base firmware and main.mpy file.

    Arguments:
        firmware_zip:
            Path to the firmware zip file or a file-like object.
        name:
            A custom name for the hub.

    Returns:
        bytes: Composite binary blob with correct padding and checksum.
        dict: Meta data for this firmware file.

    Raises:
        ValueError:
            A name is given but the firmware does not support it or the name
            exceeds the alloted space in the firmware.

    """

    archive = zipfile.ZipFile(firmware_zip)
    base = archive.open("firmware-base.bin").read()
    main_py = io.TextIOWrapper(archive.open("main.py"))
    metadata = json.load(archive.open("firmware.metadata.json"))

    mpy = await compile_file(
        save_script(main_py.read()),
        metadata["mpy-cross-options"],
        metadata["mpy-abi-version"],
    )

    # start with base firmware binary blob
    firmware = bytearray(base)
    # pad with 0s until user-mpy-offset
    firmware.extend(0 for _ in range(metadata["user-mpy-offset"] - len(firmware)))
    # append 32-bit little-endian main.mpy file size
    firmware.extend(struct.pack("<I", len(mpy)))
    # append main.mpy file
    firmware.extend(mpy)
    # pad with 0s to align to 4-byte boundary
    firmware.extend(0 for _ in range(-len(firmware) % 4))

    if name:
        if semver.compare(metadata["metadata-version"], "1.1.0") < 0:
            raise ValueError(
                "this firmware image does not support setting the hub name"
            )

        name = name.encode() + b"\0"

        max_size = metadata["max-hub-name-size"]
        if len(name) > max_size:
            raise ValueError(
                f"name is too big - must be < {metadata['max-hub-name-size']} UTF-8 bytes"
            )

        offset = metadata["hub-name-offset"]
        firmware[offset : offset + len(name)] = name

    # append 32-bit little-endian checksum
    if metadata["checksum-type"] == "sum":
        firmware.extend(
            struct.pack(
                "<I",
                sum_complement(io.BytesIO(firmware), metadata["max-firmware-size"] - 4),
            )
        )
    elif metadata["checksum-type"] == "crc32":
        firmware.extend(
            struct.pack(
                "<I",
                crc32_checksum(io.BytesIO(firmware), metadata["max-firmware-size"] - 4),
            )
        )
    else:
        print(f'Unknown checksum type "{metadata["checksum-type"]}"', file=sys.stderr)
        exit(1)

    return firmware, metadata


# NAME, PAYLOAD_SIZE requirement
HUB_INFO: Dict[HubKind, Tuple[str, int]] = {
    HubKind.BOOST: ("Move Hub", 14),
    HubKind.CITY: ("City Hub", 32),
    HubKind.TECHNIC: ("Technic Hub", 32),
}


class BootloaderRequest:
    """Bootloader request structure."""

    def __init__(
        self,
        command: BootloaderCommand,
        name: str,
        request_format: List[str],
        data_format: str,
        request_reply: bool = True,
        write_with_response: bool = True,
    ):
        self.command = command
        self.ReplyClass = namedtuple(name, request_format)
        self.data_format = data_format
        self.reply_len = struct.calcsize(data_format)
        if request_reply:
            self.reply_len += 1
        self.write_with_response = write_with_response

    def make_request(self, payload: Optional[bytes] = None) -> bytearray:
        request = bytearray([self.command])
        if payload is not None:
            request += payload
        return request

    def parse_reply(self, reply) -> namedtuple:
        if reply[0] == self.command:
            return self.ReplyClass(*struct.unpack(self.data_format, reply[1:]))
        else:
            raise ValueError(
                f"Expecting reply to {self.command.name} but received {BootloaderCommand(reply[0]).name}"
            )


class BootloaderConnection(BLERequestsConnection):
    """Connect to Powered Up Hub Bootloader and update firmware."""

    # Static BootloaderRequest instances for particular messages

    # We could probably do write with response for this command on all hubs, but
    # the response is not received until after flashing is finished, which could
    # cause a timeout, especially for hubs that take longer to erase.
    ERASE_FLASH = BootloaderRequest(
        BootloaderCommand.ERASE_FLASH,
        "Erase",
        ["result"],
        "<B",
        write_with_response=False,
    )

    # City hub bootloader always sends write response for most commands even
    # when write without response is used which confuses Bluetooth stacks, so
    # we always have to do write with response.
    ERASE_FLASH_CITY_HUB = BootloaderRequest(
        BootloaderCommand.ERASE_FLASH, "Erase", ["result"], "<B"
    )

    # Only the final flash message receives a reply.
    PROGRAM_FLASH = BootloaderRequest(
        BootloaderCommand.PROGRAM_FLASH,
        "Flash",
        [],
        "",
        request_reply=False,
        write_with_response=False,
    )

    PROGRAM_FLASH_FINAL = BootloaderRequest(
        BootloaderCommand.PROGRAM_FLASH,
        "Flash",
        ["checksum", "count"],
        "<BI",
        write_with_response=False,
    )

    # This reboots the hub, so Bluetooth is disconnected and we don't receive
    # a reply.
    START_APP = BootloaderRequest(
        BootloaderCommand.START_APP,
        "Start",
        [],
        "",
        request_reply=False,
        write_with_response=False,
    )

    INIT_LOADER = BootloaderRequest(
        BootloaderCommand.INIT_LOADER, "Init", ["result"], "<B"
    )

    GET_INFO = BootloaderRequest(
        BootloaderCommand.GET_INFO,
        "Info",
        ["version", "start_addr", "end_addr", "type_id"],
        "<iIIB",
    )

    GET_CHECKSUM = BootloaderRequest(
        BootloaderCommand.GET_CHECKSUM, "Checksum", ["checksum"], "<B"
    )

    GET_FLASH_STATE = BootloaderRequest(
        BootloaderCommand.GET_FLASH_STATE, "State", ["level"], "<B"
    )

    DISCONNECT = BootloaderRequest(
        BootloaderCommand.DISCONNECT,
        "Disconnect",
        [],
        "",
        request_reply=False,
        write_with_response=False,
    )

    def __init__(self):
        """Initialize the BLE Connection for Bootloader service."""
        super().__init__("00001626-1212-efde-1623-785feabcd123")
        self.ignore_erase_reply = False

    async def bootloader_request(self, request, payload=None, timeout=None):
        """Sends a message to the bootloader and awaits corresponding reply."""

        # Get message command and expected reply length
        logger.debug("Clear and prepare reply")
        self.prepare_reply()

        # Write message
        logger.debug("Make and write request")
        data = request.make_request(payload)
        await self.write(data, request.write_with_response)

        # If we expect a reply, await for it
        if request.reply_len > 0:
            logger.debug("Awaiting reply")
            reply = await self.wait_for_reply(timeout)
            # Windows may receive reply from erase command at the wrong time
            if self.ignore_erase_reply and reply[0] == BootloaderCommand.ERASE_FLASH:
                reply = await self.wait_for_reply(timeout)
            return request.parse_reply(reply)

    async def flash(self, firmware, metadata):

        # Firmware information
        firmware_io = io.BytesIO(firmware)
        firmware_size = len(firmware)

        # Request hub information
        logger.debug("Getting device info.")
        info = await self.bootloader_request(self.GET_INFO)
        logger.debug(info)

        # Hub specific settings
        hub_name, max_data_size = HUB_INFO[info.type_id]

        # Verify hub ID against ID in firmware package
        if info.type_id != metadata["device-id"]:
            await self.disconnect()
            raise RuntimeError(
                "This firmware {0}, but we are connected to {1}.".format(
                    HUB_INFO[metadata["device-id"]][0], hub_name
                )
            )

        # Erase existing firmware
        logger.debug("Erasing flash.")
        try:
            # Windows sometimes doesn't receive the reply to this command at all
            # or until another command is sent (buggy Bluetooth drivers?) so we
            # have a few hacks to special case this. City hub further complicates
            # things by having a buggy Bluetooth implementation in its bootloader.
            response = await self.bootloader_request(
                self.ERASE_FLASH_CITY_HUB
                if info.type_id == HubKind.CITY and not platform.system() == "Windows"
                else self.ERASE_FLASH,
                timeout=5,
            )
            logger.debug(response)
        except asyncio.TimeoutError:
            self.ignore_erase_reply = True
            logger.info("did not receive erase reply, continuing anyway")

        # Get the bootloader ready to accept the firmware
        logger.debug("Request begin update.")
        response = await self.bootloader_request(
            request=self.INIT_LOADER, payload=struct.pack("<I", firmware_size)
        )
        logger.debug(response)
        logger.debug("Begin update.")

        # Maintain progress using tqdm
        with logging_redirect_tqdm(), tqdm(
            total=firmware_size, unit="B", unit_scale=True
        ) as pbar:

            def reader():
                while True:
                    payload = firmware_io.read(max_data_size)
                    if not payload:
                        return
                    yield payload

            address = info.start_addr

            # Repeat until the whole firmware has been processed
            for i, payload in enumerate(reader()):
                # Since there is no feedback from the hub when writing the
                # firmware data, we need to periodically do something to get
                # a response back from the hub. We use the checksum command
                # for this as a hack. This throttles the speed of sending data
                # to a rate that can be handled by both the sender and the hub.
                if i % 10 == 9:
                    result = await self.bootloader_request(
                        self.GET_CHECKSUM, timeout=0.5
                    )
                    logger.debug(result)

                # Check if this is the last chunk to be sent
                if firmware_io.tell() == firmware_size:
                    # If so, request flash with confirmation request.
                    request = self.PROGRAM_FLASH_FINAL
                else:
                    # Otherwise, do not wait for confirmation.
                    request = self.PROGRAM_FLASH

                # Pack the data in the expected format
                data = struct.pack(
                    f"<BI{len(payload)}B", len(payload) + 4, address, *payload
                )
                response = await self.bootloader_request(request, data)
                logger.debug(response)
                pbar.update(len(payload))
                address += len(payload)

        # Reboot the hub
        logger.debug("Request reboot.")
        response = await self.bootloader_request(self.START_APP)
        logger.debug(response)
