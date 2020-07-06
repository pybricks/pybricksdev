# PYTHON_ARGCOMPLETE_OK

"""Command line wrapper around pybricksdev library."""

import argparse
import asyncio
import logging
import sys
import validators

from abc import ABC, abstractmethod
from os import path

import argcomplete

from argcomplete.completers import ChoicesCompleter, FilesCompleter

from . import __name__ as MODULE_NAME, __version__ as MODULE_VERSION


PROG_NAME = (f'{path.basename(sys.executable)} -m {MODULE_NAME}'
             if sys.argv[0].endswith('__main__.py') else path.basename(sys.argv[0]))


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


def _parse_script_arg(script_arg):
    """Save user script argument to a file if it is a Python one-liner."""
    from .compile import save_script

    if not path.exists(script_arg):
        return save_script(script_arg)
    return script_arg


class Compile(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            'compile',
            help='compile a Pybricks program without running it',
        )
        parser.tool = self
        # The argument is a filename or a Python one-liner.
        parser.add_argument(
            'script',
            metavar='<script>',
            help='path to a MicroPython script or inline script',
        )

    async def run(self, args: argparse.Namespace):
        from .compile import compile_file, print_mpy

        script_path = _parse_script_arg(args.script)

        # Compile the script and print the result
        mpy = await compile_file(script_path)
        print_mpy(mpy)


class Run(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            'run',
            help='run a Pybricks program',
        )
        parser.tool = self
        parser.add_argument(
            'conntype',
            metavar='<connection type>',
            help='Connection type',
            choices=['ble', 'usb', 'ssh']
        )
        parser.add_argument(
            'device',
            metavar='<device>',
            help='hostname or IP address or Bluetooth device name or Bluetooth address',
        )
        parser.add_argument(
            'script',
            metavar='<script>',
            help='path to a MicroPython script or inline script',
        )

    async def run(self, args: argparse.Namespace):
        from .ble import find_device
        from .connections import BLEPUPConnection, EV3Connection, USBPUPConnection

        # Convert script argument to valid path
        script_path = _parse_script_arg(args.script)

        # Pick the right connection
        if args.conntype == 'ssh':
            # So it's an ev3dev
            if not validators.ip_address.ipv4(args.device):
                raise ValueError("Device must be IP address.")
            hub = EV3Connection()
            address = args.device
        elif args.conntype == 'ble':
            # It is a Pybricks Hub with BLE. Device name or address is given.
            hub = BLEPUPConnection()
            if validators.mac_address(args.device):
                address = args.device
            else:
                address = await find_device(args.device, timeout=5)
        elif args.conntype == 'usb':
            # It's a Pybricks Hub with USB. Port name is given.
            hub = USBPUPConnection()
            address = args.device

        # Connect to the address and run the script
        hub.logger.setLevel(logging.INFO)

        await hub.connect(address)
        await hub.run(script_path)
        await hub.disconnect()


class Flash(Tool):
    def add_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            'flash',
            help='flash firmware on a LEGO Powered Up device'
        )
        parser.tool = self
        parser.add_argument(
            'firmware',
            metavar='<firmware-file>',
            type=argparse.FileType(mode='rb'),
            help='the firmware file',
        ).completer = FilesCompleter(allowednames=('.zip',))
        parser.add_argument(
            '-d',
            '--delay',
            dest='delay',
            metavar='<milliseconds>',
            type=int,
            default=10,
            help='delay between Bluetooth packets (default: %(default)i)',
        ).completer = ChoicesCompleter([5, 10, 15, 20])

    async def run(self, args: argparse.Namespace):
        from .ble import find_device
        from .flash import create_firmware, BootloaderConnection

        print('Creating firmware')
        firmware, metadata = await create_firmware(args.firmware)
        address = await find_device('LEGO Bootloader', 15)
        print('Found:', address)
        updater = BootloaderConnection()
        updater.logger.setLevel(logging.INFO)
        await updater.connect(address)
        print('Erasing flash and starting update')
        await updater.flash(firmware, metadata, args.delay/1000)


def entry():
    """Main entry point to the pybricksdev command line utility."""

    # Provide main description and help.
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description='Utilities for Pybricks developers.',
        epilog='Run `%(prog)s <tool> --help` for tool-specific arguments.',
    )

    parser.add_argument('-v', '--version', action='version', version=f'{MODULE_NAME} v{MODULE_VERSION}')

    subparsers = parser.add_subparsers(
        metavar='<tool>',
        dest='tool',
        help='the tool to use',
    )

    for tool in Compile(), Run(), Flash():
        tool.add_parser(subparsers)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if not args.tool:
        parser.error(f'Missing name of tool: {"|".join(subparsers.choices.keys())}')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(subparsers.choices[args.tool].tool.run(args))


if __name__ == "__main__":
    entry()
