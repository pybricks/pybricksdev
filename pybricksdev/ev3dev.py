import asyncio
import asyncssh
from os import path

_connections = {}

_HOME = '/home/robot'
_USER = 'robot'
_PASSWORD = 'maker'


async def _get_connection(address):
    """Get SSH connection. Creates it if not yet connected."""

    global _connections

    try:
        # Try if connection exists and works
        await _connections[address].run('pwd')
        print("Re-using existing connection to", address)
    except (KeyError, AttributeError, asyncssh.ChannelOpenError):
        # No working connection, so connect
        print("Connecting to", address, "...", end=" ")
        _connections.pop(address, None)
        client = await asyncssh.connect(
            '192.168.133.101', username=_USER, password=_PASSWORD
        )
        print("Connected.", end=" ")

        # Open sftp unless it is already open
        try:
            await client.sftp.getcwd()
        except AttributeError:
            client.sftp = await client.start_sftp_client()
            await client.sftp.chdir(_HOME)
            print("Opened SFTP.")

        # All done, so save result for next time
        _connections[address] = client

    # Return existing or new client
    return _connections[address]


class EV3SSH():
    """EV3 Pybricks MicroPython SSH wrapper around asyncssh client."""

    async def connect(self, address):
        """Connect to EV3 or get existing connection."""
        self.client = await _get_connection(address)

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
        _, file_name = path.split(file_path)
        remote_path = path.join(_HOME, file_name)

        # Send script to EV3
        await self.client.sftp.put(file_path, remote_path)

        # Run it and return stderr to get Pybricks MicroPython output
        prog = 'brickrun -r -- pybricks-micropython {0}'.format(remote_path)
        result = await self.client.run(prog)
        return result.stderr


if __name__ == "__main__":
    async def _test():
        ev3 = EV3SSH()

        # Makes new connection and beeps
        await ev3.connect('192.168.133.101')
        await ev3.beep()
        print(await ev3.pybricks('demo/hello.py'))

    asyncio.run(_test())
