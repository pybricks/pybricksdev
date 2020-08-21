Pybricks tools & interface library
-----------------------------------

This is a package with tools for Pybricks developers. For regular users we
recommend the `Pybricks Code`_ web IDE.

This package contains both command line tools and a library to call equivalent
operations from within a Python script.

Installation
-----------------

Requirements:

- pyenv: Used to locally install another version of Python without touching
  your system Python.
- poetry: Used to download and install all Python dependencies with the right
  versions.

Installation steps:

::

    git clone https://github.com/pybricks/pybricksdev.git
    cd pybricksdev
    pyenv install 3.8.2 # You can skip this if you already have Python >=3.8.2
    poetry install


Flashing Pybricks MicroPython firmware (Move Hub, City Hub, Control+ Hub)
--------------------------------------------------------------------------

Make sure the hub is off. Press and keep holding the hub button, and run:

::

    poetry run pybricksdev flash ../pybricks-micropython/bricks/cplushub/build/firmware.zip -d 15

Replace the example path with the path to the firmware archive. Decrease the
delay ``d`` between data packages for faster transfer. Increase the delay if it
fails.

You may release the button once the progress bar first appears. 

Flashing Pybricks MicroPython firmware (SPIKE Prime Hub)
-----------------------------------------------------------------------

TODO: Document ``udev`` rules.

Make sure the hub is off. Press and keep holding the bluetooth button, and
plug in USB. Keep holding the button until the bluetooth light flashes
red/green/blue. Then run this command:

::

    poetry run pybricksdev dfu ../pybricks-micropython/bricks/primehub/build/firmware.zip

Replace the example path with the path to the firmware archive.

*Restoring the original firmware*

The official SPIKE Prime app can only restore the firmware if an official
firmware is already installed. To install an original firmware, use:

::

    poetry run pybricksdev dfu-restore /path/to/original/firmware.bin

GitHub user @gpdaniels has obtained several original firmware versions. You
can use this `firmware file`_ to install version `1.0.06`. After recovering
this firmware, use the official SPIKE app to update to the
very latest firmware. Doing so is recommend, because that will also update
the files on the internal storage to the correct version.

Running Pybricks MicroPython programs
---------------------------------------

This compiles a MicroPython script and sends it to a hub with Pybricks
firmware.

::

    poetry run pybricksdev run --help

    #
    # ble connection examples:
    #

    # Run a one-liner on a Pybricks hub
    poetry run pybricksdev run ble 'Pybricks Hub' 'print("Hello!"); print("world!");'

    # Run script on the first device we find called Pybricks hub
    poetry run pybricksdev run ble 'Pybricks Hub' demo/shortdemo.py

    # Run script on 90:84:2B:4A:2B:75, skipping search
    poetry run pybricksdev run ble 90:84:2B:4A:2B:75 demo/shortdemo.py

    #
    # Other connection examples:
    #

    # Run script on ev3dev at 192.168.0.102
    poetry run pybricksdev run ssh 192.168.0.102 demo/shortdemo.py

    # Run script on primehub at
    poetry run pybricksdev run usb 'Pybricks Hub' demo/shortdemo.py

Compiling Pybricks MicroPython programs without running
--------------------------------------------------------

This can be used to compile programs. Instead of also running them as above,
it just prints the output on the screen instead.

::

    poetry run pybricksdev compile demo/shortdemo.py

    poetry run pybricksdev compile 'print("Hello!"); print("world!");'


This is mainly intended for developers who want to quickly inspect the
contents of the ``.mpy`` file. To get the actual file, just use ``mpy-cross``
directly. We have used this tool in the past to test bare minimum MicroPython
ports that have neither a builtin compiler or any form of I/O yet. You can
paste the generated ``const uint8_t script[]`` directly ito your C code.


.. _Pybricks Code: https://www.code.pybricks.com/
.. _firmware file: https://github.com/gpdaniels/spike-prime/blob/master/firmware/v1.0.06.0034-b0c335b/96112deb24a934bfc19a13c7ea620f54.bin?raw=true
