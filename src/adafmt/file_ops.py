# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Synchronous file operations with functional error handling.

All functions return Result types - no exceptions propagate.
"""

import os
import shutil
from pathlib import Path
from typing import Union

from returns.result import Failure, Result, Success

from .errors import FileError, file_not_found, permission_denied


def _read_text_internal(
    path: Path,
    encoding: str = 'utf-8',
    errors: str = 'strict'
) -> Result[str, Exception]:
    """
    Internal read function that catches exceptions.
    
    Args:
        path: Path to file to read
        encoding: Text encoding
        errors: Error handling strategy
        
    Returns:
        Result[str, Exception]: File contents or exception
    """
    try:
        content = path.read_text(encoding=encoding, errors=errors)
        return Success(content)
    except Exception as e:
        return Failure(e)


def read_text(
    path: Union[str, Path],
    encoding: str = 'utf-8',
    errors: str = 'strict'
) -> Result[str, FileError]:
    """
    Read file with explicit error handling.
    
    Args:
        path: Path to file to read
        encoding: Text encoding
        errors: Error handling strategy ('strict', 'ignore', 'replace')
        
    Returns:
        Result[str, FileError]: File contents or specific error
    """
    path = Path(path)
    
    result = _read_text_internal(path, encoding, errors)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_read_error(path)
        return Failure(mapper(exc))


def _write_text_internal(
    path: Path,
    content: str,
    encoding: str = 'utf-8'
) -> Result[None, Exception]:
    """
    Internal write function that catches exceptions.
    
    Args:
        path: Path to file to write
        content: Content to write
        encoding: Text encoding
        
    Returns:
        Result[None, Exception]: Success or exception
    """
    try:
        path.write_text(content, encoding=encoding)
        return Success(None)
    except Exception as e:
        return Failure(e)


def write_text(
    path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8'
) -> Result[None, FileError]:
    """
    Write file with explicit error handling.
    
    Args:
        path: Path to file to write
        content: Content to write
        encoding: Text encoding
        
    Returns:
        Result[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    result = _write_text_internal(path, content, encoding)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_write_error(path)
        return Failure(mapper(exc))


def _exists_internal(path: Path) -> Result[bool, Exception]:
    """
    Internal exists function that catches exceptions.
    
    Args:
        path: Path to check
        
    Returns:
        Result[bool, Exception]: True if exists, False if not, or exception
    """
    try:
        return Success(path.exists())
    except Exception as e:
        return Failure(e)


def exists(path: Union[str, Path]) -> Result[bool, FileError]:
    """
    Check if file exists with explicit error handling.
    
    Args:
        path: Path to check
        
    Returns:
        Result[bool, FileError]: True if exists, False if not, or error
        
    Note: In practice this rarely fails, but could on some systems
    """
    path = Path(path)
    
    result = _exists_internal(path)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_stat_error(path)
        return Failure(mapper(exc))


def _stat_internal(path: Path) -> Result[os.stat_result, Exception]:
    """
    Internal stat function that catches exceptions.
    
    Args:
        path: Path to stat
        
    Returns:
        Result[os.stat_result, Exception]: File stat information or exception
    """
    try:
        return Success(path.stat())
    except Exception as e:
        return Failure(e)


def stat(path: Union[str, Path]) -> Result[os.stat_result, FileError]:
    """
    Get file stat with explicit error handling.
    
    Args:
        path: Path to stat
        
    Returns:
        Result[os.stat_result, FileError]: Stat result or specific error
    """
    path = Path(path)
    
    result = _stat_internal(path)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_stat_error(path)
        return Failure(mapper(exc))


def _mkdir_internal(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> Result[None, Exception]:
    """
    Internal mkdir function that catches exceptions.
    
    Args:
        path: Path to create
        mode: Directory permissions
        parents: Create parent directories if needed
        exist_ok: Don't error if directory already exists
        
    Returns:
        Result[None, Exception]: Success or exception
    """
    try:
        path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        return Success(None)
    except Exception as e:
        return Failure(e)


def mkdir(
    path: Union[str, Path],
    mode: int = 0o777,
    parents: bool = False,
    exist_ok: bool = False
) -> Result[None, FileError]:
    """
    Create directory with explicit error handling.
    
    Args:
        path: Path to create
        mode: Directory permissions
        parents: Create parent directories if needed
        exist_ok: Don't error if directory already exists
        
    Returns:
        Result[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    result = _mkdir_internal(path, mode, parents, exist_ok)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_create_error(path)
        return Failure(mapper(exc))


def _rmtree_internal(path: Path) -> Result[None, Exception]:
    """
    Internal rmtree function that catches exceptions.
    
    Args:
        path: Path to remove recursively
        
    Returns:
        Result[None, Exception]: Success or exception
    """
    try:
        shutil.rmtree(path)
        return Success(None)
    except Exception as e:
        return Failure(e)


def rmtree(path: Union[str, Path]) -> Result[None, FileError]:
    """
    Remove directory tree with explicit error handling.
    
    Args:
        path: Path to remove recursively
        
    Returns:
        Result[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    result = _rmtree_internal(path)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_delete_error(path)
        return Failure(mapper(exc))


def _remove_internal(path: Path) -> Result[None, Exception]:
    """
    Internal remove function that catches exceptions.
    
    Args:
        path: Path to remove
        
    Returns:
        Result[None, Exception]: Success or exception
    """
    try:
        path.unlink()
        return Success(None)
    except Exception as e:
        return Failure(e)


def remove(path: Union[str, Path]) -> Result[None, FileError]:
    """
    Remove file with explicit error handling.
    
    Args:
        path: Path to remove
        
    Returns:
        Result[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    result = _remove_internal(path)
    if isinstance(result, Success):
        return result
    else:
        # Map exception to FileError
        exc = result.failure()
        mapper = _map_delete_error(path)
        return Failure(mapper(exc))


# Error mapping functions
def _map_read_error(path: Path):
    """Map exceptions to FileError for read operations."""
    def mapper(exc: Exception) -> FileError:
        if isinstance(exc, FileNotFoundError):
            return file_not_found(path)
        elif isinstance(exc, PermissionError):
            return permission_denied(path, "read")
        elif isinstance(exc, UnicodeDecodeError):
            return FileError(
                message=f"Encoding error reading {path}: {exc}",
                path=path,
                operation="read",
                original_error=str(exc)
            )
        else:
            return FileError(
                message=f"Failed to read {path}: {exc}",
                path=path,
                operation="read",
                original_error=str(exc)
            )
    return mapper


def _map_write_error(path: Path):
    """Map exceptions to FileError for write operations."""
    def mapper(exc: Exception) -> FileError:
        if isinstance(exc, PermissionError):
            return permission_denied(path, "write")
        elif isinstance(exc, OSError):
            return FileError(
                message=f"OS error writing {path}: {exc}",
                path=path,
                operation="write",
                original_error=str(exc)
            )
        else:
            return FileError(
                message=f"Failed to write {path}: {exc}",
                path=path,
                operation="write",
                original_error=str(exc)
            )
    return mapper


def _map_stat_error(path: Path):
    """Map exceptions to FileError for stat operations."""
    def mapper(exc: Exception) -> FileError:
        if isinstance(exc, FileNotFoundError):
            return file_not_found(path)
        elif isinstance(exc, PermissionError):
            return permission_denied(path, "stat")
        else:
            return FileError(
                message=f"Failed to stat {path}: {exc}",
                path=path,
                operation="stat",
                original_error=str(exc)
            )
    return mapper


def _map_create_error(path: Path):
    """Map exceptions to FileError for create operations."""
    def mapper(exc: Exception) -> FileError:
        if isinstance(exc, PermissionError):
            return permission_denied(path, "create")
        elif isinstance(exc, FileExistsError):
            return FileError(
                message=f"File already exists: {path}",
                path=path,
                operation="create",
                original_error=str(exc)
            )
        else:
            return FileError(
                message=f"Failed to create {path}: {exc}",
                path=path,
                operation="create",
                original_error=str(exc)
            )
    return mapper


def _map_delete_error(path: Path):
    """Map exceptions to FileError for delete operations."""
    def mapper(exc: Exception) -> FileError:
        if isinstance(exc, FileNotFoundError):
            return file_not_found(path)
        elif isinstance(exc, PermissionError):
            return permission_denied(path, "delete")
        else:
            return FileError(
                message=f"Failed to delete {path}: {exc}",
                path=path,
                operation="delete",
                original_error=str(exc)
            )
    return mapper


