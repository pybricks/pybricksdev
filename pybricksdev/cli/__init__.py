# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2024 The Pybricks Authors

"""Command line wrapper around pybricksdev library."""

import argparse
import asyncio
import contextlib
import logging
import os
import socket
import sys
from abc import ABC, abstractmethod
from os import PathLike, path
from tempfile import NamedTemporaryFile
from typing import ContextManager, TextIO

import argcomplete
from argcomplete.completers import FilesCompleter

from pybricksdev import __name__ as MODULE_NAME
from pybricksdev import __version__ as MODULE_VERSION

PROG_NAME = (
    f"{path.basename(sys.executable)} -m {MODULE_NAME}"
    if sys.argv[0].endswith("__main__.py")
    else path.basename(sys.argv[0])
)


class Tool(ABC):
    """Common base class for tool implementations."""

    @abstractmethod
    def add_parser(self, subparsers: argparse._SubParsersAction):
        """
        Overriding methods must at least do the following::

            parser = subparsers.add_parser('tool', ...)
            parser.tool = self

        Then additional arguments can be added using the ``parser`` object.
        """
        pass

    @abstractmethod
    async def run(self, args: argparse.Namespace):
        """
        Overriding methods should provide an implementation to run the tool.
        """
        pass


def _get_script_path(file: TextIO) -> ContextManager[PathLike]:
    """
    Gets the path to a script on the file system.

    If the file is ``sys.stdin``, the contents are copied to a temporary file
    and the path to the temporary file is returned. Otherwise, the file is closed
    and the path is returned.

    The context manager will delete the temporary file, if applicable.
    """
    if file is sys.stdin:
        # Have to close the temp file so that mpy-cross can read it, so we
        # create our own context manager to delete the file when we are done
        # using it.

        @contextlib.contextmanager
        def temp_context():
            try:
                with NamedTemporaryFile(suffix=".py", delete=False) as temp:
                    temp.write(file.buffer.read())

                yield temp.name
            finally:
                try:
                    os.remove(temp.name)
                except NameError:
                    # if NamedTemporaryFile() throws, temp is not defined
                    pass
                except OSError:
                    # file was already deleted or other strangeness
                    pass

        return temp_context()

    file.close()
    return contextlib.nullcontext(file.name)


class Compile(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "compile",
            help="compile a Pybricks program without running it",
        )
        parser.add_argument(
            "file",
            metavar="<file>",
            help="path to a MicroPython script or `-` for stdin",
            type=argparse.FileType(),
        )
        parser.add_argument(
            "--abi",
            metavar="<n>",
            help="the MPY ABI version, one of %(choices)s (default: %(default)s)",
            default=6,
            choices=[5, 6],
            type=int,
        )
        parser.tool = self

    async def run(self, args: argparse.Namespace):
        from pybricksdev.compile import compile_multi_file, print_mpy

        with _get_script_path(args.file) as script_path:
            mpy = await compile_multi_file(script_path, args.abi)
        print_mpy(mpy)


class Run(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "run",
            help="run a Pybricks program",
        )
        parser.tool = self
        parser.add_argument(
            "conntype",
            metavar="<connection type>",
            help="connection type: %(choices)s",
            choices=["ble", "usb", "ssh"],
        )
        parser.add_argument(
            "file",
            metavar="<file>",
            help="path to a MicroPython script or `-` for stdin",
            type=argparse.FileType(),
        )
        parser.add_argument(
            "-n",
            "--name",
            metavar="<name>",
            required=False,
            help="hostname or IP address for SSH connection; "
            "Bluetooth device name or Bluetooth address for BLE connection; "
            "serial port name for USB connection",
        )

        if hasattr(argparse, "BooleanOptionalAction"):
            # BooleanOptionalAction requires Python 3.9
            parser.add_argument(
                "--wait",
                help="wait for the program to complete before disconnecting",
                action=argparse.BooleanOptionalAction,
                default=True,
            )
        else:
            parser.add_argument(
                "--wait",
                help="wait for the program to complete before disconnecting (default)",
                action="store_true",
                default=True,
            )
            parser.add_argument(
                "--no-wait",
                help="disconnect as soon as program is done downloading",
                action="store_false",
                dest="wait",
            )

    async def run(self, args: argparse.Namespace):

        # Pick the right connection
        if args.conntype == "ssh":
            from pybricksdev.connections.ev3dev import EV3Connection

            # So it's an ev3dev
            if args.name is None:
                print("--name is required for SSH connections", file=sys.stderr)
                exit(1)

            device_or_address = socket.gethostbyname(args.name)
            hub = EV3Connection(device_or_address)
        elif args.conntype == "ble":
            from pybricksdev.ble import find_device as find_ble
            from pybricksdev.connections.pybricks import PybricksHubBLE

            # It is a Pybricks Hub with BLE. Device name or address is given.
            print(f"Searching for {args.name or 'any hub with Pybricks service'}...")
            device_or_address = await find_ble(args.name)
            hub = PybricksHubBLE(device_or_address)
        elif args.conntype == "usb":
            from usb.core import find as find_usb

            from pybricksdev.connections.pybricks import PybricksHubUSB
            from pybricksdev.usb import (
                LEGO_USB_VID,
                MINDSTORMS_INVENTOR_USB_PID,
                SPIKE_ESSENTIAL_USB_PID,
                SPIKE_PRIME_USB_PID,
            )

            def is_pybricks_usb(dev):
                return (
                    (dev.idVendor == LEGO_USB_VID)
                    and (
                        dev.idProduct
                        in [
                            SPIKE_PRIME_USB_PID,
                            SPIKE_ESSENTIAL_USB_PID,
                            MINDSTORMS_INVENTOR_USB_PID,
                        ]
                    )
                    and dev.product.endswith("Pybricks")
                )

            device_or_address = find_usb(custom_match=is_pybricks_usb)

            if device_or_address is not None:
                hub = PybricksHubUSB(device_or_address)
            else:
                from pybricksdev.connections.lego import REPLHub

                hub = REPLHub()
        else:
            raise ValueError(f"Unknown connection type: {args.conntype}")

        # Connect to the address and run the script
        await hub.connect()
        try:
            with _get_script_path(args.file) as script_path:
                await hub.run(script_path, args.wait)
        finally:
            await hub.disconnect()


