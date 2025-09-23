# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Asynchronous file I/O operations with functional error handling.

All functions return Result types - no exceptions propagate.
"""

import os
import tempfile
from pathlib import Path
from typing import Union

import aiofiles
import aiofiles.os
from returns.result import Failure, Result, Success

from .errors import FileError, file_not_found, permission_denied


async def _buffered_read_internal(
    path: Union[str, Path],
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> str:
    """
    Internal read function that may raise exceptions.
    
    Args:
        path: Path to file to read
        buffer_size: Size of read buffer in bytes
        encoding: Text encoding
        
    Returns:
        str: File contents
        
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


async def buffered_read_safe(
    path: Union[str, Path],
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> Result[str, FileError]:
    """
    Read file with explicit error handling.
    
    Returns:
        Result[str, FileError]: File contents or specific error
    """
    path = Path(path)
    
    try:
        content = await _buffered_read_internal(path, buffer_size, encoding)
        return Success(content)
    except FileNotFoundError:
        return Failure(file_not_found(path))
    except PermissionError:
        return Failure(permission_denied(path, "read"))
    except UnicodeDecodeError as e:
        return Failure(FileError(
            message=f"Encoding error reading {path}: {e}",
            path=path,
            operation="read",
            original_error=str(e)
        ))
    except Exception as e:
        return Failure(FileError(
            message=f"Failed to read {path}: {e}",
            path=path,
            operation="read",
            original_error=str(e)
        ))


async def _buffered_write_internal(
    path: Union[str, Path],
    content: str,
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> None:
    """
    Internal write function that may raise exceptions.
    
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


async def buffered_write_safe(
    path: Union[str, Path],
    content: str,
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> Result[None, FileError]:
    """
    Write file with explicit error handling.
    
    Returns:
        Result[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    try:
        await _buffered_write_internal(path, content, buffer_size, encoding)
        return Success(None)
    except PermissionError:
        return Failure(permission_denied(path, "write"))
    except OSError as e:
        return Failure(FileError(
            message=f"OS error writing {path}: {e}",
            path=path,
            operation="write",
            original_error=str(e)
        ))
    except Exception as e:
        return Failure(FileError(
            message=f"Failed to write {path}: {e}",
            path=path,
            operation="write",
            original_error=str(e)
        ))


async def atomic_write_async_safe(
    path: Union[str, Path],
    content: str,
    mode: int = 0o644,
    encoding: str = 'utf-8'
) -> Result[None, FileError]:
    """
    Atomically write file using temp file + rename.
    
    Args:
        path: Path to file to write
        content: Content to write
        mode: Unix file permissions
        encoding: Text encoding
        
    Returns:
        Result[None, FileError]: Success or error
        
    Note:
        This operation is atomic on POSIX systems. On Windows,
        it may briefly remove the target file during rename.
    """
    path = Path(path)
    temp_path = None
    
    try:
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=path.parent,
            prefix=f'.{path.name}.',
            suffix='.tmp'
        )
        temp_path = Path(temp_path_str)
        
        # Close the file descriptor - aiofiles will reopen
        os.close(temp_fd)
        
        # Write content to temp file
        write_result = await buffered_write_safe(temp_path, content, encoding=encoding)
        if isinstance(write_result, Failure):
            return write_result
        
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
        return Success(None)
        
    except PermissionError:
        return Failure(permission_denied(path, "write"))
    except OSError as e:
        return Failure(FileError(
            message=f"OS error during atomic write to {path}: {e}",
            path=path,
            operation="write",
            original_error=str(e)
        ))
    except Exception as e:
        return Failure(FileError(
            message=f"Failed to atomically write {path}: {e}",
            path=path,
            operation="write",
            original_error=str(e)
        ))
    finally:
        # Clean up temp file on error
        if temp_path and os.path.exists(temp_path):
            try:
                await aiofiles.os.remove(temp_path)
            except OSError:
                pass


async def file_exists_async(path: Union[str, Path]) -> bool:
    """
    Check if file exists asynchronously.
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if exists, False if not
        
    Note: This function never fails - it returns False for any error.
    """
    try:
        await aiofiles.os.stat(path)
        return True
    except (OSError, FileNotFoundError):
        return False


async def get_file_size_async_safe(path: Union[str, Path]) -> Result[int, FileError]:
    """
    Get file size asynchronously.
    
    Args:
        path: Path to file
        
    Returns:
        Result[int, FileError]: File size in bytes or error
    """
    path = Path(path)
    
    try:
        stat = await aiofiles.os.stat(path)
        return Success(stat.st_size)
    except FileNotFoundError:
        return Failure(file_not_found(path))
    except PermissionError:
        return Failure(permission_denied(path, "stat"))
    except Exception as e:
        return Failure(FileError(
            message=f"Failed to get size of {path}: {e}",
            path=path,
            operation="stat",
            original_error=str(e)
        ))


# Backward compatibility - keep old function signatures
# These raise exceptions for compatibility with existing code
async def buffered_read(
    path: Union[str, Path],
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> str:
    """
    Legacy version that raises exceptions.
    
    DEPRECATED: Use buffered_read_safe instead.
    """
    result = await buffered_read_safe(path, buffer_size, encoding)
    if isinstance(result, Success):
        return result.unwrap()
    else:
        error = result.failure()
        if error.not_found:
            raise FileNotFoundError(error.message)
        elif error.permission_error:
            raise PermissionError(error.message)
        else:
            raise IOError(error.message)


async def buffered_write(
    path: Union[str, Path],
    content: str,
    buffer_size: int = 8192,
    encoding: str = 'utf-8'
) -> None:
    """
    Legacy version that raises exceptions.
    
    DEPRECATED: Use buffered_write_safe instead.
    """
    result = await buffered_write_safe(path, content, buffer_size, encoding)
    if isinstance(result, Failure):
        error = result.failure()
        if error.permission_error:
            raise PermissionError(error.message)
        else:
            raise OSError(error.message)


async def atomic_write_async(
    path: Union[str, Path],
    content: str,
    mode: int = 0o644,
    encoding: str = 'utf-8'
) -> None:
    """
    Legacy version that raises exceptions.
    
    DEPRECATED: Use atomic_write_async_safe instead.
    """
    result = await atomic_write_async_safe(path, content, mode, encoding)
    if isinstance(result, Failure):
        error = result.failure()
        if error.permission_error:
            raise PermissionError(error.message)
        else:
            raise OSError(error.message)


# Legacy version of get_file_size_async
async def get_file_size_async(path: Union[str, Path]) -> int:
    """
    Legacy version that raises exceptions.
    
    DEPRECATED: Use get_file_size_async_safe instead.
    """
    result = await get_file_size_async_safe(path)
    if isinstance(result, Success):
        return result.unwrap()
    else:
        error = result.failure()
        if error.not_found:
            raise FileNotFoundError(error.message)
        elif error.permission_error:
            raise PermissionError(error.message)
        else:
            raise OSError(error.message)