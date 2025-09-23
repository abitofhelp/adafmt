# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Error types for functional error handling using Either.

This module defines all error types used throughout adafmt.
All functions return Either[Error, Value] types - no exceptions propagate.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Note: In dry-python/returns, Result is actually an Either type
# Result[Value, Error] is Right-biased Either with Value on success
# We'll use the Result name but it's actually Either semantics
from returns.result import Result


# =============================================================================
# Base Error Types
# =============================================================================

@dataclass(frozen=True)
class AdafmtError:
    """Base error type for all adafmt errors."""
    message: str


# =============================================================================
# File Operation Errors
# =============================================================================

@dataclass(frozen=True)
class FileError(AdafmtError):
    """File operation error."""
    path: Path
    operation: Literal["read", "write", "create", "delete", "stat"]
    original_error: str | None = None
    permission_error: bool = False
    not_found: bool = False


# =============================================================================
# Parsing Errors
# =============================================================================

@dataclass(frozen=True)
class ParseError(AdafmtError):
    """Ada parsing error."""
    path: Path
    line: int
    column: int
    # message inherited from AdafmtError


# =============================================================================
# Visitor Pattern Errors
# =============================================================================

@dataclass(frozen=True)
class VisitorError(AdafmtError):
    """Error from formatting visitor."""
    path: Path
    visitor_name: str
    node_type: str
    # message inherited from AdafmtError


@dataclass(frozen=True)
class PatternError(AdafmtError):
    """Pattern application error."""
    path: Path
    pattern_name: str
    line: int = 0
    original_error: str | None = None
    # message inherited from AdafmtError


# =============================================================================
# Validation Errors
# =============================================================================

@dataclass(frozen=True)
class ValidationError(AdafmtError):
    """GNAT compiler validation error."""
    path: Path
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    command: str = ""
    # message inherited from AdafmtError


# =============================================================================
# ALS Communication Errors
# =============================================================================

@dataclass(frozen=True)
class ALSError(AdafmtError):
    """Ada Language Server communication error."""
    operation: Literal["start", "shutdown", "format", "initialize", "request"]
    timeout: bool = False
    connection_lost: bool = False
    invalid_response: bool = False
    path: Path | None = None


@dataclass(frozen=True)
class GNATError(ValidationError):
    """GNAT compiler validation error."""
    warnings_as_errors: bool = False
    
    def __post_init__(self):
        # Override the tool field from parent
        object.__setattr__(self, 'tool', 'gnat')


# =============================================================================
# Concurrency Errors
# =============================================================================

@dataclass(frozen=True)
class ConcurrencyError(AdafmtError):
    """Concurrency-related error."""
    operation: Literal["worker_start", "worker_stop", "queue_full", "timeout", "cancelled"]
    worker_id: int | None = None
    queue_size: int | None = None


@dataclass(frozen=True)
class WorkerError(ConcurrencyError):
    """Worker pool error."""
    path: Path | None = None
    inner_error: AdafmtError | None = None


# =============================================================================
# Configuration Errors
# =============================================================================

@dataclass(frozen=True)
class ConfigError(AdafmtError):
    """Configuration error."""
    config_file: Path | None = None
    key: str | None = None
    invalid_value: str | None = None


# =============================================================================
# Type Aliases for Common Either Types
# =============================================================================

# File operations return Either[FileError, T]
FileEither = Result[str, FileError]  # For file content
PathEither = Result[Path, FileError]  # For file paths

# Parsing returns Either[ParseError, AST]
ParseEither = Result[dict, ParseError]  # AST is typically a dict

# ALS operations return Either[ALSError, T]
ALSEither = Result[str, ALSError]  # For formatted content
ALSResponseEither = Result[dict, ALSError]  # For JSON-RPC responses

# Validation returns Either[ValidationError, bool]
ValidationEither = Result[bool, ValidationError]

# Pattern application returns Either[PatternError, str]
PatternEither = Result[str, PatternError]

# Worker operations return Either[WorkerError, T]
WorkerEither = Result[Path, WorkerError]  # For processed files


# =============================================================================
# Error Helpers
# =============================================================================

def file_not_found(path: Path, operation: Literal["read", "write", "create", "delete", "stat"] = "read") -> FileError:
    """Create a file not found error."""
    return FileError(
        message=f"File not found: {path}",
        path=path,
        operation=operation,
        not_found=True
    )


def permission_denied(path: Path, operation: Literal["read", "write", "create", "delete", "stat"]) -> FileError:
    """Create a permission denied error."""
    return FileError(
        message=f"Permission denied: {operation} {path}",
        path=path,
        operation=operation,
        permission_error=True
    )


def als_timeout(operation: Literal["start", "shutdown", "format", "initialize", "request"]) -> ALSError:
    """Create an ALS timeout error."""
    return ALSError(
        message=f"ALS timeout during {operation}",
        operation=operation,
        timeout=True
    )


def parse_failed(path: Path, line: int, column: int, message: str) -> ParseError:
    """Create a parse error."""
    return ParseError(
        message=message,
        path=path,
        line=line,
        column=column
    )