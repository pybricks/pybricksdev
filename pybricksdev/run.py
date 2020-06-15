# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import asyncio

from pybricksdev.compile import (
    compile_argparser,
    save_script
)
from pybricksdev.connections import PUPConnection
from pybricksdev.ble import find_device
import logging


if __name__ == "__main__":
    # Add arguments to the base parser, then parse
    parser = compile_argparser
    parser.description = (
        "Run Pybricks MicroPython scripts via BLE."
    )
    args = parser.parse_args()

    # Get file path
    path = save_script(args.string) if args.file is None else args.file

    async def main():

        print("Scanning for Pybricks Hub")
        address = await find_device('Pybricks Hub', timeout=5)
        print("Found {0}!".format(address))

        hub = PUPConnection()
        hub.logger.setLevel(logging.DEBUG)
        await hub.connect(address)
        await hub.run(path, args.mpy_cross)
        await hub.disconnect()

    # Asynchronously send and run the script
    asyncio.run(main())
