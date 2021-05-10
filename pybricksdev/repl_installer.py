# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

import os

from time import sleep
from zipfile import ZipFile
from hashlib import sha256
from importlib.resources import path

from . import resources

from serial.tools import list_ports
from serial import Serial


class REPLDualBootInstaller():
    """Installs Pybricks on a SPIKE Prime Hub or MINDSTORMS Robot Inventor Hub."""

    def __init__(self):
        self.stdout = []
        self.print_output = False
        self.buffer = b''

    def connect(self):
        port = None
        devices = list_ports.comports()
        for dev in devices:
            if dev.product == "LEGO Technic Large Hub in FS Mode" or (dev.pid == 0x5740 and dev.vid == 0x0483) or (dev.vid == 0x0694 and dev.pid == 0x0010) or (dev.vid == 0x0694 and dev.pid == 0x0009):
                port = dev.device
                break

        if port is None:
            raise OSError("Could not find hub.")

        print("Connecting to {0}".format(port))
        self.serial = Serial(port)

    def disconnect(self):
        self.serial.close()

    def parse_input(self):
        data = self.serial.read(self.serial.in_waiting)
        self.buffer += data
        if self.print_output:
            print(data.decode(), end="")

    def is_ready(self, key=b'>>> '):
        """Checks if REPL is ready for next command."""
        self.parse_input()
        return self.buffer[-len(key):] == key

    def reset(self):
        """Resets into REPL mode even if something is running."""
        self.buffer = b''

        # Cancel anything that is running
        for i in range(3):
            self.serial.write(b'\x03')
            sleep(0.1)

        # Soft reboot
        self.serial.write(b'\x04')
        sleep(0.2)

        # Prevent runtime from coming up
        while not self.is_ready():
            self.serial.write(b'\x03')
            sleep(0.1)

        self.stdout = []

    def reboot(self):
        """Soft reboots the board."""
        self.reset()
        self.write(b'\x04')
        sleep(3)

    def exec_line(self, line, wait=True):
        """Executes one line of code and returns the standard output result."""
        self.parse_input()
        encoded = line.encode()
        start_len = len(self.buffer)
        echo = encoded + b'\r\n'
        self.serial.write(echo)

        if not wait:
            return

        while len(self.buffer) < start_len + len(echo):
            self.parse_input()
        if echo not in self.buffer[start_len - 1:]:
            print(self.buffer, echo)
            raise ValueError("Failed to execute line: {0}.".format(line))
        while not self.is_ready():
            sleep(0.01)

    def upload_file(self, remote_path, bin_data):
        """Uploads a file to a given destination on the hub."""

        # Reset the hub to a clean state
        self.reset()

        # Split file into chunks (max 1000)
        packetsize = 1000
        chunks = [bin_data[i:i + packetsize] for i in range(0, len(bin_data), packetsize)]

        # Create the folder on the hub
        remote_folder, _ = os.path.split(remote_path)
        self.exec_line("import os; os.mkdir('{0}')".format(remote_folder))

        # Initiate file transfer
        self.exec_line('import hub; hub.file_transfer("{0}", {1}, packetsize={2}, timeout=10000)'.format(remote_path, len(bin_data), packetsize))

        print("Uploading data to:", remote_path)

        # Give hub time to create file, then trigger the transfer
        sleep(0.05)
        self.serial.write(b'\x06')
        while not self.is_ready(b'filetransfer started;\r\n'):
            sleep(0.1)

        # Write all the chunks one by one
        for i, chunk in enumerate(chunks):
            self.serial.write(chunk)
            if i <= 2:
                sleep(0.5)
            else:
                sleep(0.05)
            print("\r{0}%".format(round((i + 1) / len(chunks) * 100)), end="")

        print("\rTransfer complete!")
        # Add a new line so the file transfer started printout is flushed.
        self.serial.write(b"\r\n")
        while not self.is_ready():
            sleep(0.1)

    def install(self, firmware_archive_path):
        """Main dual boot install script."""

        self.connect()
        self.reset()

        # Read Pybricks dual boot build
        archive = ZipFile(firmware_archive_path)
        pybricks_blob = archive.open('firmware-dual-boot-base.bin').read()
        pybricks_hash = sha256(pybricks_blob).hexdigest().encode('utf-8')

        # Upload firmware file.
        self.upload_file('_pybricks/firmware.bin', pybricks_blob)

        # Upload empty init so the installer can be run by importing it
        self.upload_file('_pybricks/__init__.py', b'# Intentionally left blank.')

        # Upload installation script.
        with path(resources, resources.INSTALL_PYBRICKS) as install_path:
            with open(install_path, "rb") as install_script:
                install_blob = install_script.read()
                install_hash = sha256(install_blob).hexdigest().encode('utf-8')
                self.upload_file('_pybricks/install.py', install_blob)

        # Upload file with hashes to verify uploaded file integrity.
        self.upload_file('_pybricks/hash.txt', pybricks_hash + b"\n" + install_hash + b"\n")

        # Run the installation script
        self.print_output = True
        self.exec_line("from _pybricks.install import install; install()")

        # Remove installation files
        self.print_output = False
        self.exec_line("import uos")
        self.exec_line("uos.remove('_pybricks/__init__.py')")
        self.exec_line("uos.remove('_pybricks/install.py')")
        self.exec_line("uos.remove('_pybricks/firmware.bin')")

        # Disconnect.
        self.disconnect()
