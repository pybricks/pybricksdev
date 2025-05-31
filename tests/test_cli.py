"""Tests for the pybricksdev CLI commands."""

import argparse
import contextlib
import io
import os
import tempfile
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from pybricksdev.cli import Compile, Download, Run, Tool, Udev


class TestTool:
    """Tests for the base Tool class."""

    def test_is_abstract(self):
        """Test that Tool is an abstract base class."""
        with pytest.raises(TypeError):
            Tool()


class TestDownload:
    """Tests for the Download command."""

    def test_add_parser(self):
        """Test that the parser is set up correctly."""
        # Create a subparsers object
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add the download command
        download = Download()
        download.add_parser(subparsers)

        # Verify the parser was created with correct arguments
        assert "download" in subparsers.choices
        parser = subparsers.choices["download"]
        assert parser.tool is download

        # Test that required arguments are present
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["ble", "test.py"])
            assert args.conntype == "ble"
            assert args.file.name == "test.py"
            assert args.name is None

        # Test with optional name argument
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["ble", "test.py", "-n", "MyHub"])
            assert args.name == "MyHub"

        # Test that invalid connection type is rejected
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid", "test.py"])

    @pytest.mark.asyncio
    async def test_download_ble(self):
        """Test running the download command with BLE connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub._mpy_abi_version = 6
        mock_hub.download = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=open(temp_path, "r"),
                name="MyHub",
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )

            # Run the command
            download = Download()
            await download.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.download.assert_called_once()
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_usb(self):
        """Test running the download command with USB connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub._mpy_abi_version = 6
        mock_hub.download = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="usb",
                file=open(temp_path, "r"),
                name=None,
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubUSB",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(patch("usb.core.find", return_value="mock_device"))

            # Run the command
            download = Download()
            await download.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.download.assert_called_once()
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_ssh(self):
        """Test running the download command with SSH connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.download = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ssh",
                file=open(temp_path, "r"),
                name="ev3dev.local",
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.ev3dev.EV3Connection",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("socket.gethostbyname", return_value="192.168.1.1")
            )

            # Run the command
            download = Download()
            await download.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("192.168.1.1")
            mock_hub.connect.assert_called_once()
            mock_hub.download.assert_called_once()
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_ssh_no_name(self):
        """Test that SSH connection requires a name."""
        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args without name
            args = argparse.Namespace(
                conntype="ssh",
                file=open(temp_path, "r"),
                name=None,
            )

            # Run the command and verify it exits
            download = Download()
            with pytest.raises(SystemExit, match="1"):
                await download.run(args)

    @pytest.mark.asyncio
    async def test_download_stdin(self):
        """Test running the download command with stdin input."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub._mpy_abi_version = 6
        mock_hub.download = AsyncMock()

        # Create a mock stdin
        mock_stdin = io.StringIO("print('test')")
        mock_stdin.buffer = io.BytesIO(b"print('test')")
        mock_stdin.name = "<stdin>"

        # Create args
        args = argparse.Namespace(
            conntype="ble",
            file=mock_stdin,
            name="MyHub",
        )

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )
            mock_temp = stack.enter_context(patch("tempfile.NamedTemporaryFile"))
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.py"

            # Run the command
            download = Download()
            await download.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.download.assert_called_once()
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_connection_error(self):
        """Test handling connection errors."""
        # Create a mock hub that raises an error during connect
        mock_hub = AsyncMock()
        mock_hub.connect.side_effect = RuntimeError("Connection failed")

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=open(temp_path, "r"),
                name="MyHub",
            )

            stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )

            # Run the command and verify it raises the error
            download = Download()
            with pytest.raises(RuntimeError, match="Connection failed"):
                await download.run(args)

            # Verify disconnect was not called since connection failed
            mock_hub.disconnect.assert_not_called()


class TestCompile:
    """Tests for the Compile command."""

    def test_add_parser(self):
        """Test that the parser is set up correctly."""
        # Create a subparsers object
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add the compile command
        compile_cmd = Compile()
        compile_cmd.add_parser(subparsers)

        # Verify the parser was created with correct arguments
        assert "compile" in subparsers.choices
        parser = subparsers.choices["compile"]
        assert parser.tool is compile_cmd

        # Test that required arguments are present
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["test.py"])
            assert args.file.name == "test.py"
            assert args.abi == 6  # Default ABI version

        # Test with custom ABI version
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["test.py", "--abi", "5"])
            assert args.abi == 5

        # Test that invalid ABI version is rejected
        with pytest.raises(SystemExit):
            parser.parse_args(["test.py", "--abi", "4"])

    @pytest.mark.asyncio
    async def test_compile_file(self):
        """Test compiling a Python file."""
        # Create a mock compile function
        mock_compile = AsyncMock()
        mock_compile.return_value = b"compiled bytecode"

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                file=open(temp_path, "r"),
                abi=6,
            )

            # Mock the compile function
            stack.enter_context(
                patch("pybricksdev.compile.compile_multi_file", mock_compile)
            )
            mock_print = stack.enter_context(patch("pybricksdev.compile.print_mpy"))

            # Run the command
            compile_cmd = Compile()
            await compile_cmd.run(args)

            # Verify compilation was called correctly
            mock_compile.assert_called_once_with(temp_path, 6)
            mock_print.assert_called_once_with(b"compiled bytecode")

    @pytest.mark.asyncio
    async def test_compile_stdin(self):
        """Test compiling from stdin."""
        # Create a mock stdin
        mock_stdin = io.StringIO("print('test')")
        mock_stdin.buffer = io.BytesIO(b"print('test')")
        mock_stdin.name = "<stdin>"

        # Create a mock compile function
        mock_compile = AsyncMock()
        mock_compile.return_value = b"compiled bytecode"

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create args
            args = argparse.Namespace(
                file=mock_stdin,
                abi=6,
            )

            # Mock the compile function and tempfile
            stack.enter_context(
                patch("pybricksdev.compile.compile_multi_file", mock_compile)
            )
            mock_print = stack.enter_context(patch("pybricksdev.compile.print_mpy"))
            mock_temp = stack.enter_context(patch("tempfile.NamedTemporaryFile"))
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.py"
            mock_temp.return_value.__enter__.return_value.write = Mock()
            mock_temp.return_value.__enter__.return_value.flush = Mock()

            # Run the command
            compile_cmd = Compile()
            await compile_cmd.run(args)

            # Verify compilation was called correctly
            mock_compile.assert_called_once_with("<stdin>", 6)
            mock_print.assert_called_once_with(b"compiled bytecode")


