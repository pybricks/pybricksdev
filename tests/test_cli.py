"""Tests for the pybricksdev CLI commands."""

import argparse
import contextlib
import io
import os
import tempfile
from unittest.mock import AsyncMock, mock_open, patch

import pytest

from pybricksdev.cli import Download, Tool


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
