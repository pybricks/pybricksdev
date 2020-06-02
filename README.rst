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

::

    poetry shell

    python -m pybricks_tools.ble --file demo/hello.py

    python -m pybricks_tools.ble --string 'print("Hello!"); wait(1000); print("world!");'