class Download(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "download",
            help="upload a Pybricks program without running it",
        )
        parser.tool = self
        parser.add_argument(
            "conntype",
            metavar="<connection type>",
            help="connection type: %(choices)s",
            choices=["ble", "usb", "ssh"],
        )
        parser.add_argument(
            "file",
            metavar="<file>",
            help="path to a MicroPython script or `-` for stdin",
            type=argparse.FileType(),
        )
        parser.add_argument(
            "-n",
            "--name",
            metavar="<name>",
            required=False,
            help="hostname or IP address for SSH connection; "
            "Bluetooth device name or Bluetooth address for BLE connection; "
            "serial port name for USB connection",
        )

    async def run(self, args: argparse.Namespace):
        # Pick the right connection
        if args.conntype == "ssh":
            from pybricksdev.connections.ev3dev import EV3Connection

            # So it's an ev3dev
            if args.name is None:
                print("--name is required for SSH connections", file=sys.stderr)
                exit(1)

            device_or_address = socket.gethostbyname(args.name)
            hub = EV3Connection(device_or_address)
        elif args.conntype == "ble":
            from pybricksdev.ble import find_device as find_ble
            from pybricksdev.connections.pybricks import PybricksHubBLE

            # It is a Pybricks Hub with BLE. Device name or address is given.
            print(f"Searching for {args.name or 'any hub with Pybricks service'}...")
            device_or_address = await find_ble(args.name)
            hub = PybricksHubBLE(device_or_address)
        elif args.conntype == "usb":
            from usb.core import find as find_usb

            from pybricksdev.connections.pybricks import PybricksHubUSB
            from pybricksdev.usb import (
                LEGO_USB_VID,
                MINDSTORMS_INVENTOR_USB_PID,
                SPIKE_ESSENTIAL_USB_PID,
                SPIKE_PRIME_USB_PID,
            )

            def is_pybricks_usb(dev):
                return (
                    (dev.idVendor == LEGO_USB_VID)
                    and (
                        dev.idProduct
                        in [
                            SPIKE_PRIME_USB_PID,
                            SPIKE_ESSENTIAL_USB_PID,
                            MINDSTORMS_INVENTOR_USB_PID,
                        ]
                    )
                    and dev.product.endswith("Pybricks")
                )

            device_or_address = find_usb(custom_match=is_pybricks_usb)

            if device_or_address is not None:
                hub = PybricksHubUSB(device_or_address)
            else:
                from pybricksdev.connections.lego import REPLHub

                hub = REPLHub()
        else:
            raise ValueError(f"Unknown connection type: {args.conntype}")

        # Connect to the address and upload the script without running it
        await hub.connect()
        try:
            with _get_script_path(args.file) as script_path:
                await hub.download(script_path)
        finally:
            await hub.disconnect()


class Flash(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "flash", help="flash firmware on a LEGO Powered Up device"
        )
        parser.tool = self

        parser.add_argument(
            "firmware",
            metavar="<firmware-file>",
            type=argparse.FileType(mode="rb"),
            help="the firmware .zip file",
        ).completer = FilesCompleter(allowednames=(".zip",))

        parser.add_argument(
            "-n", "--name", metavar="<name>", type=str, help="a custom name for the hub"
        )

    def run(self, args: argparse.Namespace):
        from pybricksdev.cli.flash import flash_firmware

        return flash_firmware(args.firmware, args.name)


