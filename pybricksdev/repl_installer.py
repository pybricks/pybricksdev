# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

import os
from asyncio import run, sleep
from zipfile import ZipFile
from hashlib import sha256
from importlib.resources import path

from . import resources

from .connections import CharacterGlue, USBConnection
from .flash import crc32_checksum


class USBREPLConnection(CharacterGlue, USBConnection):
    """Run commands in a MicroPython repl and print or eval the output."""

    def __init__(self, **kwargs):
        """Initialize base class with appropriate EOL for this connection."""
        self.stdout = []
        self.print_output = False
        super().__init__(EOL=b'\r\n', **kwargs)

    def line_handler(self, line):
        """Override base class to just store all incoming lines."""
        self.stdout.append(bytes(line))
        if self.print_output:
            print(line.decode())

    def is_ready(self):
        """Checks if REPL is ready for next command."""
        return self.char_buf[-4:] == b'>>> '

    async def reset(self):
        """Resets into REPL mode even if something is running."""
        self.char_buf = bytearray(b'')

        # Cancel anything that is running
        for i in range(3):
            await self.write(b'\x03')
            await sleep(0.1)

        # Soft reboot
        await self.write(b'\x04')
        await sleep(0.2)

        # Prevent runtime from coming up
        while not self.is_ready():
            await self.write(b'\x03')
            await sleep(0.1)

        self.stdout = []

    async def reboot(self):
        """Soft reboots the board."""
        await self.reset()
        await self.write(b'\x04')
        await sleep(3)

    async def exec_line(self, line, wait=True):
        """Executes one line of code and returns the standard output result."""
        encoded = line.encode()
        start_index = len(self.stdout)
        await self.write(encoded + b'\r\n')

        if not wait:
            return

        while len(self.stdout) == start_index:
            await sleep(0.01)
        if self.stdout[start_index] != b'>>> ' + encoded:
            raise ValueError("Failed to execute line: {0}.".format(line))
        while not self.is_ready():
            await sleep(0.01)
        if len(self.stdout) > start_index + 1:
            return b"".join(self.stdout[start_index + 1:])

    async def exec_and_eval(self, line):
        """Executes one line of code and evaluates the output."""
        return eval(await self.exec_line(line))


class REPLDualBootInstaller(USBREPLConnection):

    async def upload_file(self, remote_path, bin_data):
        """Uploads a file to a given destination on the hub."""

        # Reset the hub to a clean state
        await self.reset()

        # Split file into chunks (max 1000)
        packetsize = 1000
        chunks = [bin_data[i:i + packetsize] for i in range(0, len(bin_data), packetsize)]

        # Create the folder on the hub
        remote_folder, _ = os.path.split(remote_path)
        await self.exec_line("import os; os.mkdir('{0}')".format(remote_folder))

        # Initiate file transfer
        await self.exec_line('import hub; hub.file_transfer("{0}", {1}, packetsize={2}, timeout=10000)'.format(remote_path, len(bin_data), packetsize))

        print("Uploading data to:", remote_path)

        # Give hub time to create file, then trigger the transfer
        await sleep(0.2)
        await self.write(b'\x06')
        await sleep(0.5)

        # Write all the chunks one by one
        for i, chunk in enumerate(chunks):
            await self.write(chunk)
            await sleep(0.05)
            print("\r{0}%".format(round((i + 1) / len(chunks) * 100)), end="")
        print("\rTransfer complete!")

    async def install(self, firmware_archive_path):
        """Main dual boot install script."""
        await self.connect("LEGO Technic Large Hub in FS Mode")
        await self.reset()

        # Read Pybricks dual boot build
        archive = ZipFile(firmware_archive_path)
        pybricks_blob = archive.open('firmware-dual-boot-base.bin').read()
        pybricks_hash = sha256(pybricks_blob).hexdigest().encode('utf-8')

        # Upload firmware file.
        await self.upload_file('_pybricks/firmware.bin', pybricks_blob)

        # Upload empty init so the installer can be run by importing it
        await self.upload_file('_pybricks/__init__.py', b'# Intentionally left blank.')

        # Upload installation script.
        with path(resources, resources.INSTALL_PYBRICKS) as install_path:
            with open(install_path, "rb") as install_script:
                install_blob = install_script.read()
                install_hash = sha256(install_blob).hexdigest().encode('utf-8')
                await self.upload_file('_pybricks/install.py', install_blob)

        # Upload file with hashes to verify uploaded file integrity.
        await self.upload_file('_pybricks/hash.txt', pybricks_hash + b"\n" + install_hash + b"\n")

        # Run the installation script
        self.print_output = True
        await self.exec_line("from _pybricks.install import install; install()")

        # Remove installation files
        self.print_output = False
        await self.exec_line("import uos")
        await self.exec_line("uos.remove('_pybricks/__init__.py')")
        await self.exec_line("uos.remove('_pybricks/install.py')")
        await self.exec_line("uos.remove('_pybricks/firmware.bin')")

        # Disconnect.
        await self.disconnect()


if __name__ == "__main__":

    async def main():
        installer = REPLDualBootInstaller()
        await installer.install('../pybricks-micropython/bricks/primehub/build/firmware.zip')

    run(main())
