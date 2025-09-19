# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for async file I/O operations."""

import asyncio
import os
import stat
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest

import aiofiles

from adafmt.async_file_io import (
    buffered_read,
    buffered_write,
    atomic_write_async,
    file_exists_async,
    get_file_size_async
)


class TestBufferedRead:
    """Test buffered async reading."""
    
    @pytest.mark.asyncio
    async def test_read_normal_file(self, tmp_path):
        """Test reading a normal text file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello\nWorld\n" * 100
        test_file.write_text(test_content)
        
        # Read with buffering
        content = await buffered_read(test_file, buffer_size=64)
        
        assert content == test_content
    
    @pytest.mark.asyncio
    async def test_read_empty_file(self, tmp_path):
        """Test reading an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()
        
        content = await buffered_read(test_file)
        assert content == ""
    
    @pytest.mark.asyncio
    async def test_read_large_file(self, tmp_path):
        """Test reading a large file with small buffer."""
        test_file = tmp_path / "large.txt"
        # Create 1MB file
        test_content = "x" * (1024 * 1024)
        test_file.write_text(test_content)
        
        # Read with small buffer
        content = await buffered_read(test_file, buffer_size=1024)
        
        assert content == test_content
        assert len(content) == 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await buffered_read("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_read_with_encoding(self, tmp_path):
        """Test reading with specific encoding."""
        test_file = tmp_path / "utf16.txt"
        test_content = "Hello 世界"
        test_file.write_text(test_content, encoding='utf-16')
        
        content = await buffered_read(test_file, encoding='utf-16')
        assert content == test_content
    
    @pytest.mark.asyncio
    async def test_read_permission_error(self, tmp_path):
        """Test reading a file without permissions."""
        test_file = tmp_path / "noperm.txt"
        test_file.write_text("secret")
        
        # Remove read permissions (Unix only)
        if hasattr(os, 'chmod'):
            os.chmod(test_file, 0o000)
            
            try:
                with pytest.raises(PermissionError):
                    await buffered_read(test_file)
            finally:
                # Restore permissions for cleanup
                os.chmod(test_file, 0o644)


class TestBufferedWrite:
    """Test buffered async writing."""
    
    @pytest.mark.asyncio
    async def test_write_normal_file(self, tmp_path):
        """Test writing a normal text file."""
        test_file = tmp_path / "output.txt"
        test_content = "Hello\nWorld\n"
        
        await buffered_write(test_file, test_content)
        
        assert test_file.exists()
        assert test_file.read_text() == test_content
    
    @pytest.mark.asyncio
    async def test_write_large_content(self, tmp_path):
        """Test writing large content with buffering."""
        test_file = tmp_path / "large_output.txt"
        # 1MB of content
        test_content = "x" * (1024 * 1024)
        
        await buffered_write(test_file, test_content, buffer_size=4096)
        
        assert test_file.read_text() == test_content
    
    @pytest.mark.asyncio
    async def test_write_overwrites_existing(self, tmp_path):
        """Test that write overwrites existing file."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("old content")
        
        new_content = "new content"
        await buffered_write(test_file, new_content)
        
        assert test_file.read_text() == new_content
    
    @pytest.mark.asyncio
    async def test_write_creates_file(self, tmp_path):
        """Test writing creates file if it doesn't exist."""
        test_file = tmp_path / "new.txt"
        assert not test_file.exists()
        
        await buffered_write(test_file, "content")
        
        assert test_file.exists()
        assert test_file.read_text() == "content"
    
    @pytest.mark.asyncio
    async def test_write_with_encoding(self, tmp_path):
        """Test writing with specific encoding."""
        test_file = tmp_path / "utf16_out.txt"
        test_content = "Hello 世界"
        
        await buffered_write(test_file, test_content, encoding='utf-16')
        
        assert test_file.read_text(encoding='utf-16') == test_content
    
    @pytest.mark.asyncio
    async def test_write_empty_content(self, tmp_path):
        """Test writing empty content."""
        test_file = tmp_path / "empty_out.txt"
        
        await buffered_write(test_file, "")
        
        assert test_file.exists()
        assert test_file.read_text() == ""


class TestAtomicWrite:
    """Test atomic file writing."""
    
    @pytest.mark.asyncio
    async def test_atomic_write_creates_file(self, tmp_path):
        """Test atomic write creates new file."""
        test_file = tmp_path / "atomic.txt"
        content = "atomic content"
        
        await atomic_write_async(test_file, content)
        
        assert test_file.exists()
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_atomic_write_replaces_existing(self, tmp_path):
        """Test atomic write replaces existing file."""
        test_file = tmp_path / "replace.txt"
        test_file.write_text("old content")
        
        new_content = "new atomic content"
        await atomic_write_async(test_file, new_content)
        
        assert test_file.read_text() == new_content
    
    @pytest.mark.asyncio
    async def test_atomic_write_preserves_on_error(self, tmp_path):
        """Test atomic write preserves original on error."""
        test_file = tmp_path / "preserve.txt"
        original_content = "original"
        test_file.write_text(original_content)
        
        # Mock to cause error during write
        with patch('adafmt.async_file_io.buffered_write', side_effect=OSError("Write failed")):
            with pytest.raises(OSError):
                await atomic_write_async(test_file, "new content")
        
        # Original file should be unchanged
        assert test_file.read_text() == original_content
    
    @pytest.mark.asyncio
    async def test_atomic_write_cleans_up_temp_file(self, tmp_path):
        """Test temp file cleanup on error."""
        test_file = tmp_path / "cleanup.txt"
        
        # Track temp files created
        temp_files = []
        original_mkstemp = os.open
        
        def track_mkstemp(*args, **kwargs):
            result = original_mkstemp(*args, **kwargs)
            if args and 'tmp' in str(args[0]):
                temp_files.append(args[0])
            return result
        
        with patch('os.open', side_effect=track_mkstemp):
            with patch('adafmt.async_file_io.buffered_write', side_effect=OSError("Write failed")):
                with pytest.raises(OSError):
                    await atomic_write_async(test_file, "content")
        
        # No temp files should remain
        for temp_file in temp_files:
            assert not Path(temp_file).exists()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(os.name == 'nt', reason="Unix permissions test")
    async def test_atomic_write_sets_permissions(self, tmp_path):
        """Test atomic write sets file permissions."""
        test_file = tmp_path / "perms.txt"
        
        await atomic_write_async(test_file, "content", mode=0o600)
        
        # Check permissions
        file_stat = test_file.stat()
        assert stat.S_IMODE(file_stat.st_mode) == 0o600
    
    @pytest.mark.asyncio
    async def test_atomic_write_windows_handling(self, tmp_path):
        """Test atomic write handles Windows correctly."""
        test_file = tmp_path / "windows.txt"
        test_file.write_text("existing")
        
        # Just verify atomic write works on current platform
        await atomic_write_async(test_file, "new content")
        assert test_file.read_text() == "new content"


class TestFileExists:
    """Test async file existence checking."""
    
    @pytest.mark.asyncio
    async def test_exists_for_existing_file(self, tmp_path):
        """Test exists returns True for existing file."""
        test_file = tmp_path / "exists.txt"
        test_file.touch()
        
        assert await file_exists_async(test_file) is True
    
    @pytest.mark.asyncio
    async def test_exists_for_nonexistent_file(self):
        """Test exists returns False for nonexistent file."""
        assert await file_exists_async("/nonexistent/file.txt") is False
    
    @pytest.mark.asyncio
    async def test_exists_for_directory(self, tmp_path):
        """Test exists returns True for directory."""
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()
        
        assert await file_exists_async(test_dir) is True
    
    @pytest.mark.asyncio
    async def test_exists_handles_permission_error(self, tmp_path):
        """Test exists handles permission errors gracefully."""
        with patch('aiofiles.os.stat', side_effect=PermissionError()):
            assert await file_exists_async(tmp_path / "file.txt") is False


class TestFileSize:
    """Test async file size retrieval."""
    
    @pytest.mark.asyncio
    async def test_size_of_empty_file(self, tmp_path):
        """Test size of empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()
        
        size = await get_file_size_async(test_file)
        assert size == 0
    
    @pytest.mark.asyncio
    async def test_size_of_normal_file(self, tmp_path):
        """Test size of file with content."""
        test_file = tmp_path / "sized.txt"
        content = "Hello, World!"
        test_file.write_text(content)
        
        size = await get_file_size_async(test_file)
        assert size == len(content.encode('utf-8'))
    
    @pytest.mark.asyncio
    async def test_size_of_large_file(self, tmp_path):
        """Test size of large file."""
        test_file = tmp_path / "large.txt"
        # 1MB file
        content = "x" * (1024 * 1024)
        test_file.write_text(content)
        
        size = await get_file_size_async(test_file)
        assert size == 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_size_of_nonexistent_file(self):
        """Test size raises error for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            await get_file_size_async("/nonexistent/file.txt")