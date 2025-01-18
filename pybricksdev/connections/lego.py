# SPDX-License-Identifier: MIT
# Copyright (c) 2021-2022 The Pybricks Authors

import asyncio
import os

from serial import Serial
from serial.tools import list_ports

from pybricksdev.connections.pybricks import PybricksHub
from pybricksdev.tools import chunk
from pybricksdev.usb import LEGO_USB_VID

FILE_PACKET_SIZE = 1024
FILE_TRANSFER_SCRIPT = f"""
import sys
import micropython
import utime

PACKETSIZE = {FILE_PACKET_SIZE}

def receive_file(filename, filesize):

    micropython.kbd_intr(-1)

    with open(filename, "wb") as f:

        # Initialize buffers
        done = 0
        buf = bytearray(PACKETSIZE)
        sys.stdin.buffer.read(1)

        while done < filesize:

            # Size of last package
            if filesize - done < PACKETSIZE:
                buf = bytearray(filesize - done)

            # Read one packet from standard in.
            time_now = utime.ticks_ms()
            bytes_read = sys.stdin.buffer.readinto(buf)

            # If transmission took a long time, something bad happened.
            if utime.ticks_ms() - time_now > 5000:
                print("transfer timed out")
                return

            # Write the data and say we're ready for more.
            f.write(buf)
            done += bytes_read
            print("ACK")
"""