class DFUBackup(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser("backup", help="backup firmware using DFU")
        parser.tool = self
        parser.add_argument(
            "firmware",
            metavar="<firmware-file>",
            type=argparse.FileType(mode="wb"),
            help="the firmware .bin file",
        ).completer = FilesCompleter(allowednames=(".bin",))

    async def run(self, args: argparse.Namespace):
        from pybricksdev.dfu import backup_dfu

        backup_dfu(args.firmware)


class DFURestore(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "restore",
            help="restore firmware using DFU",
        )
        parser.tool = self
        parser.add_argument(
            "firmware",
            metavar="<firmware-file>",
            type=argparse.FileType(mode="rb"),
            help="the firmware .bin file",
        ).completer = FilesCompleter(allowednames=(".bin",))

    async def run(self, args: argparse.Namespace):
        from pybricksdev.dfu import restore_dfu

        restore_dfu(args.firmware)


class DFU(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        self.parser = subparsers.add_parser(
            "dfu",
            help="use DFU to backup or restore firmware",
        )
        self.parser.tool = self
        self.subparsers = self.parser.add_subparsers(
            metavar="<action>", dest="action", help="the action to perform"
        )

        for tool in DFUBackup(), DFURestore():
            tool.add_parser(self.subparsers)

    def run(self, args: argparse.Namespace):
        if args.action not in self.subparsers.choices:
            self.parser.error(
                f'Missing name of action: {"|".join(self.subparsers.choices.keys())}'
            )

        return self.subparsers.choices[args.action].tool.run(args)


class OADFlash(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "flash",
            help="update firmware on a LEGO Powered Up device using TI OAD",
        )
        parser.tool = self
        parser.add_argument(
            "firmware",
            metavar="<firmware-file>",
            type=argparse.FileType(mode="rb"),
            help="the firmware .oda file",
        ).completer = FilesCompleter(allowednames=(".oda",))

    async def run(self, args: argparse.Namespace):
        from pybricksdev.cli.oad import flash_oad_image

        await flash_oad_image(args.firmware)


class OADInfo(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "info",
            help="get information about firmware on a LEGO Powered Up device using TI OAD",
        )
        parser.tool = self

    async def run(self, args: argparse.Namespace):
        from pybricksdev.cli.oad import dump_oad_info

        await dump_oad_info()


class OAD(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        self.parser = subparsers.add_parser(
            "oad",
            help="update firmware on a LEGO Powered Up device using TI OAD",
        )
        self.parser.tool = self
        self.subparsers = self.parser.add_subparsers(
            metavar="<action>", dest="action", help="the action to perform"
        )

        for tool in OADFlash(), OADInfo():
            tool.add_parser(self.subparsers)

    def run(self, args: argparse.Namespace):
        if args.action not in self.subparsers.choices:
            self.parser.error(
                f'Missing name of action: {"|".join(self.subparsers.choices.keys())}'
            )

        return self.subparsers.choices[args.action].tool.run(args)


class LWP3Repl(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "repl",
            help="interactive REPL for sending and receiving LWP3 messages",
        )
        parser.tool = self

    def run(self, args: argparse.Namespace):
        from pybricksdev.cli.lwp3.repl import repl, setup_repl_logging

        setup_repl_logging()
        return repl()


class LWP3(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        self.parser = subparsers.add_parser(
            "lwp3", help="interact with devices using LWP3"
        )
        self.parser.tool = self
        self.subparsers = self.parser.add_subparsers(
            metavar="<lwp3-tool>", dest="lwp3_tool", help="the tool to run"
        )

        for tool in (LWP3Repl(),):
            tool.add_parser(self.subparsers)

    def run(self, args: argparse.Namespace):
        if args.lwp3_tool not in self.subparsers.choices:
            self.parser.error(
                f'Missing name of tool: {"|".join(self.subparsers.choices.keys())}'
            )

        return self.subparsers.choices[args.lwp3_tool].tool.run(args)


class Udev(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser("udev", help="print udev rules to stdout")
        parser.tool = self

    async def run(self, args: argparse.Namespace):
        from importlib.resources import read_text

        from pybricksdev import resources

        print(read_text(resources, resources.UDEV_RULES))


def main():
    """Runs ``pybricksdev`` command line interface."""

    if sys.platform == "win32":
        # Hack around bad side-effects of pythoncom on Windows
        try:
            from bleak_winrt._winrt import MTA, init_apartment
        except ImportError:
            from winrt._winrt import MTA, init_apartment

        init_apartment(MTA)

    # Provide main description and help.
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description="Utilities for Pybricks developers.",
        epilog="Run `%(prog)s <tool> --help` for tool-specific arguments.",
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"{MODULE_NAME} v{MODULE_VERSION}"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="enable debug logging"
    )

    subparsers = parser.add_subparsers(
        metavar="<tool>",
        dest="tool",
        help="the tool to use",
    )

    for tool in Compile(), Run(), Download(), Flash(), DFU(), OAD(), LWP3(), Udev():
        tool.add_parser(subparsers)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s: %(levelname)s: %(name)s: %(message)s",
        level=logging.DEBUG if args.debug else logging.WARNING,
    )

    if not args.tool:
        parser.error(f'Missing name of tool: {"|".join(subparsers.choices.keys())}')

    asyncio.run(subparsers.choices[args.tool].tool.run(args))
