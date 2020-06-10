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

    python -m pybricks_tools.run --help

    # Run hello.py on a Pybricks hub
    python -m pybricks_tools.run --file demo/hello.py

    # Run a oneliner on a Pybricks hub
    python -m pybricks_tools.run --string 'print("Hello!"); print("world!");'
