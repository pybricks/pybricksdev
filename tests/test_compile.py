# SPDX-License-Identifier: MIT
# Copyright (c) 2022 The Pybricks Authors


import contextlib
import os
import struct
from tempfile import TemporaryDirectory

import pytest

from pybricksdev.compile import compile_file, compile_multi_file


@pytest.mark.parametrize("abi", [5, 6])
@pytest.mark.asyncio
async def test_compile_file(abi: int):
    with TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "test.py"), "w", encoding="utf-8") as f:
            f.write("print('test')")

        mpy = await compile_file(
            os.path.dirname(f.name), os.path.basename(f.name), abi=abi
        )

        magic, abi_ver, flags, int_bits = struct.unpack_from("<BBBB", mpy)

        assert chr(magic) == "M"
        assert abi_ver == abi
        assert flags == 0
        assert int_bits == 31


@pytest.mark.asyncio
async def test_compile_file_invalid_abi():
    with TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "test.py"), "w", encoding="utf-8") as f:
            f.write("print('test')")

        with pytest.raises(ValueError, match="mpy_version must be 5 or 6"):
            await compile_file(os.path.dirname(f.name), os.path.basename(f.name), abi=4)


@pytest.mark.parametrize("abi", [5, 6])
@pytest.mark.asyncio
async def test_compile_multi_file(abi: int):
    with TemporaryDirectory() as temp_dir, contextlib.chdir(temp_dir):
        with open(os.path.join(temp_dir, "test.py"), "w", encoding="utf-8") as f:
            f.writelines(
                [
                    "from pybricks import version\n",
                    "import test1\n",
                    "from test2 import thing2\n",
                    "from nested.test3 import thing3\n",
                ]
            )

        with open(os.path.join(temp_dir, "test1.py"), "w", encoding="utf-8") as f1:
            f1.write("thing1 = 'thing1'\n")

        with open(os.path.join(temp_dir, "test2.py"), "w", encoding="utf-8") as f2:
            f2.write("thing2 = 'thing2'\n")

        os.mkdir("nested")

        # Work around bug where ModuleFinder can't handle implicit namespace
        # packages by adding an __init__.py file.
        with open(
            os.path.join(temp_dir, "nested", "__init__.py"), "w", encoding="utf-8"
        ) as init:
            init.write("")

        with open(
            os.path.join(temp_dir, "nested", "test3.py"), "w", encoding="utf-8"
        ) as f3:
            f3.write("thing3 = 'thing3'\n")

        multi_mpy = await compile_multi_file("test.py", abi)
        pos = 0

        def unpack_mpy(data: bytes) -> tuple[bytes, bytes]:
            nonlocal pos

            size = struct.unpack_from("<I", multi_mpy, pos)[0]
            pos += 4

            name = bytearray()

            # read zero-terminated string
            while multi_mpy[pos] != 0:
                name.append(multi_mpy[pos])
                pos += 1

            pos += 1  # skip 0 byte

            mpy = multi_mpy[pos : pos + size]
            pos += size

            return name, mpy

        name1, mpy1 = unpack_mpy(multi_mpy)
        name2, mpy2 = unpack_mpy(multi_mpy)
        name3, mpy3 = unpack_mpy(multi_mpy)
        name4, mpy4 = unpack_mpy(multi_mpy)
        name5, mpy5 = unpack_mpy(multi_mpy)

        assert pos == len(multi_mpy)

        assert name1.decode() == "__main__"
        assert name2.decode() == "test1"
        assert name3.decode() == "test2"
        assert name4.decode() == "nested"
        assert name5.decode() == "nested.test3"

        def check_mpy(mpy: bytes) -> None:
            magic, abi_ver, flags, int_bits = struct.unpack_from("<BBBB", mpy)

            assert chr(magic) == "M"
            assert abi_ver == abi
            assert flags == 0
            assert int_bits == 31

        check_mpy(mpy1)
        check_mpy(mpy2)
        check_mpy(mpy3)
        check_mpy(mpy4)
        check_mpy(mpy5)
