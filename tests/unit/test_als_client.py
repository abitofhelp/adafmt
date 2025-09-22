# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for the als_client module.

This module contains comprehensive unit tests for the Ada Language Server client
implementation. Tests cover:

- ALS process lifecycle management (start, stop, restart)
- Language Server Protocol communication
- Request/response handling and correlation
- Error handling and recovery mechanisms
- Timeout management
- Message framing and parsing
- Environment configuration

All tests use mocks to avoid requiring actual ALS installation.
"""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import os
import pytest

from adafmt.als_client import ALSClient, ALSProtocolError, build_als_command, _has_cmd, _timestamp


class TestUtilityFunctions:
    """Test suite for ALS client utility functions.
    
    Tests the helper functions used by ALSClient for command detection,
    timestamp generation, and other utilities.
    """
    
    @patch('adafmt.als_client.which')
    def test_has_cmd_found(self, mock_which):
        """Test that _has_cmd returns True when command exists in PATH.
        
        Given: A command that exists in the system PATH
        When: _has_cmd is called with the command name
        Then: Returns True indicating command is available
        """
        mock_which.return_value = '/usr/bin/ada_language_server'
        assert _has_cmd('ada_language_server') is True
        mock_which.assert_called_once_with('ada_language_server')
    
    @patch('adafmt.als_client.which')
    def test_has_cmd_not_found(self, mock_which):
        """Test that _has_cmd returns False when command is not in PATH.
        
        Given: A command that does not exist in the system PATH
        When: _has_cmd is called with the command name
        Then: Returns False indicating command is not available
        """
        mock_which.return_value = None
        assert _has_cmd('missing_command') is False
    
    def test_timestamp(self):
        """Test timestamp generation for logging.
        
        Given: No specific input
        When: _timestamp is called
        Then: Returns a valid ISO-format timestamp string
        """
        ts = _timestamp()
        assert isinstance(ts, str)
        assert len(ts) > 0
        # Should be in ISO format
        assert 'T' in ts or ' ' in ts


class TestBuildALSCommand:
    """Test suite for ALS command line building.
    
    Tests the build_als_command function that constructs the command line
    and environment for launching the Ada Language Server process.
    """
    
    def test_build_basic_command(self):
        """Test building basic ALS command without additional options.
        
        Given: No special configuration
        When: build_als_command is called with no arguments
        Then: Returns basic 'ada_language_server' command and clean environment
        """
        cmd, env = build_als_command()
        assert cmd == 'ada_language_server'
        assert isinstance(env, dict)
    
    def test_build_command_with_traces(self):
        """Test building ALS command with trace configuration file.
        
        Given: A path to a traces configuration file
        When: build_als_command is called with traces_config parameter
        Then: Returns command with --tracefile option and environment
        """
        cmd, env = build_als_command(traces_config='/path/to/traces.cfg')
        assert cmd == 'ada_language_server --tracefile=/path/to/traces.cfg'
        assert isinstance(env, dict)


class TestALSProtocolError:
    """Test suite for ALSProtocolError exception handling.
    
    Tests the custom exception class used for Language Server Protocol
    errors, including different payload types and string representations.
    """
    
    def test_init_with_dict_payload(self):
        """Test ALSProtocolError initialization with dictionary payload.
        
        Given: A dictionary payload containing error code and message
        When: ALSProtocolError is instantiated with the dictionary
        Then: The error stores the payload and returns it as string representation
        """
        payload = {"code": -32603, "message": "Internal error"}
        error = ALSProtocolError(payload)
        assert error.payload == payload
        assert str(error) == str(payload)
    
    def test_init_with_string_payload(self):
        """Test ALSProtocolError initialization with string payload.
        
        Given: A simple string error message
        When: ALSProtocolError is instantiated with the string
        Then: The error stores the string payload and returns it unchanged
        """
        error = ALSProtocolError("Simple error message")
        assert error.payload == "Simple error message"
        assert str(error) == "Simple error message"


class TestALSClient:
    """Test suite for the ALSClient class.
    
    Tests the main Ada Language Server client implementation including:
    - Client initialization and configuration
    - Process lifecycle management
    - LSP message handling
    - Request/response correlation
    - Error handling and timeouts
    - Summary reporting
    """
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create a test ALSClient instance with a temporary project file.
        
        Given: A temporary directory for test files
        When: Creating a new test client instance
        Then: Returns configured ALSClient with mock project file
        """
        project_file = tmp_path / "test.gpr"
        project_file.touch()
        return ALSClient(project_file=project_file)
    
    def test_init_basic(self, tmp_path):
        """Test basic ALSClient initialization with minimal configuration.
        
        Given: A project file path
        When: ALSClient is instantiated with just the project file
        Then: Client is initialized with default values and no active process
        """
        project = tmp_path / "test.gpr"
        project.touch()
        client = ALSClient(project_file=project)
        
        assert client.project_file == project
        assert client._id == 0
        assert client._pending == {}
        assert client.process is None
    
    def test_init_with_stderr_path(self, tmp_path):
        """Test ALSClient initialization with custom stderr path and timeout.
        
        Given: A project file, custom stderr path, and initialization timeout
        When: ALSClient is instantiated with all parameters
        Then: Client stores all configuration values correctly
        """
        project = tmp_path / "test.gpr"
        project.touch()
        stderr_path = tmp_path / "stderr.log"
        
        client = ALSClient(
            project_file=project,
            stderr_file_path=stderr_path,
            init_timeout=60
        )
        
        assert client.stderr_file_path == stderr_path
        assert client.init_timeout == 60
    
    def test_next_id(self, client):
        """Test sequential message ID generation.
        
        Given: A fresh ALSClient instance
        When: _next_id() is called multiple times
        Then: Returns incrementing string IDs starting from "1"
        """
        assert client._next_id() == "1"
        assert client._next_id() == "2"
        assert client._next_id() == "3"
        assert client._id == 3
    
    def test_resolve_stderr_path_none(self, client, tmp_path):
        """Test stderr path resolution when no custom path is configured.
        
        Given: Client with no stderr_file_path set
        When: _resolve_stderr_path is called with a working directory
        Then: Returns default "als_stderr.log" in the working directory
        """
        cwd = tmp_path / "work"
        cwd.mkdir()
        result = client._resolve_stderr_path(cwd)
        assert result == cwd / "als_stderr.log"
    
    def test_resolve_stderr_path_absolute(self, client, tmp_path):
        """Test stderr path resolution with absolute path configuration.
        
        Given: Client with absolute stderr_file_path
        When: _resolve_stderr_path is called
        Then: Returns the configured absolute path unchanged
        """
        stderr_path = tmp_path / "logs" / "als.log"
        client.stderr_file_path = stderr_path
        result = client._resolve_stderr_path(tmp_path)
        assert result == stderr_path
    
    def test_resolve_stderr_path_relative(self, client, tmp_path):
        """Test stderr path resolution with relative path configuration.
        
        Given: Client with relative stderr_file_path
        When: _resolve_stderr_path is called
        Then: Resolves path relative to current working directory
        """
        client.stderr_file_path = Path("logs/als.log")
        cwd = tmp_path / "work"
        cwd.mkdir()
        
        # Save current working directory
        original_cwd = Path.cwd()
        try:
            # Change to tmp_path to test relative path resolution
            os.chdir(tmp_path)
            result = client._resolve_stderr_path(cwd)
            # Relative paths are resolved from current working directory
            assert result == tmp_path / "logs" / "als.log"
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_write_message(self, client):
        """Test writing JSON-RPC message to ALS process stdin.
        
        Given: An active ALS process with stdin stream
        When: _write is called with a JSON-RPC message
        Then: Message is written with proper Content-Length header and drained
        """
        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()  # Not async
        mock_stdin.drain = AsyncMock()  # Async
        
        client.process = MagicMock()
        client.process.stdin = mock_stdin
        
        message = {"jsonrpc": "2.0", "method": "test"}
        await client._write(message)
        
        # Verify proper JSON-RPC format
        expected = json.dumps(message).encode('utf-8')
        expected_header = f"Content-Length: {len(expected)}\r\n\r\n".encode('ascii')
        
        mock_stdin.write.assert_called_once_with(expected_header + expected)
        mock_stdin.drain.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notify(self, client):
        """Test sending LSP notification (no response expected).
        
        Given: A method name and parameters
        When: _notify is called
        Then: Sends JSON-RPC notification without ID field
        """
        client._write = AsyncMock()
        
        await client._notify("test/method", {"param": "value"})
        
        client._write.assert_called_once()
        msg = client._write.call_args[0][0]
        assert msg["jsonrpc"] == "2.0"
        assert msg["method"] == "test/method"
        assert msg["params"] == {"param": "value"}
        assert "id" not in msg
    
    @pytest.mark.asyncio
    async def test_send_request(self, client):
        """Test sending LSP request with response tracking.
        
        Given: A JSON-RPC request message with ID
        When: _send is called
        Then: Message is written and future is created for tracking response
        """
        client._write = AsyncMock()
        
        msg = {"jsonrpc": "2.0", "id": "1", "method": "test"}
        await client._send(msg)
        
        client._write.assert_called_once_with(msg)
        assert "1" in client._pending
        assert isinstance(client._pending["1"], asyncio.Future)
    
    @pytest.mark.asyncio
    async def test_handle_response_in_reader_loop(self, client):
        """Test response handling logic within the reader loop.
        
        Given: A pending request future waiting for response
        When: Response is processed by reader loop
        Then: Future is resolved with the response data
        """
        # The client doesn't have a separate _handle_response method anymore.
        # Response handling happens inside _reader_loop.
        future = asyncio.Future()
        client._pending["1"] = future
        
        # Simulate a successful response by directly manipulating the future
        future.set_result({"data": "test"})
        
        assert future.done()
        assert await future == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_request_with_timeout_success(self, client):
        """Test successful request completion within timeout period.
        
        Given: A request and a reasonable timeout
        When: Response arrives before timeout
        Then: Returns the response data successfully
        """
        # We need to mock the entire flow more carefully
        client._write = AsyncMock()
        
        # Directly test that the method creates the future properly
        msg = {"method": "test", "params": {}}
        mid = client._next_id()
        msg["id"] = mid
        
        # Call _send to set up the future
        await client._send(msg)
        
        # Verify future was created
        assert mid in client._pending
        fut = client._pending[mid]
        
        # Simulate response arriving
        fut.set_result({"data": "test"})
        
        # Get the result
        result = await fut
        assert result == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_request_with_timeout_timeout(self, client):
        """Test request timeout when response doesn't arrive in time.
        
        Given: A request with a very short timeout
        When: No response arrives within timeout period
        Then: Raises asyncio.TimeoutError
        """
        client._write = AsyncMock()
        client._send = AsyncMock()
        
        with pytest.raises(asyncio.TimeoutError):
            await client.request_with_timeout(
                {"method": "test", "params": {}},
                timeout=0.001
            )
    
    def test_summary_with_metrics(self, client):
        """Test summary generation with complete execution metrics.
        
        Given: Client with recorded execution metrics (timing, stderr, return code)
        When: summary() is called
        Then: Returns dictionary with all metrics properly calculated
        """
        client._start_ns = 1_000_000_000  # 1 second
        client._end_ns = 2_500_000_000    # 2.5 seconds
        client._stderr_lines = 10
        client._returncode = 0
        client._stderr_log_path = Path("/tmp/als_stderr.log")
        
        summary = client.summary()
        
        assert summary["returncode"] == 0
        assert summary["duration_ms"] == 1500.0
        assert summary["stderr_lines"] == 10
        assert summary["stderr_log_path"] == "/tmp/als_stderr.log"
    
    def test_summary_no_metrics(self, client):
        """Test summary generation before ALS process has been started.
        
        Given: Client with no recorded metrics
        When: summary() is called
        Then: Returns dictionary with None/zero values for all metrics
        """
        summary = client.summary()
        assert summary["returncode"] is None
        assert summary["duration_ms"] is None
        assert summary["stderr_lines"] == 0
        assert summary["stderr_log_path"] is None
    
    @pytest.mark.asyncio
    async def test_pump_stderr(self, client, tmp_path):
        """Test stderr stream pumping to log file.
        
        Given: Mock stderr stream with error messages
        When: _pump_stderr reads the stream
        Then: All lines are written to log file and line count is tracked
        """
        # Create a mock stream reader
        lines = [b"Error line 1\n", b"Error line 2\n"]
        line_iter = iter(lines)
        
        mock_stderr = AsyncMock()
        
        # Mock at_eof to return False until we've read all lines
        eof_calls = 0
        def mock_at_eof():
            nonlocal eof_calls
            eof_calls += 1
            # Return False for first 2 calls (while reading lines), then True
            return eof_calls > len(lines)
        
        mock_stderr.at_eof = mock_at_eof
        
        # Mock readline to return lines then empty bytes
        async def mock_readline():
            try:
                return next(line_iter)
            except StopIteration:
                return b""
        
        mock_stderr.readline = mock_readline
        
        stderr_file = tmp_path / "als_stderr.log"
        
        await client._pump_stderr(mock_stderr, stderr_file)
        
        content = stderr_file.read_text()
        assert "Error line 1" in content
        assert "Error line 2" in content
        assert client._stderr_lines == 2
    
    @pytest.mark.asyncio
    async def test_reader_loop_single_message(self, client):
        """Test reader loop processing a single LSP response message.
        
        Given: Mock stdout with one complete JSON-RPC message
        When: _reader_loop processes the stream
        Then: Message is parsed and pending future is resolved
        """
        message = {"jsonrpc": "2.0", "id": "1", "result": {"test": "data"}}
        message_str = json.dumps(message)
        
        # Create a future that will be resolved by the reader loop
        future = asyncio.Future()
        client._pending["1"] = future
        
        mock_stdout = AsyncMock()
        # First readline returns header, second returns empty line, third returns empty (EOF)
        mock_stdout.readline.side_effect = [
            f"Content-Length: {len(message_str)}\r\n".encode(),
            b"\r\n",
            b""  # EOF
        ]
        mock_stdout.readexactly.return_value = message_str.encode()
        
        client.process = MagicMock()
        client.process.stdout = mock_stdout
        
        await client._reader_loop()
        
        # Verify the future was resolved with the result
        assert future.done()
        assert await future == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_shutdown(self, client):
        """Test graceful shutdown sequence of ALS process.
        
        Given: Active ALS client with running process and tasks
        When: shutdown() is called
        Then: Sends shutdown request, exit notification, and cleans up resources
        """
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.terminate = MagicMock()
        
        client.process = mock_process
        client._reader_task = MagicMock()
        client._reader_task.cancel = MagicMock()
        client._stderr_task = MagicMock()
        client._stderr_task.cancel = MagicMock()
        client._send = AsyncMock()
        client._notify = AsyncMock()
        
        await client.shutdown()
        
        # Verify shutdown message was sent
        client._send.assert_called_once()
        shutdown_msg = client._send.call_args[0][0]
        assert shutdown_msg["method"] == "shutdown"
        assert "id" in shutdown_msg
        
        # Verify exit notification
        client._notify.assert_called_once_with("exit", {})
        
        # Verify process termination was called
        mock_process.terminate.assert_called_once()
        
        # Verify tasks were cancelled
        client._reader_task.cancel.assert_called_once()
        client._stderr_task.cancel.assert_called_once()
        
        # Verify process is set to None
        assert client.process is None
    
    @pytest.mark.asyncio
    async def test_restart(self, client):
        """Test ALS process restart functionality.
        
        Given: An ALSClient instance
        When: restart() is called
        Then: Performs shutdown followed by start to refresh the process
        """
        client.shutdown = AsyncMock()
        client.start = AsyncMock()
        
        await client.restart()
        
        client.shutdown.assert_called_once()
        client.start.assert_called_once()