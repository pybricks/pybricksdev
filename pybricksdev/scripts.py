"""Command line wrapper around pybricksdev library. Do not import from here."""

import argparse
import asyncio
import logging
from os import path
import validators

from pybricksdev.compile import save_script, compile_file, print_mpy
from pybricksdev.connections import PUPConnection, EV3Connection
from pybricksdev.ble import find_device


def _compile(args):
    """pybricksdev compile"""
    parser = argparse.ArgumentParser(
        prog='pybricksdev compile',
        description='Compile a Pybricks program without running it.',
    )
    # The argument is a filename or a Python one-liner.
    parser.add_argument('script')
    script = parser.parse_args(args).script

    # If the user does not provide a file, assume they provide Python code.
    if not path.exists(script):
        script = save_script(script)

    # Compile the script and print the result
    mpy = asyncio.run(compile_file(script))
    print_mpy(mpy)


def _run(args):
    """pybricksdev run"""
    parser = argparse.ArgumentParser(
        prog='pybricksdev run',
        description='Run a Pybricks program.',
    )
    # The argument is a filename or a Python one-liner.
    parser.add_argument('device')
    parser.add_argument('script')
    args = parser.parse_args(args)

    # If the user does not provide a file, assume they provide Python code.
    if not path.exists(args.script):
        script = save_script(args.script)
    else:
        script = args.script

    async def _main(script):

        # Check device argument
        if validators.ip_address.ipv4(args.device):
            # If the device is an IP adress, it's an EV3 Brick with ev3dev.
            hub = EV3Connection()
            address = args.device
        else:
            # Otherwise it is a Pybricks Hub with device name or address given.
            hub = PUPConnection()
            if validators.mac_address(args.device):
                address = args.device
            else:
                address = await find_device(args.device, timeout=5)

        # Connect to the address and run the script
        await hub.connect(address)
        await hub.run(script)
        await hub.disconnect()

    asyncio.run(_main(script))


def _flash(args):
    print("I'm the flash tool")


def entry():
    """Main entry point to the pybricksdev command line utility."""

    # Provide main description and help.
    parser = argparse.ArgumentParser(
        prog='pybricksdev',
        description='Utilities for Pybricks developers.'
    )

    # The first argument is which tool we run.
    parser.add_argument('tool', choices=['run', 'compile', 'flash'])

    # All remaining arguments get passed to the respective tool.
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    # Run the respective tool with those remaining arguments
    if args.tool == 'compile':
        _compile(args.arguments)
    elif args.tool == 'run':
        _run(args.arguments)
    elif args.tool == 'flash':
        _flash(args.arguments)
