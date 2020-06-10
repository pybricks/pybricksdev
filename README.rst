Pybricks tools
-----------------

Intro

Installation
-----------------

::

    pyenv install 3.8.3
    poetry install


Running Pybricks MicroPython programs
---------------------------------------

This compiles a MicroPython script and sends it to a hub with Pybricks firmware
over Bluetooth Low Energy. It will attempt to send the program to the first
device named `Pybricks Hub` that it finds.

::

    poetry shell

    python -m pybricks_tools.run --help

    # Run hello.py on a Pybricks hub
    python -m pybricks_tools.run --file demo/hello.py

    # Run a oneliner on a Pybricks hub
    python -m pybricks_tools.run --string 'print("Hello!"); print("world!");'

Compiling Pybricks MicroPython programs
---------------------------------------

This can be used to compile programs. Instead of also running them as above,
it prints the output on the screen instead.

This is mainly intended for developers who want to quickly inspect the
contents of the `.mpy` file. To get the actual file, just use `mpy-cross`
directly. We have used this tool in the past to test bare minimum MicroPython
ports that have neither a builtin compiler or any form of I/O yet. You can
paste the generated `const uint8_t script[]` directly ito your C code.

::

    poetry shell

    python -m pybricks_tools.compile --help

You can use the same example arguments for `--file` and `--string` as above.
