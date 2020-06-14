# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import asyncio

from pybricksdev.compile import (
    compile_argparser,
    compile_file,
    compile_str
)
from pybricksdev.connections import find_ble_device, PUPConnection




if __name__ == "__main__":
    # Add arguments to the base parser, then parse
    parser = compile_argparser
    parser.description = (
        "Run Pybricks MicroPython scripts via BLE."
    )
    args = parser.parse_args()

    # Convert either the file or the string to mpy format
    if args.file is not None:
        data = compile_file(args.file, args.mpy_cross)
    else:
        data = compile_str(args.string, args.mpy_cross)

    async def main(mpy):

        print("Scanning for Pybricks Hub")
        address = await find_ble_device('Pybricks Hub', timeout=5)
        print("Found {0}!".format(address))

        hub = PUPConnection(debug=False)
        await hub.connect(address)
        await hub.download_and_run(mpy)
        await hub.disconnect()

    # Asynchronously send and run the script
    asyncio.run(main(data))
