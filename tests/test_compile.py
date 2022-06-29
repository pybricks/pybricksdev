# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors


import os
import struct
from tempfile import NamedTemporaryFile

import pytest
from pybricksdev.compile import compile_file


@pytest.mark.asyncio
async def test_compile_file():
    with NamedTemporaryFile("w", delete=False) as f:
        try:
            f.write("print('test')")
            f.close()

            mpy = await compile_file(f.name, abi=5)

            magic, abi_ver, flags, int_bits = struct.unpack_from("<BBBB", mpy)

            assert chr(magic) == "M"
            assert abi_ver == 5
            assert flags == 0
            assert int_bits == 31
        finally:
            os.unlink(f.name)
