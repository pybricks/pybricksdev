# SPDX-License-Identifier: MIT
# Copyright (c) 2021-2022 The Pybricks Authors

import asyncio
import os

import asyncssh


class EV3Connection:
    """ev3dev SSH connection for running pybricks-micropython scripts.

    This wraps convenience functions around the asyncssh client.
    """

    _HOME = "/home/robot"
    _USER = "robot"
    _PASSWORD = "maker"

    def abs_path(self, path):
        return os.path.join(self._HOME, path)

    async def connect(self, address):
        """Connects to ev3dev using SSH with a known IP address.

        Arguments:
            address (str):
                IP address of the EV3 brick running ev3dev.

        Raises:
            OSError:
                Connect failed.
        """

        print("Connecting to", address, "...", end=" ")
        self.client = await asyncssh.connect(
            address, username=self._USER, password=self._PASSWORD
        )
        print("Connected.", end=" ")
        self.client.sftp = await self.client.start_sftp_client()
        await self.client.sftp.chdir(self._HOME)
        print("Opened SFTP.")

    async def beep(self):
        """Makes the EV3 beep."""
        await self.client.run("beep")

    async def disconnect(self):
        """Closes the connection."""
        self.client.sftp.exit()
        self.client.close()

    async def download(self, local_path):
        """Downloads a file to the EV3 Brick using sftp.

        Arguments:
            local_path (str):
                Path to the file to be downloaded. Relative to current working
                directory. This same tree will be created on the EV3 if it
                does not already exist.
        """
        # Compute paths
        dirs, file_name = os.path.split(local_path)

        # Make sure same directory structure exists on EV3
        if not await self.client.sftp.exists(self.abs_path(dirs)):
            # If not, make the folders one by one
            total = ""
            for name in dirs.split(os.sep):
                total = os.path.join(total, name)
                if not await self.client.sftp.exists(self.abs_path(total)):
                    await self.client.sftp.mkdir(self.abs_path(total))

        # Send script to EV3
        remote_path = self.abs_path(local_path)
        await self.client.sftp.put(local_path, remote_path)
        return remote_path

    async def run(self, local_path, wait=True):
        """Downloads and runs a Pybricks MicroPython script.

        Arguments:
            local_path (str):
                Path to the file to be downloaded. Relative to current working
                directory. This same tree will be created on the EV3 if it
                does not already exist.
            wait (bool):
                Whether to wait for any output until the program completes.
        """

        # Send script to the hub
        remote_path = await self.download(local_path)

        # Run it and return stderr to get Pybricks MicroPython output
        print("Now starting:", remote_path)
        prog = "brickrun -r -- pybricks-micropython {0}".format(remote_path)

        # Run process asynchronously and print output as it comes in
        async with self.client.create_process(prog) as process:
            # Keep going until the process is done
            while process.exit_status is None and wait:
                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(), timeout=0.1
                    )
                    print(line.strip())
                except asyncio.TimeoutError:
                    pass

    async def get(self, remote_path, local_path=None):
        """Gets a file from the EV3 over sftp.

        Arguments:
            remote_path (str):
                Path to the file to be fetched. Relative to ev3 home directory.
            local_path (str):
                Path to save the file. Defaults to same as remote_path.
        """
        if local_path is None:
            local_path = remote_path
        await self.client.sftp.get(self.abs_path(remote_path), localpath=local_path)
