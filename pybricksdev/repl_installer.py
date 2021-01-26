from asyncio import run, sleep
from pybricksdev.connections import CharacterGlue, USBConnection


class USBREPLConnection(CharacterGlue, USBConnection):

    def __init__(self, **kwargs):
        self.stdout = []
        super().__init__(EOL=b'\r\n', **kwargs)

    def line_handler(self, line):
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
        """Soft reboots the hub."""
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
        return eval(await self.exec_line(line))


class REPLDualBootInstaller(USBREPLConnection):

    FLASH_OFFSET = 0x8008000

    async def get_firmware_version(self):
        """Gets firmware version without reboot"""

        # Read boot sector
        boot_data = await self.exec_and_eval(
            "import firmware; firmware.flash_read(0x200)"
        )

        # Read firmware version data
        position = int.from_bytes(boot_data[0:4], 'little') - self.FLASH_OFFSET
        version_bytes = await self.exec_and_eval(
            "firmware.flash_read({0})".format(position)
        )

        # Return version string
        return version_bytes[0:20].decode()

    async def show_image(self, image):
        # Convert 2D list to expected string format
        image_string = ":".join([
            "".join([str(round(min(abs(i), 100)*0.09)) for i in col]) for col in image
        ])

        # Display the image
        await self.exec_line("import hub")
        await self.exec_line("hub.display.show(hub.Image('{0}'))".format(image_string))

    async def show_progress(self, progress):
        """Create 2D grid of intensities to show 0--100% 25 pixels."""
        progress = max(0, min(round(progress), 100))
        image = [[0 for i in range(5)] for j in range(5)]
        for i, row in enumerate(image):
            for j, col in enumerate(row):
                pixel_position = (i * 5 + j) * 4
                if progress > pixel_position:
                    image[i][j] = min((progress - pixel_position)*25, 100)
        await self.show_image(image)


if __name__ == "__main__":

    async def main():
        repl = REPLDualBootInstaller()
        await repl.connect("LEGO Technic Large Hub in FS Mode")

        await repl.reset()
        print(await repl.get_firmware_version())

        for i in range(101):
            await repl.show_progress(i)
            await sleep(0.03)

    run(main())
