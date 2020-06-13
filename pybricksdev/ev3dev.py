import asyncio
import asyncssh
from os import path, sep


_HOME = '/home/robot'
_USER = 'robot'
_PASSWORD = 'maker'


class EV3SSH():
    """EV3 Pybricks MicroPython SSH wrapper around asyncssh client."""

    async def connect(self, address):
        """Connect to EV3 or get existing connection."""

        print("Connecting to", address, "...", end=" ")
        self.client = await asyncssh.connect(
            address, username=_USER, password=_PASSWORD
        )
        print("Connected.", end=" ")

        self.client.sftp = await self.client.start_sftp_client()
        await self.client.sftp.chdir(_HOME)
        print("Opened SFTP.")

    async def beep(self):
        """Runs a command on the shell and returns stdout and stderr."""
        await self.client.run('beep')

    async def disconnect(self):
        """Close the connection."""
        self.client.sftp.exit()
        self.client.close()

    async def pybricks(self, file_path):
        """Download and run a Pybricks MicroPython script."""

        # Compute paths
        dirs, file_name = path.split(file_path)

        # Make sure same directory structure exists on EV3
        if not await self.client.sftp.exists(path.join(_HOME, dirs)):
            # If not, make the folders one by one
            total = ''
            for name in dirs.split(sep):
                total = path.join(total, name)
                if not await self.client.sftp.exists(path.join(_HOME, total)):
                    await self.client.sftp.mkdir(path.join(_HOME, total))

        # Send script to EV3
        remote_path = path.join(_HOME, file_path)
        await self.client.sftp.put(file_path, remote_path)

        # Run it and return stderr to get Pybricks MicroPython output
        print("Now starting:", remote_path)
        prog = 'brickrun -r -- pybricks-micropython {0}'.format(remote_path)

        # Run process asynchronously and print output as it comes in
        async with self.client.create_process(prog) as process:
            # Keep going until the process is done
            while process.exit_status is None:
                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(), timeout=0.1
                    )
                    print(line.strip())
                except asyncio.exceptions.TimeoutError:
                    pass

    async def get(self, file_path, local_path=None):
        if local_path is None:
            local_path = file_path
        await self.client.sftp.get(path.join(_HOME, file_path), localpath=local_path)


if __name__ == "__main__":
    async def _test():
        ev3 = EV3SSH()

        # Makes new connection and beeps
        await ev3.connect('192.168.133.101')
        await ev3.beep()
        await ev3.pybricks('demo/hello.py')

    asyncio.run(_test())
