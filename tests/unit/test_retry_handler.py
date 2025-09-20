# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for retry handler."""

import asyncio
import errno
from pathlib import Path
import pytest

from adafmt.retry_handler import RetryHandler


class TestRetryHandler:
    """Test RetryHandler functionality."""
    
    def test_is_transient_error_timeout(self):
        """Test timeout errors are considered transient."""
        error = asyncio.TimeoutError("Operation timed out")
        assert RetryHandler.is_transient_error(error)
    
    def test_is_transient_error_permission(self):
        """Test permission errors are considered transient."""
        error = PermissionError("Access denied")
        assert RetryHandler.is_transient_error(error)
    
    def test_is_transient_error_oserror_with_errno(self):
        """Test OSError with transient errno."""
        error = OSError(errno.EAGAIN, "Resource temporarily unavailable")
        error.errno = errno.EAGAIN
        assert RetryHandler.is_transient_error(error)
    
    def test_is_transient_error_oserror_with_message(self):
        """Test OSError with transient message."""
        error = OSError("Device not ready")
        assert RetryHandler.is_transient_error(error)
    
    def test_is_not_transient_error(self):
        """Test non-transient errors."""
        # ValueError is not transient
        assert not RetryHandler.is_transient_error(ValueError("Bad value"))
        
        # FileNotFoundError is not transient (permanent)
        assert not RetryHandler.is_transient_error(FileNotFoundError("No such file"))
        
        # Generic exception is not transient
        assert not RetryHandler.is_transient_error(Exception("Generic error"))
    
    @pytest.mark.asyncio
    async def test_retry_async_success_first_try(self):
        """Test retry with success on first attempt."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result, attempts = await RetryHandler.retry_async(test_func)
        
        assert result == "success"
        assert attempts == 1
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_async_success_after_retry(self):
        """Test retry with success after transient error."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Temporarily unavailable")
            return "success"
        
        result, attempts = await RetryHandler.retry_async(
            test_func,
            max_attempts=3
        )
        
        assert result == "success"
        assert attempts == 3
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_non_transient_error(self):
        """Test retry stops on non-transient error."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Bad value")
        
        with pytest.raises(ValueError):
            await RetryHandler.retry_async(test_func)
        
        assert call_count == 1  # No retries for non-transient
    
    @pytest.mark.asyncio
    async def test_retry_async_max_attempts_exceeded(self):
        """Test retry fails after max attempts."""
        call_count = 0
        
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("Always timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await RetryHandler.retry_async(
                test_func,
                max_attempts=2
            )
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_async_with_callback(self):
        """Test retry with on_retry callback."""
        retry_log = []
        
        async def test_func():
            if len(retry_log) < 2:
                raise OSError("Temporarily unavailable")
            return "success"
        
        def on_retry(attempt, error):
            retry_log.append((attempt, str(error)))
        
        result, attempts = await RetryHandler.retry_async(
            test_func,
            max_attempts=3,
            on_retry=on_retry
        )
        
        assert result == "success"
        assert attempts == 3
        assert len(retry_log) == 2
        assert retry_log[0] == (1, "Temporarily unavailable")
        assert retry_log[1] == (2, "Temporarily unavailable")
    
    def test_should_retry_file_operation_file_not_found(self):
        """Test file operations don't retry on FileNotFoundError."""
        path = Path("/test/file.txt")
        error = FileNotFoundError("File not found")
        
        assert not RetryHandler.should_retry_file_operation(path, error)
    
    def test_should_retry_file_operation_transient(self):
        """Test file operations retry on transient errors."""
        path = Path("/test/file.txt")
        error = OSError("Resource temporarily unavailable")
        
        assert RetryHandler.should_retry_file_operation(path, error)
    
    def test_should_retry_file_operation_invalid_path(self):
        """Test file operations don't retry on invalid path."""
        error = OSError("Some error")
        
        assert not RetryHandler.should_retry_file_operation(None, error)
        assert not RetryHandler.should_retry_file_operation(Path(""), error)