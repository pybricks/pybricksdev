# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

"""
The :mod:`pybricks.cli.lwp3.repl` module provides a command line interface
for connecting to a device and sending and receiving LWP3 messages.
"""

import asyncio
import inspect
import logging
import os
import re
import struct
from enum import Enum
from pathlib import Path

from appdirs import user_cache_dir
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import StdoutProxy, patch_stdout

from pybricksdev.ble.lwp3 import (
    LEGO_CID,
    LWP3_HUB_CHARACTERISTIC_UUID,
    LWP3_HUB_SERVICE_UUID,
    bytecodes,
    messages,
)
from pybricksdev.ble.lwp3.bytecodes import Capabilities, HubKind, LastNetwork, Status
from pybricksdev.ble.lwp3.messages import AbstractMessage, parse_message

logger = logging.getLogger(__name__)
history_file = Path(user_cache_dir("pybricksdev"), "lwp3-explorer-history.txt")

# Get names that are valid for evaluating on the REPL.
# This hides built-in functions to avoid arbitrary code execution.
_eval_pool = {"__builtins__": {}}

# TODO: these dicts can be used for tab completion on the REPL

# The first groups is any type from bytecodes that inherits from int (includes
# enums/flags) or bytes.
_PARAMETER_TYPES = {
    k: v
    for k, v in bytecodes.__dict__.items()
    if inspect.isclass(v)
    and v.__module__ == bytecodes.__name__
    and (issubclass(v, int) or issubclass(v, bytes))
}

_eval_pool.update(_PARAMETER_TYPES)

# The second group are all of the non-abstract message types from the messages module.
_MESSAGE_KINDS = {
    k: v
    for k, v in messages.__dict__.items()
    if inspect.isclass(v)
    and issubclass(v, AbstractMessage)
    and not inspect.isabstract(v)
}

_eval_pool.update(_MESSAGE_KINDS)


class _CommandCompleter(Completer):
    """
    Custom completer for command prompt.
    """

    # matches words with dots in them, e.g. "Enum.MEMBER"
    _MATCH_DOT = re.compile(r"[a-zA-Z0-9_\.]+")

    def get_completions(self, document: Document, complete_event):
        if document.get_word_before_cursor() == ".":
            # if this is a dotted word, look up the enum member
            cls = _PARAMETER_TYPES.get(
                document.get_word_before_cursor(pattern=self._MATCH_DOT).split(".")[0]
            )
            if cls and issubclass(cls, Enum):
                for m in cls:
                    if m.name.startswith("_"):
                        continue
                    yield Completion(m.name)
        elif document.find_enclosing_bracket_left("(", ")") is not None:
            # if we are inside of "(...)", list the enums and other parameter types
            for p in _PARAMETER_TYPES.keys():
                yield Completion(p)
        elif document.get_word_under_cursor() == "":
            # if we are at the beginning of the line, list the commands
            for m in _MESSAGE_KINDS.keys():
                yield Completion(m)


async def repl() -> None:
    """
    Provides an interactive REPL for sending and receiving LWP3 messages.
    """
    os.makedirs(history_file.parent, exist_ok=True)

    session = PromptSession(
        history=FileHistory(history_file),
        completer=FuzzyCompleter(_CommandCompleter()),
    )

    def match_lwp3_uuid(dev: BLEDevice, adv: AdvertisementData) -> None:
        if LWP3_HUB_SERVICE_UUID.lower() not in adv.service_uuids:
            return False

        mfg_data = adv.manufacturer_data[LEGO_CID]
        button, kind, cap, last_net, status, opt = struct.unpack("<6B", mfg_data)
        button = bool(button)
        kind = HubKind(kind)
        cap = Capabilities(cap)
        last_net = LastNetwork(last_net)
        status = Status(status)
        logger.debug(
            "button: %s, kind: %s, cap: %s, last net: %s, status: %s, option: %s",
            button,
            kind,
            cap,
            last_net,
            status,
            opt,
        )

        return True

    logger.info("scanning...")

    device = await BleakScanner.find_device_by_filter(match_lwp3_uuid)

    if device is None:
        logger.error("timed out")
        return

    logger.info("found device")

    repl_task = asyncio.current_task()

    def handle_disconnect(client: BleakClient):
        repl_task.cancel()

    try:
        async with BleakClient(
            device, disconnected_callback=handle_disconnect
        ) as client:
            logger.info("connected")

            def handle_notify(handle, value):
                try:
                    msg = parse_message(value)
                except Exception as ex:
                    logger.warning("failed to parse message: %s", value, exc_info=ex)
                else:
                    logger.info("received: %s", msg)

            await client.start_notify(LWP3_HUB_CHARACTERISTIC_UUID, handle_notify)

            # welcome is delayed to allow initial log messages to settle.
            async def welcome():
                await asyncio.sleep(1)
                print("Type message and press ENTER to send. Press CTRL+D to exit.")

            asyncio.ensure_future(welcome())

            while True:
                with patch_stdout():
                    try:
                        result = await session.prompt_async(">>> ")
                    except KeyboardInterrupt:
                        # CTRL+C ignores the line
                        continue
                    except EOFError:
                        # CTRL+D exits the program
                        break
                try:
                    msg = eval(result, _eval_pool)
                    if not isinstance(msg, AbstractMessage):
                        raise ValueError("not a message object")
                except SyntaxError as ex:
                    logger.error(
                        "%s\n\n    %s\n   %s",
                        ex.msg,
                        ex.text,
                        " " * ex.offset + "^" * (ex.end_offset - ex.offset),
                    )
                except Exception:
                    logger.exception("unexpected error:")
                else:
                    logger.info("sending: %s", msg)
                    await client.write_gatt_char(
                        LWP3_HUB_CHARACTERISTIC_UUID, bytes(msg), response=True
                    )

            logger.info("disconnecting...")
    except asyncio.CancelledError:
        # happens on disconnect
        pass

    logger.info("disconnected")


def setup_repl_logging() -> None:
    """
    Overrides logging as needed for :func:`repl`.
    """
    logging.basicConfig(
        stream=StdoutProxy(),
        format="[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logger.setLevel(logging.INFO)


if __name__ == "__main__":
    setup_repl_logging()
    asyncio.run(repl())
