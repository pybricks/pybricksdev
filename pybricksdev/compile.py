# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2023 The Pybricks Authors

import asyncio
import logging
import os
from modulefinder import ModuleFinder
from typing import List, Optional, Tuple, Union

import mpy_cross_v5
import mpy_cross_v6

from pybricksdev.tools import chunk

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


async def compile_file(
    proj_dir: str, proj_path: str, abi: int, compile_args: Optional[List[str]] = None
):
    """Compiles a Python file with ``mpy-cross``.

    Arguments:
        proj_dir:
            Path to project containing the script to be compiled
        proj_path:
            Path to script that is to be compiled relative to proj_dir. This is
            the portion of the name that is passed to ``mpy-cross``.
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
    with open(os.path.join(proj_dir, proj_path), "r") as f:
        loop = asyncio.get_running_loop()
        script = f.read()

        if abi == 5:
            proc, mpy = await loop.run_in_executor(
                None,
                lambda: mpy_cross_v5.mpy_cross_compile(
                    proj_path, script, no_unicode=True, extra_args=compile_args
                ),
            )
        elif abi == 6:
            proc, mpy = await loop.run_in_executor(
                None,
                lambda: mpy_cross_v6.mpy_cross_compile(
                    proj_path, script, extra_args=compile_args
                ),
            )
        else:
            raise ValueError("mpy_version must be 5 or 6")

        proc.check_returncode()

        return mpy


async def compile_multi_file(path: str, abi: Union[int, Tuple[int, int]]):
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
            Expected MPY ABI version. Can be major version (int) if no native
            .mpy modules or tuple of major, minor version.

    Returns:
        Concatenation of all compiled files in the format given above.

    Raises:
        RuntimeError: if there is not a running event loop.
        ValueError if MPY ABI version is not 5 or 6.
        subprocess.CalledProcessError: if executing the ``mpy-cross` tool failed.
    """

    # compile files using Python to find imports contained within the same directory as path
    proj_path = os.path.dirname(path)
    search_path = [proj_path]
    finder = ModuleFinder(search_path)

    try:
        finder.run_script(path)
    except AttributeError as e:
        raise RuntimeError(
            "ModuleFinder doesn't currently handle implicit namespace packages. Did you forget to put an __init__.py file in one of your subdirectories? See https://github.com/pybricks/support/issues/1602"
        ) from e

    # we expect missing modules, namely builtin MicroPython packages like pybricks.*
    logger.debug("missing modules: %r", finder.any_missing())

    # Get a data blob with all scripts.
    parts: List[bytes] = []

    abi_major, abi_minor = (abi, None) if isinstance(abi, int) else abi

    for name, module in finder.modules.items():
        if not module.__file__:
            continue

        mpy = await compile_file(
            proj_path, os.path.relpath(module.__file__, proj_path), abi_major
        )

        parts.append(len(mpy).to_bytes(4, "little"))
        parts.append(name.encode() + b"\x00")
        parts.append(mpy)

    # look for .mpy modules
    for name in finder.any_missing():
        for spath in search_path:
            try:
                with open(os.path.join(spath, f"{name}.mpy"), "rb") as f:
                    mpy = f.read()
                if mpy[1] != abi_major:
                    raise ValueError(
                        f"{name}.mpy has abi major version {mpy[1]} while {abi_major} is required"
                    )
                if (
                    abi_minor is not None  # hub indicated a minor version
                    and (mpy[2] >> 2)  # mpy has native arch
                    # TODO: How to validate native arch? For now just gets runtime error on hub.
                    and (mpy[2] & 0x3)
                    != abi_minor  # mpy minor version does not match hub minor version
                ):
                    raise ValueError(
                        f"{name}.mpy has abi minor version {mpy[2] & 0x3} while {abi_minor} is required"
                    )
                parts.append(len(mpy).to_bytes(4, "little"))
                parts.append(name.encode() + b"\x00")
                parts.append(mpy)
            except OSError:
                continue

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
    print(f"// MPY file. Size: {len(data)} bytes")
    print("const uint8_t script[] = {")

    for c in chunk(data, WIDTH):
        hex_repr = [f"0x{i:02X}" for i in c]
        print(f"    {', '.join(hex_repr)},")

    print("};")
