# SPDX-License-Identifier: MIT
# Copyright (c) 2019-2020 The Pybricks Authors

import os
import argparse
import subprocess
from pathlib import Path
import mpy_cross
import asyncio

BUILD_DIR = "build"
TMP_PY_SCRIPT = "_tmp.py"
TMP_MPY_SCRIPT = "_tmp.mpy"


def make_build_dir():
    # Create build folder if it does not exist
    if not os.path.exists(BUILD_DIR):
        os.mkdir(BUILD_DIR)

    # Raise error if there happens to be a file by this name
    if os.path.isfile(BUILD_DIR):
        raise OSError("A file named build already exists.")


async def run_mpy_cross(args, mpy_cross_path=None):
    """Runs mpy-cross asynchronously with given arguments.

    Arguments:
        args:
            Arguments to pass to mpy-cross.
        mpy_cross_path (str or None):
            Path to mpy-cross. Choose None to use default from package.

    Returns:
        str: stdout.

    Raises:
        OSError with stderr if mpy-cross fails.

    """

    # If no path to mpy-cross is given, use packaged version
    if mpy_cross_path is None:
        mpy_cross_path = mpy_cross.mpy_cross

    # Run the process asynchronously
    proc = await asyncio.create_subprocess_exec(
        mpy_cross_path, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    # Check the output for compile errors such as syntax errors
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ValueError(stderr.decode())

    # On success, return stdout
    return stdout.decode()


async def compile_file(py_path, mpy_cross_path=None):
    """Compiles a Python file with mpy-cross and return as bytes.

    Arguments:
        py_path (str):
            Path to script that is to be compiled.
        mpy_cross_path (str):
            Path to mpy-cross. Choose None to use default from package.

    Returns:
        str: stdout.

    Raises:
        OSError with stderr if mpy-cross fails.
    """

    # Get version info
    print(await run_mpy_cross(["--version"], mpy_cross_path))

    # Make the build directory
    make_build_dir()

    # Cross-compile Python file to .mpy and raise errors if any
    mpy_path = os.path.join(BUILD_DIR, Path(py_path).stem + ".mpy")
    await run_mpy_cross(
        [py_path, "-mno-unicode", "-o", mpy_path], mpy_cross_path
    )

    # Read the .mpy file and return as bytes
    with open(mpy_path, "rb") as mpy:
        return mpy.read()


def save_script(py_string):
    """Save a MicroPython one-liner to a file."""
    # Make the build directory.
    make_build_dir()

    # Path to temporary file.
    py_path = os.path.join(BUILD_DIR, TMP_PY_SCRIPT)

    # Write Python command to a file.
    with open(py_path, "w") as f:
        f.write(py_string + "\n")

    # Return path to file
    return py_path


# Base arg parser shared by all tools that have to compile Pybricks scripts
# to bytes one way or another
compile_argparser = argparse.ArgumentParser()
group = compile_argparser.add_mutually_exclusive_group(required=True)
group.add_argument("--file", dest="file", nargs="?", const=1, type=str)
group.add_argument("--string", dest="string", nargs="?", const=1, type=str)
compile_argparser.add_argument(
    "--mpy_cross", dest="mpy_cross", nargs="?", type=str, required=False
)


if __name__ == "__main__":

    # Get base parser, then parse
    parser = compile_argparser
    parser.description = (
        "Convert MicroPython scripts or commands to .mpy bytes."
    )
    args = parser.parse_args()

    # Get file path
    path = save_script(args.string) if args.file is None else args.file

    # Convert to bytes
    data = compile_file(path, args.mpy_cross)

    # Print as string as a sanity check.
    print("\nBytes:")
    print(data)

    # Print the bytes as a C byte array for development of new MicroPython
    # ports without usable I/O, REPL or otherwise.
    WIDTH = 8
    print(
        "\n// MPY file. Version: {0}. Size: {1}".format(data[1], len(data))
        + "\nconst uint8_t script[] = "
    )
    for i in range(0, len(data), WIDTH):
        chunk = data[i:i + WIDTH]
        hex_repr = ["0x{0}".format(hex(i)[2:].zfill(2).upper()) for i in chunk]
        print("    " + ", ".join(hex_repr) + ",")
    print("};")
