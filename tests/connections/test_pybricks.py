"""Tests for the pybricks connection module."""

import asyncio
import contextlib
import os
import tempfile
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from reactivex.subject import Subject

from pybricksdev.connections.pybricks import (
    ConnectionState,
    HubCapabilityFlag,
    HubKind,
    PybricksHubBLE,
    StatusFlag,
)


class TestPybricksHub:
    """Tests for the PybricksHub base class functionality."""

    @pytest.mark.asyncio
    async def test_download_modern_protocol(self):
        """Test downloading with modern protocol and capability flags."""
        hub = PybricksHubBLE("mock_device")
        hub._mpy_abi_version = 6
        hub._client = AsyncMock()
        hub.get_capabilities = AsyncMock(return_value={"pybricks": {"mpy": True}})
        hub.download_user_program = AsyncMock()
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub._capability_flags = HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6

        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            await hub.download(temp_path)
            hub.download_user_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_legacy_firmware(self):
        """Test downloading with legacy firmware."""
        hub = PybricksHubBLE("mock_device")
        hub._mpy_abi_version = None  # Legacy firmware
        hub._client = AsyncMock()
        hub.download_user_program = AsyncMock()
        hub.hub_kind = HubKind.BOOST
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub._capability_flags = HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6

        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            await hub.download(temp_path)
            hub.download_user_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_unsupported_capabilities(self):
        """Test downloading when hub doesn't support required capabilities."""
        hub = PybricksHubBLE("mock_device")
        hub._mpy_abi_version = 6
        hub._client = AsyncMock()
        hub.get_capabilities = AsyncMock(return_value={"pybricks": {"mpy": False}})
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub._capability_flags = 0

        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            with pytest.raises(
                RuntimeError,
                match="Hub is not compatible with any of the supported file formats",
            ):
                await hub.download(temp_path)

    @pytest.mark.asyncio
    async def test_download_compile_error(self):
        """Test handling compilation errors."""
        hub = PybricksHubBLE("mock_device")
        hub._mpy_abi_version = 6
        hub._client = AsyncMock()
        hub.get_capabilities = AsyncMock(return_value={"pybricks": {"mpy": True}})
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub._capability_flags = HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6
        hub._max_user_program_size = 1000  # Set a reasonable size limit

        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test'  # Missing closing parenthesis")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Mock compile_multi_file to raise SyntaxError
            stack.enter_context(
                patch(
                    "pybricksdev.connections.pybricks.compile_multi_file",
                    side_effect=SyntaxError("invalid syntax"),
                )
            )

            with pytest.raises(SyntaxError, match="invalid syntax"):
                await hub.download(temp_path)

    @pytest.mark.asyncio
    async def test_run_modern_protocol(self):
        """Test running a program with modern protocol."""
        hub = PybricksHubBLE("mock_device")
        hub._mpy_abi_version = None  # Use modern protocol
        hub._client = AsyncMock()
        hub.client = AsyncMock()
        hub.get_capabilities = AsyncMock(return_value={"pybricks": {"mpy": True}})
        hub.download_user_program = AsyncMock()
        hub.start_user_program = AsyncMock()
        hub.write_gatt_char = AsyncMock()
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub._capability_flags = HubCapabilityFlag.USER_PROG_MULTI_FILE_MPY6
        hub.hub_kind = HubKind.BOOST

        # Mock the status observable to simulate program start and stop
        status_subject = Subject()
        hub.status_observable = status_subject
        hub._stdout_line_queue = asyncio.Queue()
        hub._enable_line_handler = True

        with contextlib.ExitStack() as stack:
            # Create and manage temporary file
            temp = stack.enter_context(
                tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False)
            )
            temp.write("print('test')")
            temp_path = temp.name
            stack.callback(os.unlink, temp_path)

            # Start the run task
            run_task = asyncio.create_task(hub.run(temp_path))

            # Simulate program start
            await asyncio.sleep(0.1)
            status_subject.on_next(StatusFlag.USER_PROGRAM_RUNNING)

            # Simulate program stop after a short delay
            await asyncio.sleep(0.1)
            status_subject.on_next(0)  # Clear all flags

            # Wait for run task to complete
            await run_task

            # Verify the expected calls were made
            hub.download_user_program.assert_called_once()
            hub.start_user_program.assert_called_once()