class TestRun:
    """Tests for the Run command."""

    def test_add_parser(self):
        """Test that the parser is set up correctly."""
        # Create a subparsers object
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add the run command
        run_cmd = Run()
        run_cmd.add_parser(subparsers)

        # Verify the parser was created with correct arguments
        assert "run" in subparsers.choices
        parser = subparsers.choices["run"]
        assert parser.tool is run_cmd

        # Test that required arguments are present
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["ble", "test.py"])
            assert args.conntype == "ble"
            assert args.file.name == "test.py"
            assert args.name is None
            assert args.wait is True  # Default wait value

        # Test with optional name argument
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["ble", "test.py", "-n", "MyHub"])
            assert args.name == "MyHub"

        # Test with wait/no-wait arguments
        mock_file = mock_open(read_data="print('test')")
        mock_file.return_value.name = "test.py"
        with patch("builtins.open", mock_file):
            args = parser.parse_args(["ble", "test.py", "--no-wait"])
            assert args.wait is False

        # Test that invalid connection type is rejected
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid", "test.py"])

    @pytest.mark.asyncio
    async def test_run_ble(self):
        """Test running a program with BLE connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=open(temp_path, "r"),
                name="MyHub",
                wait=True,
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.run.assert_called_once_with(temp_path, True)
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_usb(self):
        """Test running a program with USB connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="usb",
                file=open(temp_path, "r"),
                name=None,
                wait=True,
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubUSB",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(patch("usb.core.find", return_value="mock_device"))

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.run.assert_called_once_with(temp_path, True)
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_ssh(self):
        """Test running a program with SSH connection."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ssh",
                file=open(temp_path, "r"),
                name="ev3dev.local",
                wait=True,
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.ev3dev.EV3Connection",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("socket.gethostbyname", return_value="192.168.1.1")
            )

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("192.168.1.1")
            mock_hub.connect.assert_called_once()
            mock_hub.run.assert_called_once_with(temp_path, True)
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_ssh_no_name(self):
        """Test that SSH connection requires a name."""
        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args without name
            args = argparse.Namespace(
                conntype="ssh",
                file=open(temp_path, "r"),
                name=None,
                wait=True,
            )

            # Run the command and verify it exits
            run_cmd = Run()
            with pytest.raises(SystemExit, match="1"):
                await run_cmd.run(args)

    @pytest.mark.asyncio
    async def test_run_stdin(self):
        """Test running a program from stdin."""
        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()

        # Create a mock stdin
        mock_stdin = io.StringIO("print('test')")
        mock_stdin.buffer = io.BytesIO(b"print('test')")
        mock_stdin.name = "<stdin>"

        # Create args
        args = argparse.Namespace(
            conntype="ble",
            file=mock_stdin,
            name="MyHub",
            wait=True,
        )

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )
            mock_temp = stack.enter_context(patch("tempfile.NamedTemporaryFile"))
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.py"
            mock_temp.return_value.__enter__.return_value.write = Mock()
            mock_temp.return_value.__enter__.return_value.flush = Mock()

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.run.assert_called_once_with("<stdin>", True)
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_connection_error(self):
        """Test handling connection errors."""
        # Create a mock hub that raises an error during connect
        mock_hub = AsyncMock()
        mock_hub.connect.side_effect = RuntimeError("Connection failed")

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=open(temp_path, "r"),
                name="MyHub",
                wait=True,
            )

            stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubBLE",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )

            # Run the command and verify it raises the error
            run_cmd = Run()
            with pytest.raises(RuntimeError, match="Connection failed"):
                await run_cmd.run(args)

            # Verify disconnect was not called since connection failed
            mock_hub.disconnect.assert_not_called()


class TestUdev:
    """Tests for the Udev command."""

    def test_add_parser(self):
        """Test that the parser is set up correctly."""
        # Create a subparsers object
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add the udev command
        udev_cmd = Udev()
        udev_cmd.add_parser(subparsers)

        # Verify the parser was created with correct arguments
        assert "udev" in subparsers.choices
        parser = subparsers.choices["udev"]
        assert parser.tool is udev_cmd

    @pytest.mark.asyncio
    async def test_print_rules(self):
        """Test printing udev rules."""
        # Mock the read_text function
        mock_rules = (
            '# Mock udev rules\nSUBSYSTEM=="usb", ATTRS{idVendor}=="0694", MODE="0666"'
        )
        mock_read_text = Mock(return_value=mock_rules)

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create args
            args = argparse.Namespace()

            # Mock the read_text function
            stack.enter_context(patch("importlib.resources.read_text", mock_read_text))
            mock_print = stack.enter_context(patch("builtins.print"))

            # Run the command
            udev_cmd = Udev()
            await udev_cmd.run(args)

            # Verify the rules were printed
            mock_read_text.assert_called_once()
            mock_print.assert_called_once_with(mock_rules)
