# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2022 The Pybricks Authors

import asyncio
import logging
import os
from modulefinder import ModuleFinder
from typing import List, Optional

import mpy_cross_v5
import mpy_cross_v6

from .tools import chunk

logger = logging.getLogger(__name__)

BUILD_DIR = "build"
TMP_PY_SCRIPT = "_tmp.py"
TMP_MPY_SCRIPT = "_tmp.mpy"


def make_build_dir():
    # Create build folder if it does not exist
    if not os.path.exists(BUILD_DIR):
        os.mkdir(BUILD_DIR)

    # Raise error if there happens to be a file by this name
    if os.path.isfile(BUILD_DIR):
        raise FileExistsError("A file named build already exists.")


async def compile_file(path: str, abi: int, compile_args: Optional[List[str]] = None):
    """Compiles a Python file with ``mpy-cross``.

    Arguments:
        path:
            Path to script that is to be compiled.
        abi:
            Expected MPY ABI version.
        compile_args:
            Extra arguments for ``mpy-cross``.

    Returns:
        The compiled script in MPY format.

    Raises:
        RuntimeError: if there is not a running event loop.
        ValueError if MPY ABI version is not 5 or 6.
        subprocess.CalledProcessError: if executing the ``mpy-cross` tool failed.
    """

    # Get version info
    with open(path, "r") as f:
        loop = asyncio.get_running_loop()
        script = f.read()

        if abi == 5:
            proc, mpy = await loop.run_in_executor(
                None,
                lambda: mpy_cross_v5.mpy_cross_compile(
                    path, script, no_unicode=True, extra_args=compile_args
                ),
            )
        elif abi == 6:
            proc, mpy = await loop.run_in_executor(
                None,
                lambda: mpy_cross_v6.mpy_cross_compile(
                    path, script, extra_args=compile_args
                ),
            )
        else:
            raise ValueError("mpy_version must be 5")

        proc.check_returncode()

        return mpy


async def compile_multi_file(path: str, abi: int):
    """Compiles a Python file and its dependencies with ``mpy-cross``.

    On the hub, all dependencies behave as independent modules. Any (leading)
    dots will be considered to be part of the module name. As such, relative
    or "package" imports will work, but there is no handling of __init__, etc.

    The returned bytes format is of the form:

       - first script size (uint32 little endian)
       - first script name (no extension, zero terminated string)
       - first script mpy data
       - second script size
       - second script name
       - second script mpy data
       - ...

    If the main script does not import any local module, it returns only the
    first script mpy data (without size and name) for backwards compatibility
    with older firmware.

    Arguments:
        path:
            Path to script that is to be compiled.
        abi:
            Expected MPY ABI version.

    Returns:
        Concatenation of all compiled files in the format given above.

    Raises:
        RuntimeError: if there is not a running event loop.
        ValueError if MPY ABI version is not 5 or 6.
        subprocess.CalledProcessError: if executing the ``mpy-cross` tool failed.
    """

    # compile files using Python to find imports contained within the same directory as path
    finder = ModuleFinder([os.path.dirname(path)])
    finder.run_script(path)

    # we expect missing modules, namely builtin MicroPython packages like pybricks.*
    logger.debug("missing modules: %r", finder.any_missing())

    # Get a data blob with all scripts.
    parts: List[bytes] = []

    for name, module in finder.modules.items():
        mpy = await compile_file(module.__file__, abi)

        parts.append(len(mpy).to_bytes(4, "little"))
        parts.append(name.encode() + b"\x00")
        parts.append(mpy)

    return b"".join(parts)


def save_script(py_string):
    """Save a MicroPython one-liner to a file."""
    # Make the build directory.
    make_build_dir()

    # Path to temporary file.
    py_path = os.path.join(BUILD_DIR, TMP_PY_SCRIPT)

    # Write Python command to a file.
    with open(py_path, "w") as f:
        f.write(py_string)
        f.write("\n")

    # Return path to file
    return py_path


def print_mpy(data):
    # Print as string as a sanity check.
    print()
    print("Bytes:")
    print(data)

    # Print the bytes as a C byte array for development of new MicroPython
    # ports without usable I/O, REPL or otherwise.
    WIDTH = 8
    print()
    print(f"// MPY file. Version: {data[1]}. Size: {len(data)} bytes")
    print("const uint8_t script[] = {")

    for c in chunk(data, WIDTH):
        hex_repr = [f"0x{i:02X}" for i in c]
        print(f"    {', '.join(hex_repr)},")

    print("};")
