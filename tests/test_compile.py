# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors


import os
import struct
from tempfile import NamedTemporaryFile

import pytest

from pybricksdev.compile import compile_file


@pytest.mark.parametrize("abi", [5, 6])
@pytest.mark.asyncio
async def test_compile_file(abi: int):
    with NamedTemporaryFile("w", delete=False) as f:
        try:
            f.write("print('test')")
            f.close()

            mpy = await compile_file(
                os.path.dirname(f.name), os.path.basename(f.name), abi=abi
            )

            magic, abi_ver, flags, int_bits = struct.unpack_from("<BBBB", mpy)

            assert chr(magic) == "M"
            assert abi_ver == abi
            assert flags == 0
            assert int_bits == 31
        finally:
            os.unlink(f.name)
