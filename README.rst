Pybricks tools
-----------------

This is a package with tools for Pybricks developers. For regular users we
recommend the `Pybricks Code`_ web IDE.

These developer tools can be used to install Pybricks firmware on a hub,
and run Pybricks MicroPython programs on them.

Installation
-----------------

Requirements:

- pyenv: Used to locally install another version of Python without touching
  your system Python.
- poetry: Used to download and install all Python dependencies with the right
  versions.
- For now, this package has only been tested on Ubuntu 18.04 and Ubuntu 20.04.
  However, we have mostly selected cross-platform dependencies.

Installation steps:

::

    git clone https://github.com/pybricks/pybricks-tools.git
    cd pybricks-tools
    pyenv install 3.8.2 # You can skip this if you already have Python >=3.8.2
    poetry install


Flashing Pybricks MicroPython firmware
---------------------------------------


Running Pybricks MicroPython programs
---------------------------------------

This compiles a MicroPython script and sends it to a hub with Pybricks firmware
over Bluetooth Low Energy. It will attempt to send the program to the first
device named `Pybricks Hub` that it finds.

::

    poetry shell

    python -m pybricks_tools.run --help

    # Run a oneliner on a Pybricks hub
    python -m pybricks_tools.run --string 'print("Hello!"); print("world!");'

    # Run hello.py on a Pybricks hub
    python -m pybricks_tools.run --file demo/hello.py

    # Run hello.py on a Pybricks hub with a custom-built local mpy_cross binary
    python -m pybricks_tools.run --file demo/hello.py --mpy_cross /path/to/mpy-cross

Compiling Pybricks MicroPython programs without running
--------------------------------------------------------

This can be used to compile programs. Instead of also running them as above,
it prints the output on the screen instead.

This is mainly intended for developers who want to quickly inspect the
contents of the ``.mpy`` file. To get the actual file, just use ``mpy-cross``
directly. We have used this tool in the past to test bare minimum MicroPython
ports that have neither a builtin compiler or any form of I/O yet. You can
paste the generated ``const uint8_t script[]`` directly ito your C code.

::

    poetry shell

    python -m pybricks_tools.compile --help

You can use the same example arguments for ``--file``, ``--string``, and
``--mpy_cross`` as above.

.. _Pybricks Code: https://www.code.pybricks.com/
