from paramiko import SSHClient, AutoAddPolicy
from os import path

_connections = {}

_HOME = '/home/robot'
_USER = 'robot'
_PASSWORD = 'maker'


def _get_connection(address):
    """Get SSH connection. Creates it if not yet connected."""

    global _connections

    try:
        # Try if connection exists and works
        cwd = _connections[address].exec_command('pwd')[1].read()
        if cwd.decode().strip() != _HOME:
            raise OSError
        print("Re-using existing connection to", address)
    except (KeyError, AttributeError):
        print("Connecting to", address, "...", end=" ")

        # No working connection, so connect
        _connections.pop(address, None)

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(address, username=_USER, password=_PASSWORD)
        print("Connected.", end=" ")

        # Open sftp unless it is already open
        try:
            if client.sftp.getcwd() != _HOME:
                raise OSError
        except AttributeError:
            client.sftp = client.open_sftp()
            client.sftp.chdir(_HOME)
            print("Opened SFTP.")

        # All done, so save result for next time
        _connections[address] = client

    # Return existing or new client
    return _connections[address]


class EV3SSH():
    """EV3 Pybricks MicroPython SSH wrapper around Paramiko SSH Client."""

    def __init__(self, address):
        """Initializes client using new or existing connection."""
        self.client = _get_connection(address)

    def command(self, command):
        """Runs a command on the shell and returns stdout and stderr."""
        ssh_stdin, ssh_stdout, ssh_stderr = self.client.exec_command(command)
        return ssh_stdout.read(), ssh_stderr.read()

    def close(self):
        """Close the connection."""
        self.client.sftp.close()
        self.client.close()

    def run(self, file_path):
        """Download and run a Pybricks MicroPython script."""
        remote_path = path.join(_HOME, file_path)
        self.client.sftp.put(file_path, remote_path)
        return self.command(
            'brickrun -r -- pybricks-micropython {0}'.format(remote_path))[1]
