# SPDX-License-Identifier: MIT
# Copyright (c) 2022-2026 The Pybricks Authors


import contextlib
import os
import struct
import sys
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from pybricksdev.compile import compile_file, compile_multi_file

# TODO: Remove this when we drop support for Python 3.10.
if sys.version_info < (3, 11):
    from contextlib import AbstractContextManager

    class chdir(AbstractContextManager[None]):
        """Non thread-safe context manager to change the current working directory."""

        def __init__(self, path: str) -> None:
            self.path = path
            self._old_cwd: list[str] = []

        def __enter__(self) -> None:
            self._old_cwd.append(os.getcwd())
            os.chdir(self.path)

        def __exit__(self, *excinfo: Any) -> None:
            os.chdir(self._old_cwd.pop())

    setattr(contextlib, "chdir", chdir)


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
                    "from test4 import thing4\n",
                    "from nested.test5 import thing5\n",
                ]
            )

        with open(os.path.join(temp_dir, "test1.py"), "w", encoding="utf-8") as f1:
            f1.write("thing1 = 'thing1'\n")

        with open(os.path.join(temp_dir, "test2.py"), "w", encoding="utf-8") as f2:
            f2.write("thing2 = 'thing2'\n")

        os.mkdir("nested")

        # We didn't implement a better way for older ABI yet.
        uses_module_finder = abi == 5

        # Work around bug where ModuleFinder can't handle implicit namespace
        # packages by adding an __init__.py file.
        if uses_module_finder:
            with open(
                os.path.join(temp_dir, "nested", "__init__.py"), "w", encoding="utf-8"
            ) as init:
                init.write("")

        with open(
            os.path.join(temp_dir, "nested", "test3.py"), "w", encoding="utf-8"
        ) as f3:
            f3.write("thing3 = 'thing3'\n")

        # test4 and test5 are to test package modules with non-empty __init__.py

        os.mkdir("test4")

        with open(
            os.path.join(temp_dir, "test4", "__init__.py"), "w", encoding="utf-8"
        ) as f4:
            f4.write("thing4 = 'thing4'\n")

        os.mkdir(os.path.join("nested", "test5"))

        with open(
            os.path.join(temp_dir, "nested", "test5", "__init__.py"),
            "w",
            encoding="utf-8",
        ) as f5:
            f5.write("thing5 = 'thing5'\n")

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

        names = set[str]()

        name1, mpy1 = unpack_mpy(multi_mpy)
        name2, mpy2 = unpack_mpy(multi_mpy)
        names.add(name2.decode())
        name3, mpy3 = unpack_mpy(multi_mpy)
        names.add(name3.decode())

        if uses_module_finder:
            # ModuleFinder requires __init__.py.
            name4, mpy4 = unpack_mpy(multi_mpy)
            names.add(name4.decode())

        name5, mpy5 = unpack_mpy(multi_mpy)
        names.add(name5.decode())

        name6, mpy6 = unpack_mpy(multi_mpy)
        names.add(name6.decode())

        name7, mpy7 = unpack_mpy(multi_mpy)
        names.add(name7.decode())

        assert pos == len(multi_mpy)

        # It is important that the main module is first.
        assert name1.decode() == "__main__"

        # The other modules can be in any order.
        assert "test1" in names
        assert "test2" in names
        if uses_module_finder:
            assert "nested" in names
        assert "nested.test3" in names

        if uses_module_finder:
            assert len(names) == 6
        else:
            assert len(names) == 5

        def check_mpy(mpy: bytes) -> None:
            magic, abi_ver, flags, int_bits = struct.unpack_from("<BBBB", mpy)

            assert chr(magic) == "M"
            assert abi_ver == abi
            assert flags == 0
            assert int_bits == 31

        check_mpy(mpy1)
        check_mpy(mpy2)
        check_mpy(mpy3)
        if uses_module_finder:
            check_mpy(mpy4)  # pyright: ignore[reportPossiblyUnboundVariable]
        check_mpy(mpy5)
        check_mpy(mpy6)
        check_mpy(mpy7)
