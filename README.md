[![Coverage Status](https://coveralls.io/repos/github/pybricks/pybricksdev/badge.svg?branch=master)](https://coveralls.io/github/pybricks/pybricksdev?branch=master) [![Documentation Status](https://readthedocs.org/projects/pybricksdev/badge/?version=latest)](https://docs.pybricks.com/projects/pybricksdev/en/latest/?badge=latest)

# Pybricks tools & interface library

This is a package with tools for Pybricks developers. For regular users we
recommend the [Pybricks Code][code] web IDE.

This package contains both command line tools and a library to call equivalent
operations from within a Python script.

[code]: https://www.code.pybricks.com

## Installation

### Python Runtime

`pybricksdev` requires Python 3.10 or higher.

- For Windows, use the [official Python installer][py-dl] or the [Windows Store][py38-win].
- For Mac, use the [official Python installer][py-dl] or Homebrew (`brew install python@3.12`).
- For Linux, use the distro provided `python3.12` or if not available, use a Python
  runtime version manager such as [asdf][asdf] or [pyenv][pyenv].


[py-dl]: https://www.python.org/downloads/
[py38-win]: https://www.microsoft.com/en-us/p/python-38/9mssztt1n39l
[asdf]: https://asdf-vm.com
[pyenv]: https://github.com/pyenv/pyenv

### Command Line Tool

We recommend using [pipx] to run `pybricksdev` as a command line tool. This
ensures that you are always running the latest version of `pybricksdev`.

We also highly recommend installing `pipx` using a package manager such as `apt`,
`brew`, etc. as suggested in the official [pipx installation] instructions.

Then use `pipx` to run `pybricksdev`:

    pipx run pybricksdev ...

[pipx]: https://pipxproject.github.io/pipx/
[pipx installation]: https://pipxproject.github.io/pipx/installation/


If you don't like typing `pipx run ...` all of the time, you can install
`pybrickdev` with:

    pipx install pybricksdev

Then you can just type:

    pybricksdev run ...

And check for updates with:

    pipx upgrade pybricksdev

#### Windows users

If you are using the *Python Launcher for Windows* (installed by default with
the official Python installer), then you will need to use `py -3` instead
of `python3`.

    py -3 -m pip install --upgrade pip # ensure pip is up to date first
    py -3 -m pip install pipx
    py -3 -m pipx run pybricksdev ...

#### Linux USB

On Linux, `udev` rules are needed to allow access via USB. The `pybricksdev`
command line tool contains a function to generate the required rules. Run the
following:

    pipx run pybricksdev udev | sudo tee /etc/udev/rules.d/99-pybricksdev.rules

### Library

To install `pybricksdev` as a library, we highly recommend using a virtual
environment for your project. Our tool of choice for this is [poetry]:

    poetry env use python3.12
    poetry add pybricksdev

Of course you can always use `pip` as well:

    pip install pybricksdev --pre


[poetry]: https://python-poetry.org


## Using the Command Line Tool

The following are some examples of how to use the `pybricksdev` command line tool.
For additional info, run `pybricksdev --help`.

### Flashing Pybricks MicroPython firmware

Turn on the hub, and run:

    pipx run pybricksdev flash <firmware.zip>

Replace `<firmware.zip>` with the actual path to the firmware archive.

### Running Pybricks MicroPython programs

This compiles a MicroPython script and sends it to a hub with Pybricks
firmware.

    pipx run pybricksdev run --help

    #
    # ble connection examples:
    #
    
    # Run script on any Pybricks device
    pipx run pybricksdev run ble demo/shortdemo.py

    # Run script on the first device we find called Pybricks hub
    pipx run pybricksdev run ble --name "Pybricks Hub" demo/shortdemo.py

    # Run script on device with address 90:84:2B:4A:2B:75 (doesn't work on Mac)
    pipx run pybricksdev run ble --name 90:84:2B:4A:2B:75 demo/shortdemo.py
           
    #
    # usb connection examples:
    # NOTE: running programs via usb connection works for official LEGO firmwares only

    # Run script on any Pybricks device
    pipx run pybricksdev run usb demo/shortdemo.py

    #
    # Other connection examples:
    #

    # Run script on ev3dev at 192.168.0.102
    pipx run pybricksdev run ssh --name 192.168.0.102 demo/shortdemo.py


### Compiling Pybricks MicroPython programs without running

This can be used to compile programs. Instead of also running them as above,
it just prints the output on the screen instead.

    pipx run pybricksdev compile demo/shortdemo.py

    pipx run pybricksdev compile "print('Hello!'); print('world!');"


This is mainly intended for developers who want to quickly inspect the
contents of the `.mpy` file. To get the actual file, just use `mpy-cross`
directly. We have used this tool in the past to test bare minimum MicroPython
ports that have neither a builtin compiler or any form of I/O yet. You can
paste the generated `const uint8_t script[]` directly ito your C code.

## Additional Documentation

https://docs.pybricks.com/projects/pybricksdev (work in progress)
