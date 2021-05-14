Flashing Pybricks MicroPython firmware (SPIKE Prime Hub)
-----------------------------------------------------------------------

The SPIKE Prime bootloader works a bit differently than other hubs. It uses USB
instead of Bluetooth Low Energy. More specifically, it uses a variant of the
MicroPython ``mboot`` bootloader which uses the `Device Firmware Upgrade (DFU)`_
protocol.

The official SPIKE Prime app doesn't use the DFU bootloader for flashing firmware
so it is not currently possible to restore the LEGO firmware after using Pybricks
using the SPIKE Prime app. It is always possible to restore the firmware using
the DFU bootloader though.

To activate the DFU mode on the SPIKE Prime, unplug the USB cable and make sure
the hub is powered off. Press and keep holding the Bluetooth button, and then
plug in the USB cable. Keep holding the button until the Bluetooth light flashes
red/green/blue.

*Backing up the original firmware*

LEGO doesn't offer standalone firmware files that can be downloaded, so it is
a good idea to back up your current firmware before erasing it.

Make sure the hub in in DFU mode, then run this command::

    pybricksdev dfu backup /path/to/original/firmware.bin

The path can be any file location and name you like as long as it is something
you will remember.

*Flashing the Pybricks firmware*

 Make sure the hub in in DFU mode, then run this command::

    pybricksdev flash ../pybricks-micropython/bricks/primehub/build/firmware.zip

Replace the example path with the path to the firmware archive.

*Restoring the original firmware*

Make sure the hub in in DFU mode, then run this command::

    pybricksdev dfu restore /path/to/original/firmware.bin

The path should be the path the file backup file you created above.

If you have lost your backup, GitHub user `@gpdaniels`_ has obtained
several original firmware versions.

After recovering this firmware, use the official SPIKE app to update to the
very latest firmware. Doing so is recommended, because that will also update
the files on the internal storage to the correct version.

.. _Device Firmware Upgrade (DFU): https://en.wikipedia.org/wiki/USB#Device_Firmware_Upgrade
.. _@gpdaniels: https://github.com/gpdaniels/spike-prime/
