from asyncio import run, sleep
from pybricksdev.connections import CharacterGlue, USBConnection


class USBREPLConnection(CharacterGlue, USBConnection):
    """Run commands in a MicroPython repl and print or eval the output."""

    def __init__(self, **kwargs):
        """Initialize base class with appropriate EOL for this connection."""
        self.stdout = []
        super().__init__(EOL=b'\r\n', **kwargs)

    def line_handler(self, line):
        """Override base class to just store all incoming lines."""
        self.stdout.append(bytes(line))

    def is_ready(self):
        """Checks if REPL is ready for next command."""
        return self.char_buf[-4:] == b'>>> '

    async def reset(self):
        """Resets into REPL mode even if something is running."""
        self.stdout = []
        while not self.is_ready():
            await self.write(b'\x03')
            await sleep(0.1)

    async def reboot(self):
        """Soft reboots the board."""
        await self.reset()
        await self.write(b'\x04')
        await sleep(3)

    async def exec_line(self, line):
        """Executes one line of code and returns the standard output result."""
        encoded = line.encode()
        start_index = len(self.stdout)
        await self.write(encoded + b'\r\n')
        while len(self.stdout) == start_index:
            await sleep(0.01)
        if self.stdout[start_index] != b'>>> ' + encoded:
            raise ValueError(b"Failed to execute line: {0}.".format(line))
        while not self.is_ready():
            await sleep(0.01)
        if len(self.stdout) > start_index + 1:
            return b"".join(self.stdout[start_index + 1:])

    async def exec_and_eval(self, line):
        """Executes one line of code and evaluates the output."""
        return eval(await self.exec_line(line))


class REPLDualBootInstaller(USBREPLConnection):

    PYBRICKS_BASE = 0x80C0000
    FLASH_OFFSET = 0x8008000
    READ_BLOCKS = 8

    async def get_base_firmware_info(self):
        """Gets firmware version without reboot"""

        # Read boot sector
        boot_data = await self.exec_and_eval(
            "import firmware; firmware.flash_read(0x200)"
        )

        # Read firmware version data
        version_position = int.from_bytes(boot_data[0:4], 'little') - self.FLASH_OFFSET
        base_firmware_version = (await self.exec_and_eval(
            "firmware.flash_read({0})".format(version_position)
        ))[0:20].decode()

        # Read firmware size data
        checksum_position = int.from_bytes(boot_data[4:8], 'little') - self.FLASH_OFFSET
        base_firmware_checksum = int.from_bytes((await self.exec_and_eval(
            "firmware.flash_read({0})".format(checksum_position)))[0:4], 'little')
        base_firmware_size = checksum_position + 4

        # Read the boot vector
        base_firmware_vector = await self.get_base_firmware_vector()

        # Return firmware info
        return {
            "size": base_firmware_size,
            "version": base_firmware_version,
            "checksum": base_firmware_checksum,
            "boot_vector": base_firmware_vector
        }

    async def get_base_firmware_vector(self):
        """Gets base firmware boot vector, already accounting for dual boot."""

        # Import firmware module
        await self.exec_line("import firmware")

        # Read base vector sector
        base_vector_data = (await self.exec_and_eval(
            "import firmware; firmware.flash_read(0x000)"
        ))[4:8]

        # If it's running pure stock firmware, return as is.
        if int.from_bytes(base_vector_data, 'little') < self.PYBRICKS_BASE:
            print("Currently running single-boot firmware.")
            return base_vector_data

        # Otherwise read the boot vector in Pybricks, which points at base.
        print("Currently running dual-boot firmware.")
        return (await self.exec_and_eval(
            "import firmware; firmware.flash_read({0})".format(
                self.PYBRICKS_BASE - self.FLASH_OFFSET)))[4:8]

    async def get_flash_block(self, address):
        return await self.exec_and_eval(
                "+".join(["flr({0})".format(address + i * 32) for i in range(self.READ_BLOCKS)])
        )

    async def get_base_firmware_blob(self, base_firmware_info):
        """Backs up original firmware with original boot vector."""

        size = base_firmware_info["size"]
        print("Backing up {0} bytes of original firmware. Progress:".format(size))

        # Import abbreviated function to reduce data transfer
        await self.exec_line("from firmware import flash_read as flr")

        # Read the first chunk and reinstate the original boot vector
        blob = await self.get_flash_block(0)
        blob = blob[0:4] + base_firmware_info["boot_vector"] + blob[8:]

        # Read the remainder up to the requested size
        bytes_read = len(blob)

        # Yield new blocks until done.
        while bytes_read < size:

            # Read several chunks of 32 bytes into one block.
            block = await self.get_flash_block(bytes_read)
            bytes_read += len(block)

            # If we read past the end, cut off the extraneous bytes.
            if bytes_read > size:
                block = block[0: size % len(block)]

            # Add the resulting block.
            blob += block

            print("{0}%".format(int(len(blob)/size*100)), end="\r")

        # Also save a copy to disk
        with open("firmware-" + base_firmware_info["version"] + ".bin", "wb") as bin_file:
            bin_file.write(blob)

        print("Backup complete\n")

    async def show_image(self, image):
        """Shows an image made as a 2D list of intensities."""

        # Convert 2D list to expected string format
        image_string = ":".join([
            "".join([str(round(min(abs(i), 100)*0.09)) for i in col]) for col in image
        ])

        # Display the image
        await self.exec_line("import hub")
        await self.exec_line("hub.display.show(hub.Image('{0}'))".format(image_string))

    async def show_progress(self, progress):
        """Create 2D grid of intensities to show 0--100% 25 pixels."""
        await self.show_image([[
                max(0, min((progress - (i * 5 + j) * 4) * 25, 100)) for j in range(5)
            ] for i in range(5)
        ])


if __name__ == "__main__":

    async def main():

        # Initialize connection
        repl = REPLDualBootInstaller()
        await repl.connect("LEGO Technic Large Hub in FS Mode")
        await repl.reset()

        # Get firmware information
        base_firmware_info = await repl.get_base_firmware_info()
        print("Detected firmware:")
        print(base_firmware_info)

        # Back up the original firmware
        await repl.get_base_firmware_blob(base_firmware_info)

        # for i in range(101):
        #     await repl.show_progress(i)
        #     await sleep(0.03)



    run(main())
