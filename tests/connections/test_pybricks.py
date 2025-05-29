"""Tests for the pybricks connection module."""

import asyncio
import contextlib
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from reactivex.subject import Subject

from pybricksdev.ble.pybricks import PYBRICKS_COMMAND_EVENT_UUID
from pybricksdev.connections.pybricks import (
    ConnectionState,
    HubCapabilityFlag,
    HubKind,
    PybricksHubBLE,
    PybricksHubUSB,
    StatusFlag,
)
from pybricksdev.usb.pybricks import PybricksUsbOutEpMessageType


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


class TestPybricksHubUSB:
    """Tests for the PybricksHubUSB class functionality."""

    @pytest.mark.asyncio
    async def test_pybricks_hub_usb_write_gatt_char_disconnect(self):
        """Test write_gatt_char when a disconnect event occurs."""
        hub = PybricksHubUSB(MagicMock())

        hub._ep_out = MagicMock()
        # Simulate _response_queue.get() blocking indefinitely
        hub._response_queue = AsyncMock()
        hub._response_queue.get = AsyncMock(side_effect=asyncio.Event().wait)

        mock_observable = MagicMock(
            spec=Subject
        )  # Using Subject as a base for mock spec
        disconnect_callback_handler = None

        def mock_subscribe_side_effect(on_next_callback, *args, **kwargs):
            nonlocal disconnect_callback_handler
            disconnect_callback_handler = on_next_callback
            mock_subscription = MagicMock()
            mock_subscription.dispose = MagicMock()
            return mock_subscription

        mock_observable.subscribe = MagicMock(side_effect=mock_subscribe_side_effect)
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub.connection_state_observable = mock_observable

        async def trigger_disconnect_event():
            await asyncio.sleep(0.05)
            assert (
                disconnect_callback_handler is not None
            ), "Subscribe was not called by race_disconnect"
            disconnect_callback_handler(ConnectionState.DISCONNECTED)

        with pytest.raises(RuntimeError, match="disconnected during operation"):
            await asyncio.gather(
                hub.write_gatt_char(PYBRICKS_COMMAND_EVENT_UUID, b"test_data", True),
                trigger_disconnect_event(),
            )

        hub._ep_out.write.assert_called_once_with(
            bytes([PybricksUsbOutEpMessageType.COMMAND]) + b"test_data"
        )

    @pytest.mark.asyncio
    async def test_pybricks_hub_usb_write_gatt_char_timeout(self):
        """Test write_gatt_char when a timeout occurs."""
        hub = PybricksHubUSB(MagicMock())

        hub._ep_out = MagicMock()
        hub._response_queue = AsyncMock()
        # Make _response_queue.get() block indefinitely
        hub._response_queue.get = AsyncMock(side_effect=asyncio.Event().wait)

        mock_observable = MagicMock(spec=Subject)

        def mock_subscribe_side_effect(on_next_callback, *args, **kwargs):
            mock_subscription = MagicMock()
            mock_subscription.dispose = MagicMock()
            return mock_subscription

        mock_observable.subscribe = MagicMock(side_effect=mock_subscribe_side_effect)
        type(hub.connection_state_observable).value = PropertyMock(
            return_value=ConnectionState.CONNECTED
        )
        hub.connection_state_observable = mock_observable

        # The method has a hardcoded timeout of 5.0s.
        # We can patch asyncio.wait_for to speed up the test.
        with patch(
            "asyncio.wait_for", side_effect=asyncio.TimeoutError("Test-induced timeout")
        ):
            with pytest.raises(
                asyncio.TimeoutError, match="Timeout waiting for USB response"
            ):
                await hub.write_gatt_char(
                    PYBRICKS_COMMAND_EVENT_UUID, b"test_data", True
                )

        hub._ep_out.write.assert_called_once_with(
            bytes([PybricksUsbOutEpMessageType.COMMAND]) + b"test_data"
        )
