# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import asyncio
import logging
import os
import re

from pathlib import Path
from subprocess import Popen, PIPE

import mpy_cross

from ._mpy_tool import merge_mpy, read_mpy, config

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


async def run_mpy_cross(args):
    """Runs mpy-cross asynchronously with given arguments.

    Arguments:
        args:
            Arguments to pass to mpy-cross.

    Returns:
        str: stdout.

    Raises:
        RuntimeError with stderr if mpy-cross fails.

    """

    # Run the process asynchronously
    try:
        proc = await asyncio.create_subprocess_exec(
            mpy_cross.mpy_cross, *args, stdout=PIPE, stderr=PIPE
        )

        # Check the output for compile errors such as syntax errors
        stdout, stderr = await proc.communicate()
    except NotImplementedError:
        # This error happens when running on Windows with WindowsSelectorEventLoopPolicy()
        # which is the required policy for ipython kernels due to a requirement
        # by the tornado package. So in that case, we call the subprocess synchronously
        # which shouldn't be a big deal for running in notebooks. Python versions
        # before 3.8 also used WindowsSelectorEventLoopPolicy() by default, but
        # pybricksdev requires at least Python 3.8, so that shouldn't be a problem.
        logger.debug("calling mpy-cross synchronously")
        proc = Popen([mpy_cross.mpy_cross, *args], stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    # On success, return stdout
    return stdout.decode()


async def compile_file(path, compile_args=["-mno-unicode"], mpy_version=5):
    """Compiles a Python file with mpy-cross and return as bytes.

    Arguments:
        path (str):
            Path to script that is to be compiled.
        compile_args (dict):
            Extra arguments for mpy-cross.
        mpy_version (int):
            Expected mpy ABI version.

    Returns:
        bytes: compiled script in mpy format.

    Raises:
        RuntimeError with stderr if mpy-cross fails.
        ValueError if mpy-cross ABI version does not match packaged version.
    """

    # Get version info
    out = await run_mpy_cross(["--version"])
    installed_mpy_version = int(out.strip()[-1])
    if installed_mpy_version != mpy_version:
        raise ValueError(
            "Expected mpy-cross ABI v{0} but v{1} is installed.".format(
                mpy_version, installed_mpy_version
            )
        )

    # Make the build directory
    make_build_dir()

    # Location of script after parsing
    source_dir = Path(path).parent
    build_dir = Path(BUILD_DIR)
    parsed_path = build_dir / Path(path).name

    # Parse input file to detect matching import statements
    imported_modules = []
    with open(Path(path)) as source, open(parsed_path, "w") as parsed:
        for line in source:

            # Scan for imports
            module_found = None
            if result := re.search("from (.*) import (.*)", line):
                module = result.group(1)
                if module != "pybricks" and not module.startswith("pybricks."):
                    module_found = module

            # Handle detected import.
            if module_found:
                # Replace with empty line to preserve line numbers.
                imported_modules.append(module_found)
                parsed.write("\n")
            else:
                # Don't modify other lines.
                parsed.write(line)

    # Cross-compile dependencies to .mpy and raise errors.
    mpy_paths = []
    for module in imported_modules:
        py_path = source_dir / (module + ".py")
        mpy_paths.append(build_dir / (module + ".mpy"))
        await run_mpy_cross([py_path] + compile_args + ["-o", mpy_paths[-1]])

    # Cross-compile main script to .mpy and raise errors if any.
    mpy_paths.append(parsed_path.with_suffix(".mpy"))
    await run_mpy_cross([parsed_path] + compile_args + ["-o", mpy_paths[-1]])

    # TODO: Get this from from mpy-tool.py instead of hard coding.
    config.MICROPY_LONGINT_IMPL = 2
    config.MPZ_DIG_SIZE = 16
    config.native_arch = 0
    config.MICROPY_QSTR_BYTES_IN_LEN = 1
    config.MICROPY_QSTR_BYTES_IN_HASH = 1

    # Use mpy-tool to combine all files, with the main script last.
    merge_mpy([read_mpy(file) for file in mpy_paths], build_dir / "merged.mpy")

    # Read the .mpy file and return as bytes
    with open(build_dir / "merged.mpy", "rb") as mpy:
        return mpy.read()


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
