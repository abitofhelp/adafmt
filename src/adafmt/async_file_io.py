# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Asynchronous file I/O operations with buffering."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Union

import aiofiles
import aiofiles.os


async def buffered_read(
    path: Union[str, Path],
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> str:
    """Read file asynchronously with buffering.
    
    Args:
        path: Path to file to read
        buffer_size: Size of read buffer in bytes
        encoding: Text encoding
        
    Returns:
        File contents as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't readable
        UnicodeDecodeError: If file encoding is invalid
    """
    path = Path(path)
    
    chunks = []
    async with aiofiles.open(path, mode='r', encoding=encoding) as f:
        while True:
            chunk = await f.read(buffer_size)
            if not chunk:
                break
            chunks.append(chunk)
    
    return ''.join(chunks)


async def buffered_write(
    path: Union[str, Path],
    content: str,
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> None:
    """Write file asynchronously with buffering.
    
    Args:
        path: Path to file to write
        content: Content to write
        buffer_size: Size of write buffer in bytes
        encoding: Text encoding
        
    Raises:
        PermissionError: If file isn't writable
        OSError: If disk is full or other OS error
    """
    path = Path(path)
    
    async with aiofiles.open(path, mode='w', encoding=encoding) as f:
        # Write in chunks for large content
        for i in range(0, len(content), buffer_size):
            chunk = content[i:i + buffer_size]
            await f.write(chunk)
        await f.flush()


async def atomic_write_async(
    path: Union[str, Path],
    content: str,
    mode: int = 0o644,
    encoding: str = 'utf-8'
) -> None:
    """Atomically write file using temp file + rename.
    
    Args:
        path: Path to file to write
        content: Content to write
        mode: Unix file permissions
        encoding: Text encoding
        
    Raises:
        PermissionError: If file isn't writable
        OSError: If disk is full or other OS error
        
    Note:
        This operation is atomic on POSIX systems. On Windows,
        it may briefly remove the target file during rename.
    """
    path = Path(path)
    
    # Create temp file in same directory for atomic rename
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f'.{path.name}.',
        suffix='.tmp'
    )
    
    try:
        # Close the file descriptor - aiofiles will reopen
        os.close(temp_fd)
        
        # Write content to temp file
        await buffered_write(temp_path, content, encoding=encoding)
        
        # Set permissions (Unix only)
        if hasattr(os, 'chmod'):
            try:
                await aiofiles.os.chmod(temp_path, mode)
            except (OSError, AttributeError):
                # Windows or permission error - ignore
                pass
        
        # Atomic rename
        # On Windows, this may briefly remove the target
        if os.name == 'nt' and path.exists():
            # Windows requires target removal
            try:
                await aiofiles.os.remove(path)
            except OSError:
                pass
        
        await aiofiles.os.rename(temp_path, path)
        
    except Exception:
        # Clean up temp file on error
        try:
            if os.path.exists(temp_path):
                await aiofiles.os.remove(temp_path)
        except OSError:
            pass
        raise


async def file_exists_async(path: Union[str, Path]) -> bool:
    """Check if file exists asynchronously.
    
    Args:
        path: Path to check
        
    Returns:
        True if file exists
    """
    try:
        await aiofiles.os.stat(path)
        return True
    except (OSError, FileNotFoundError):
        return False


async def get_file_size_async(path: Union[str, Path]) -> int:
    """Get file size asynchronously.
    
    Args:
        path: Path to file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    stat = await aiofiles.os.stat(path)
    return stat.st_size