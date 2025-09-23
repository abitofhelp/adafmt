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

from returns.io import IOResult, impure_safe

from .errors import FileError, file_not_found, permission_denied


def read_text(
    path: Union[str, Path],
    encoding: str = 'utf-8',
    errors: str = 'strict'
) -> IOResult[str, FileError]:
    """
    Read file with explicit error handling.
    
    Args:
        path: Path to file to read
        encoding: Text encoding
        errors: Error handling strategy ('strict', 'ignore', 'replace')
        
    Returns:
        IOResult[str, FileError]: File contents or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _read() -> str:
        # No try/except needed - decorator will catch exceptions
        return path.read_text(encoding=encoding, errors=errors)
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _read().alt(_map_read_error(path))


def write_text(
    path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8'
) -> IOResult[None, FileError]:
    """
    Write file with explicit error handling.
    
    Args:
        path: Path to file to write
        content: Content to write
        encoding: Text encoding
        
    Returns:
        IOResult[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _write() -> None:
        # No try/except needed - decorator will catch exceptions
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _write().alt(_map_write_error(path))


def exists(path: Union[str, Path]) -> IOResult[bool, FileError]:
    """
    Check if file exists with explicit error handling.
    
    Args:
        path: Path to check
        
    Returns:
        IOResult[bool, FileError]: True if exists, False if not, or error
        
    Note: In practice this rarely fails, but could on some systems
    """
    path = Path(path)
    
    @impure_safe
    def _exists() -> bool:
        return path.exists()
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _exists().alt(_map_stat_error(path))




def stat(path: Union[str, Path]) -> IOResult[os.stat_result, FileError]:
    """
    Get file stat with explicit error handling.
    
    Args:
        path: Path to stat
        
    Returns:
        IOResult[os.stat_result, FileError]: Stat result or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _stat() -> os.stat_result:
        return path.stat()
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _stat().alt(_map_stat_error(path))




def mkdir(
    path: Union[str, Path],
    mode: int = 0o777,
    parents: bool = False,
    exist_ok: bool = False
) -> IOResult[None, FileError]:
    """
    Create directory with explicit error handling.
    
    Args:
        path: Path to create
        mode: Directory permissions
        parents: Create parent directories if needed
        exist_ok: Don't error if directory already exists
        
    Returns:
        IOResult[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _mkdir() -> None:
        path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _mkdir().alt(_map_create_error(path))




def rmtree(path: Union[str, Path]) -> IOResult[None, FileError]:
    """
    Remove directory tree with explicit error handling.
    
    Args:
        path: Path to remove recursively
        
    Returns:
        IOResult[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _rmtree() -> None:
        shutil.rmtree(path)
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _rmtree().alt(_map_delete_error(path))




def remove(path: Union[str, Path]) -> IOResult[None, FileError]:
    """
    Remove file with explicit error handling.
    
    Args:
        path: Path to remove
        
    Returns:
        IOResult[None, FileError]: Success or specific error
    """
    path = Path(path)
    
    @impure_safe
    def _remove() -> None:
        path.unlink()
    
    # Map IOFailure[Exception] -> IOFailure[FileError]
    return _remove().alt(_map_delete_error(path))


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
            return file_not_found(path, "stat")
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
            return file_not_found(path, "delete")
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


