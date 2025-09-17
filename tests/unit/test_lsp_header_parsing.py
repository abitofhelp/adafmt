# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Tests for robust LSP header parsing."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from adafmt.als_client import ALSClient


class MockStreamReader:
    """Mock for asyncio StreamReader."""
    
    def __init__(self, data_sequence):
        """Initialize with a sequence of data to return from readline/readexactly."""
        self.data_sequence = data_sequence
        self.index = 0
        
    async def readline(self):
        """Return next line from sequence."""
        if self.index < len(self.data_sequence):
            data = self.data_sequence[self.index]
            self.index += 1
            return data
        return b''  # EOF
        
    async def readexactly(self, n):
        """Return next data from sequence."""
        if self.index < len(self.data_sequence):
            data = self.data_sequence[self.index]
            self.index += 1
            return data
        raise asyncio.IncompleteReadError(b'', n)


class TestLSPHeaderParsing:
    """Test robust LSP header parsing in ALS client."""
    
    @pytest.mark.asyncio
    async def test_standard_header_crlf(self):
        """Test parsing standard LSP headers with CRLF line endings."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"data": "test"}}
        response_bytes = json.dumps(response).encode('utf-8')
        
        mock_data = [
            b'Content-Length: ' + str(len(response_bytes)).encode() + b'\r\n',
            b'\r\n',  # Empty line
            response_bytes
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        future = asyncio.Future()
        client._pending = {"1": future}
        
        # Run reader loop in background
        reader_task = asyncio.create_task(client._reader_loop())
        
        # Give it time to process
        await asyncio.sleep(0.1)
        
        # Check the future was resolved
        assert future.done()
        assert future.result() == {"data": "test"}
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_header_parsing_lf_only(self):
        """Test parsing headers with LF-only line endings."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        response_bytes = json.dumps(response).encode('utf-8')
        
        mock_data = [
            b'Content-Length: ' + str(len(response_bytes)).encode() + b'\n',
            b'\n',  # Empty line
            response_bytes
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        future = asyncio.Future()
        client._pending = {"1": future}
        
        reader_task = asyncio.create_task(client._reader_loop())
        await asyncio.sleep(0.1)
        
        assert future.done()
        assert future.result() == {"ok": True}
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_multiple_headers(self):
        """Test parsing multiple headers including unknown ones."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {}}
        response_bytes = json.dumps(response).encode('utf-8')
        
        mock_data = [
            b'Content-Length: ' + str(len(response_bytes)).encode() + b'\r\n',
            b'Content-Type: application/json\r\n',  # Extra header
            b'X-Custom-Header: value\r\n',  # Unknown header
            b'\r\n',
            response_bytes
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        future = asyncio.Future()
        client._pending = {"1": future}
        client._stderr_lines = []
        
        reader_task = asyncio.create_task(client._reader_loop())
        await asyncio.sleep(0.1)
        
        assert future.done()
        assert future.result() == {}
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_malformed_header(self):
        """Test handling of headers without colons."""
        response = {"jsonrpc": "2.0", "id": 1, "result": {}}
        response_bytes = json.dumps(response).encode('utf-8')
        
        mock_data = [
            b'HeaderWithoutColon\r\n',  # Header without colon - will be ignored
            b'Content-Length: ' + str(len(response_bytes)).encode() + b'\r\n',
            b'\r\n',
            response_bytes
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        future = asyncio.Future()
        client._pending = {"1": future}
        client._stderr_lines = []
        
        reader_task = asyncio.create_task(client._reader_loop())
        await asyncio.sleep(0.1)
        
        # Should still process the message
        assert future.done()
        assert future.result() == {}
        
        # Headers without colons are silently ignored per LSP spec
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_missing_content_length(self):
        """Test handling when Content-Length header is missing."""
        mock_data = [
            b'Content-Type: application/json\r\n',  # No Content-Length
            b'\r\n',
            b'{"some": "data"}'  # This won't be read
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        client._stderr_lines = []
        
        reader_task = asyncio.create_task(client._reader_loop())
        await asyncio.sleep(0.1)
        
        # Should log the missing header
        assert any("Missing Content-Length" in line for line in client._stderr_lines)
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_invalid_content_length(self):
        """Test handling of non-numeric Content-Length."""
        mock_data = [
            b'Content-Length: invalid\r\n',
            b'\r\n'
        ]
        
        client = ALSClient(project_file=Path("test.gpr"))
        client.process = MagicMock()
        client.process.stdout = MockStreamReader(mock_data)
        client._stderr_lines = []
        
        reader_task = asyncio.create_task(client._reader_loop())
        await asyncio.sleep(0.1)
        
        # Should log the invalid content length
        assert any("Invalid Content-Length" in line for line in client._stderr_lines)
        
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass