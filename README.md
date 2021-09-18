[![Coverage Status](https://coveralls.io/repos/github/pybricks/pybricksdev/badge.svg?branch=master)](https://coveralls.io/github/pybricks/pybricksdev?branch=master) [![Documentation Status](https://readthedocs.org/projects/pybricksdev/badge/?version=latest)](https://docs.pybricks.com/projects/pybricksdev/en/latest/?badge=latest)

# Pybricks tools & interface library

This is a package with tools for Pybricks developers. For regular users we
recommend the [Pybricks Code][code] web IDE.

This package contains both command line tools and a library to call equivalent
operations from within a Python script.

[code]: https://www.code.pybricks.com

## Installation

### Python Runtime

`pybricksdev` requires Python 3.8 or higher.

- For Windows, use the [official Python installer][py-dl] or the [Windows Store][py38-win].
- For Mac, use the [official Python installer][py-dl] or Homebrew (`brew install python@3.8`).
- For Linux, use the distro provided `python3.8` or if not available, use a Python
  runtime version manager such as [asdf][asdf] or [pyenv][pyenv].


[py-dl]: https://www.python.org/downloads/
[py38-win]: https://www.microsoft.com/en-us/p/python-38/9mssztt1n39l
[asdf]: https://asdf-vm.com
[pyenv]: https://github.com/pyenv/pyenv

### Command Line Tool

We recommend using [pipx] to install `pybricksdev` as a command line tool.

We also highly recommend installing `pipx` using a package manager such as `apt`,
`brew`, etc. as suggested in the official [pipx installation] instructions.

And don't forget to run `pipx ensurepath` after the initial installation.
This will make it so that tools installed with `pipx` are in your `PATH`.
You will need to restart any terminal windows for this to take effect. If that
doesn't work, try logging out and logging back in.

Then use `pipx` to install `pybricksdev`:

    # POSIX shell (Linux, macOS, Cygwin, etc)
    PIPX_DEFAULT_PYTHON=python3.8 pipx install pybricksdev

Setting the `PIPX_DEFAULT_PYTHON` environment variable is only needed when
`pipx` uses a different Python runtime other that Python 3.8. This may be the
case if your package manager uses a different Python runtime.

[pipx]: https://pipxproject.github.io/pipx/
[pipx installation]: https://pipxproject.github.io/pipx/installation/

#### Windows users

If you are using the *Python Launcher for Windows* (installed by default with
the official Python installer), then you will need to use `py -3.8` instead
of `python3.8`.

    py -3.8 -m pip install --upgrade pip # ensure pip is up to date first
    py -3.8 -m pip install pipx
    py -3.8 -m pipx ensurepath
    py -3.8 -m pipx install pybricksdev

#### Linux USB

On Linux, `udev` rules are needed to allow access via USB. The `pybricksdev`
command line tool contains a function to generate the required rules. Run the
following:

    pybricksdev udev | sudo tee /etc/udev/rules.d/99-pybricksdev.rules

### Library

To install `pybricksdev` as a library, we highly recommend using a virtual
environment for your project. Our tool of choice for this is [poetry][poetry]:

    poetry env use python3.8
    poetry add pybricksdev

Of course you can always use `pip` as well:

    pip install pybricksdev --pre


[poetry]: https://python-poetry.org


## Using the Command Line Tool

The following are some examples of how to use the `pybricksdev` command line tool.
For additional info, run `pybricksdev --help`.

### Flashing Pybricks MicroPython firmware

Make sure the hub is off. Press and keep holding the hub button, and run:

    pybricksdev flash <firmware.zip>

Replace `<firmware.zip>` with the actual path to the firmware archive.

You may release the button once the progress bar first appears. 

The SPIKE Prime Hub and MINDSTORMS Robot Inventor Hub do not have a Bluetooth
bootloader. It is recommended to [install Pybricks using a Python script][issue-167] that
runs on the hub. You can also flash the firmware manually using [DFU](dfu).


[dfu]: ./README_dfu.rst
[issue-167]: https://github.com/pybricks/support/issues/167


### Running Pybricks MicroPython programs

This compiles a MicroPython script and sends it to a hub with Pybricks
firmware.

    pybricksdev run --help

    #
    # ble connection examples:
    #

    # Run a one-liner on a Pybricks hub
    pybricksdev run ble "print('Hello!'); print('world!');"

    # Run script on the first device we find called Pybricks hub
    pybricksdev run ble --name "Pybricks Hub" demo/shortdemo.py

    # Run script on device with address 90:84:2B:4A:2B:75 (doesn't work on Mac)
    pybricksdev run ble --name 90:84:2B:4A:2B:75 demo/shortdemo.py

    #
    # Other connection examples:
    #

    # Run script on ev3dev at 192.168.0.102
    pybricksdev run ssh --name 192.168.0.102 demo/shortdemo.py

    # Run script on primehub at
    pybricksdev run usb --name "Pybricks Hub" demo/shortdemo.py


### Compiling Pybricks MicroPython programs without running

This can be used to compile programs. Instead of also running them as above,
it just prints the output on the screen instead.

    pybricksdev compile demo/shortdemo.py

    pybricksdev compile "print('Hello!'); print('world!');"


This is mainly intended for developers who want to quickly inspect the
contents of the `.mpy` file. To get the actual file, just use `mpy-cross`
directly. We have used this tool in the past to test bare minimum MicroPython
ports that have neither a builtin compiler or any form of I/O yet. You can
paste the generated `const uint8_t script[]` directly ito your C code.

## Additional Documentation

https://docs.pybricks.com/projects/pybricksdev (work in progress)
