"""Tests for the pybricksdev CLI commands."""

import argparse
import asyncio
import contextlib
import io
import os
import subprocess
import tempfile
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
from packaging.version import Version

from pybricksdev.cli import Compile, Run, Tool, Udev
from pybricksdev.connections.pybricks import (
    HubDisconnectError,
    HubPowerButtonPressedError,
)


class TestTool:
    """Tests for the base Tool class."""

    def test_is_abstract(self):
        """Test that Tool is an abstract base class."""
        with pytest.raises(TypeError):
            Tool()


class TestRun:
    """Tests for the Download command."""

    def test_add_parser(self):
        """Test that the parser is set up correctly."""
        # Create a subparsers object
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add the download command
        run = Run()
        run.add_parser(subparsers)

        # Verify the parser was created with correct arguments
        assert "run" in subparsers.choices
        parser = subparsers.choices["run"]
        assert parser.tool is run

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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=False,
                wait=False,
                stay_connected=False,
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
            run = Run()
            await run.run(args)

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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="usb",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name=None,
                start=False,
                wait=False,
                stay_connected=False,
            )

            mock_hub_class = stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.PybricksHubUSB",
                    return_value=mock_hub,
                )
            )
            stack.enter_context(patch("usb.core.find", return_value="mock_device"))

            # Run the command
            run = Run()
            await run.run(args)

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
            start=False,
            wait=False,
            stay_connected=False,
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
            run = Run()
            await run.run(args)

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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=False,
                wait=False,
                stay_connected=False,
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
            run = Run()
            with pytest.raises(RuntimeError, match="Connection failed"):
                await run.run(args)

            # Verify disconnect was not called since connection failed
            mock_hub.disconnect.assert_not_called()

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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=False,
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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="usb",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name=None,
                start=True,
                wait=True,
                stay_connected=False,
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
            start=True,
            wait=True,
            stay_connected=False,
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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=False,
                wait=True,
                stay_connected=False,
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

    @pytest.mark.asyncio
    async def test_run_syntax_error(self):
        """Test that the stay connected menu is called upon a syntax error when the appropriate flag is active."""

        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock(
            side_effect=subprocess.CalledProcessError(
                returncode=1, cmd="test", stderr=b"test"
            )
        )
        mock_hub.connect = AsyncMock()

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=True,
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
            mock_menu = stack.enter_context(
                patch("pybricksdev.cli.Run.stay_connected_menu")
            )

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()
            mock_hub.run.assert_called_once_with(temp_path, True)
            mock_menu.assert_called_once_with(mock_hub, args)
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stay_connected_menu_integration(self):
        """Test all of the basic options in the stay_connected menu."""

        async def passthrough_awaitable(awaitable):
            return await awaitable

        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.fw_version = Version("3.2.0-beta.4")
        mock_hub.run = AsyncMock()
        mock_hub.connect = AsyncMock()
        mock_hub.start_user_program = AsyncMock()
        mock_hub._wait_for_user_program_stop = AsyncMock()
        mock_hub.race_disconnect = mock_hub.race_power_button_press = AsyncMock(
            side_effect=passthrough_awaitable
        )
        mock_hub.download = AsyncMock()

        # create a mock questionary menu
        mock_selector = AsyncMock()
        mock_selector.ask_async.side_effect = [
            "Recompile and Run",
            "Recompile and Download",
            "Run Stored Program",
            "Exit",
        ]

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=True,
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
            mock_selector = stack.enter_context(
                patch("questionary.select", return_value=mock_selector)
            )

            # Run the command
            run_cmd = Run()
            await run_cmd.run(args)

            # Verify the hub was created and used correctly
            mock_hub_class.assert_called_once_with("mock_device")
            mock_hub.connect.assert_called_once()

            assert mock_hub.run.call_count == 2
            mock_hub.run.assert_called_with(temp_path, wait=True)
            mock_hub.download.assert_called_once_with(temp_path)
            mock_hub.start_user_program.assert_called_once()
            mock_hub._wait_for_user_program_stop.assert_called_once()

            assert mock_selector.call_count == 4
            mock_hub.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stay_connected_menu_change_target_file(self):
        """Test the change target file option."""

        async def passthrough_awaitable(awaitable):
            return await awaitable

        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()
        mock_hub.connect = AsyncMock()
        mock_hub.race_disconnect = mock_hub.race_power_button_press = AsyncMock(
            side_effect=passthrough_awaitable
        )
        mock_hub.download = AsyncMock()

        # create a mock questionary menu
        mock_menu = AsyncMock()
        mock_menu.ask_async.side_effect = [
            "Change Target File",
            "Recompile and Run",
            "Exit",
        ]

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            new_target_file = stack.enter_context(
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)
            new_target_file.write("print('test')")
            new_path = new_target_file.name
            stack.callback(os.unlink, new_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=True,
            )

            stack.enter_context(
                patch("pybricksdev.ble.find_device", return_value="mock_device")
            )
            mock_selector = stack.enter_context(
                patch("questionary.select", return_value=mock_menu)
            )
            mock_file_selector = stack.enter_context(patch("questionary.path"))
            path_obj = AsyncMock()
            path_obj.ask_async = AsyncMock(return_value=new_path)
            mock_file_selector.return_value = path_obj

            # Run the command
            run_cmd = Run()
            await run_cmd.stay_connected_menu(mock_hub, args)

            assert mock_selector.call_count == 3
            mock_file_selector.assert_called_once()
            mock_hub.download.assert_called_once_with(new_path)
            mock_hub.run.assert_called_once_with(new_path, wait=True)

    @pytest.mark.asyncio
    async def test_stay_connected_menu_interruptions(self):
        """Test the stay_connected_menu being interrupted by a power button press or hub disconnect."""
        mock_menu_call_count = 0

        # simulates the hub disconnecting on the first call,
        async def mock_race_disconnect(awaitable):
            task = asyncio.create_task(awaitable)
            try:
                if mock_menu_call_count == 1:
                    await asyncio.sleep(0.01)
                    task.cancel()
                    raise HubDisconnectError("hub disconnected")
                return await task
            except BaseException:
                await asyncio.sleep(0.01)
                task.cancel()
                raise

        # simulate the power button being pressed on the second call
        async def mock_race_power_button_press(awaitable):
            task = asyncio.create_task(awaitable)
            try:
                if mock_menu_call_count == 2:
                    await asyncio.sleep(0.01)
                    task.cancel()
                    raise HubPowerButtonPressedError("power button pressed")
                return await task
            except BaseException:
                await asyncio.sleep(0.01)
                task.cancel()
                raise

        # should be called but cancelled twice, returning "Recompile and Run" the third time
        async def mock_menu_function():
            nonlocal mock_menu_call_count
            mock_menu_call_count += 1
            if mock_menu_call_count <= 3:
                return "Recompile and Run"
            else:
                return "Exit"

        # Create a mock hub
        mock_hub = AsyncMock()
        mock_hub.run = AsyncMock()
        mock_hub.connect = AsyncMock()
        mock_hub.disconnect = AsyncMock()
        mock_hub.race_disconnect = AsyncMock(
            side_effect=mock_race_disconnect,
        )
        mock_hub.race_power_button_press = AsyncMock(
            side_effect=mock_race_power_button_press,
        )
        mock_hub._wait_for_power_button_release = AsyncMock()
        mock_hub._wait_for_user_program_stop = AsyncMock()
        # create a mock questionary menu
        mock_menu = AsyncMock()
        mock_menu.ask_async.side_effect = mock_menu_function

        # create a mock confirmation menu to reconnect to the hub
        mock_confirm_menu = AsyncMock()
        mock_confirm_menu.ask_async.return_value = True

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=True,
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
            mock_selector = stack.enter_context(
                patch("questionary.select", return_value=mock_menu)
            )
            mock_confirm = stack.enter_context(
                patch("questionary.confirm", return_value=mock_confirm_menu)
            )

            # Run the command
            run_cmd = Run()
            await run_cmd.stay_connected_menu(mock_hub, args)

            assert mock_selector.call_count == 4
            # a confirmation menu should be triggered and the hub should be re-instantiated upon a HubDisconnectError
            mock_confirm.assert_called_once()
            mock_hub_class.assert_called_once()
            mock_hub.connect.assert_called_once()

            # these functions should be triggered upon a HubPowerButtonPressedError
            mock_hub._wait_for_power_button_release.assert_called_once()
            mock_hub._wait_for_user_program_stop.assert_called_once()

            # this should only be called once because the menu was canceled the first two times it was called
            mock_hub.run.assert_called_once_with(temp_path, wait=True)

    @pytest.mark.asyncio
    async def test_stay_connected_menu_run_stored(self):
        """Test that the run_stored program option doesn't call an inaccessible method on an old hub."""

        async def passthrough_awaitable(awaitable):
            return await awaitable

        # Create a mock hub
        old_mock_hub = AsyncMock()

        # simulate an old hub that can't handle the run_stored_program option
        old_mock_hub.fw_version = Version("3.2.0-beta.3")
        old_mock_hub.run = AsyncMock()
        old_mock_hub.connect = AsyncMock()
        old_mock_hub.start_user_program = AsyncMock()
        old_mock_hub.race_disconnect = old_mock_hub.race_power_button_press = AsyncMock(
            side_effect=passthrough_awaitable
        )

        # create a mock questionary menu
        mock_selector = AsyncMock()
        mock_selector.ask_async.side_effect = [
            "Run Stored Program",
            "Exit",
        ]

        # Set up mocks using ExitStack
        with contextlib.ExitStack() as stack:
            # Create and manage temporary file

            # Create args
            args = argparse.Namespace(
                conntype="ble",
                file=stack.enter_context(
                    tempfile.NamedTemporaryFile(
                        suffix=".py", mode="w+", delete=False, encoding="utf-8"
                    )
                ),
                name="MyHub",
                start=True,
                wait=True,
                stay_connected=True,
            )

            stack.enter_context(patch("questionary.select", return_value=mock_selector))

            # Run the command
            run_cmd = Run()
            await run_cmd.stay_connected_menu(old_mock_hub, args)

            old_mock_hub.start_user_program.assert_not_called()
            old_mock_hub._wait_for_user_program_stop.assert_not_called()


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
                tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w+", delete=False, encoding="utf-8"
                )
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Create args
            args = argparse.Namespace(
                file=stack.enter_context(open(temp_path, "r", encoding="utf-8")),
                abi=6,
                bin=False,
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
                bin=False,
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