class REPLHub:
    """Run scripts on generic MicroPython boards with a REPL over USB."""

    EOL = b"\r\n"  # MicroPython EOL

    def __init__(self):
        self.reset_buffers()

    def reset_buffers(self):
        """Resets internal buffers that track (parsed) serial data."""
        self.print_output = False
        self.output = []
        self.buffer = b""
        self.log_file = None
        try:
            self.serial.read(self.serial.in_waiting)
        except AttributeError:
            pass

    async def connect(self, device=None):
        """Connects to a SPIKE Prime or MINDSTORMS Inventor Hub."""

        # Go through all comports.
        port = None
        devices = list_ports.comports()
        for dev in devices:
            if (
                dev.product == "LEGO Technic Large Hub in FS Mode"
                or dev.vid == LEGO_USB_VID
            ):
                port = dev.device
                break

        # Raise error if there is no hub.
        if port is None:
            raise OSError("Could not find hub.")

        # Open the serial connection.
        print("Connecting to {0}".format(port))
        self.serial = Serial(port)
        self.serial.read(self.serial.in_waiting)
        print("Connected!")

    async def disconnect(self):
        """Disconnects from the hub."""
        self.serial.close()

    def parse_input(self):
        """Reads waiting serial data and parse as needed."""
        data = self.serial.read(self.serial.in_waiting)
        self.buffer += data

    def is_idle(self, key=b">>> "):
        """Checks if REPL is ready for a new command."""
        self.parse_input()
        return self.buffer[-len(key) :] == key

    async def reset_hub(self):
        """Soft resets the hub to clear MicroPython variables."""

        # Cancel anything that is running
        for i in range(5):
            self.serial.write(b"\x03")
            await asyncio.sleep(0.1)

        # Soft reboot
        self.serial.write(b"\x04")
        await asyncio.sleep(0.5)

        # Prevent runtime from coming up
        while not self.is_idle():
            self.serial.write(b"\x03")
            await asyncio.sleep(0.1)

        # Clear all buffers
        self.reset_buffers()

        # Load file transfer function
        await self.exec_paste_mode(FILE_TRANSFER_SCRIPT, print_output=False)
        self.reset_buffers()

        print("Hub is ready.")

    async def exec_line(self, line, wait=True):
        """Executes one line on the REPL."""

        # Initialize
        self.reset_buffers()
        encoded = line.encode()
        start_len = len(self.buffer)

        # Write the command and prepare expected echo.
        echo = encoded + b"\r\n"
        self.serial.write(echo)

        # Wait until the echo has been read.
        while len(self.buffer) < start_len + len(echo):
            await asyncio.sleep(0.05)
            self.parse_input()
        # Raise error if we did not get the echo back.
        if echo not in self.buffer[start_len:]:
            print(start_len, self.buffer, self.buffer[start_len - 1 :], echo)
            raise ValueError("Failed to execute line: {0}.".format(line))

        # We are done if we don't want to wait for the result.
        if not wait:
            return

        # Wait for MicroPython to execute the command.
        while not self.is_idle():
            await asyncio.sleep(0.1)

    line_handler = PybricksHub._line_handler

    async def exec_paste_mode(self, code, wait=True, print_output=True):
        """Executes commands via paste mode."""

        # Initialize buffers
        self.reset_buffers()
        self.print_output = print_output

        # Convert script string to binary.
        encoded = code.encode()

        # Enter paste mode.
        self.serial.write(b"\x05")
        while not self.is_idle(key=b"=== "):
            await asyncio.sleep(0.1)

        # Paste the script, chunk by chunk to avoid overrun
        start_len = len(self.buffer)
        echo = encoded + b"\r\n"

        for c in chunk(echo, 200):
            self.serial.write(c)
            # Wait until the pasted code is echoed back.
            while len(self.buffer) < start_len + len(c):
                await asyncio.sleep(0.05)
                self.parse_input()

            # If it isn't, then stop.
            if c not in self.buffer[start_len:]:
                print(start_len, self.buffer, self.buffer[start_len - 1 :], echo)
                raise ValueError("Failed to paste: {0}.".format(code))

            start_len += len(c)

        # Parse hub output until the script is done.
        line_index = len(self.buffer)
        self.output = []

        # Exit paste mode and start executing.
        self.serial.write(b"\x04")

        # If we don't want to wait, we are done.
        if not wait:
            return

        # Look for output while the program runs
        while not self.is_idle():
            # Keep parsing hub data.
            self.parse_input()

            # Look for completed lines that we haven't parsed yet.
            next_line_index = self.buffer.find(self.EOL, line_index)

            if next_line_index >= 0:
                # If a new line is found, parse it.
                self.line_handler(self.buffer[line_index:next_line_index])
                line_index = next_line_index + len(self.EOL)
            await asyncio.sleep(0.1)

        # Parse remaining hub data.
        while (next_line_index := self.buffer.find(self.EOL, line_index)) >= 0:
            self.line_handler(self.buffer[line_index:next_line_index])
            line_index = next_line_index + len(self.EOL)

    async def run(self, py_path, wait=True, print_output=True):
        """Executes a script via paste mode."""
        script = open(py_path).read()
        self.script_dir, _ = os.path.split(py_path)
        await self.reset_hub()
        await self.exec_paste_mode(script, wait, print_output)

    async def upload_file(self, destination, contents):
        """Uploads a file to the hub."""

        # Print upload info.
        size = len(contents)
        print(f"Uploading {destination} ({size} bytes)")
        self.reset_buffers()

        # Prepare hub to receive file
        await self.exec_line(f"receive_file('{destination}', {size})", wait=False)

        ACK = b"ACK" + self.EOL
        progress = 0

        # Write file chunk by chunk.
        for data in chunk(contents, FILE_PACKET_SIZE):
            # Send a chunk and wait for acknowledgement of receipt
            buffer_now = len(self.buffer)
            progress += self.serial.write(data)
            while len(self.buffer) < buffer_now + len(ACK):
                await asyncio.sleep(0.01)
                self.parse_input()

            # Raise error if we didn't get acknowledgement
            if self.buffer[buffer_now : buffer_now + len(ACK)] != ACK:
                print(self.buffer[buffer_now:])
                raise ValueError("Did not get expected response from the hub.")

            # Print progress
            print(f"Progress: {int(progress / size * 100)}%", end="\r")

        # Get REPL back in normal state
        await self.exec_line("# File transfer complete")
