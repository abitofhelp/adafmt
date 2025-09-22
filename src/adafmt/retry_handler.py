# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Retry handler for transient errors."""

import asyncio
from typing import TypeVar, Callable, Optional, Tuple
from pathlib import Path

T = TypeVar('T')


class RetryHandler:
    """Handles retry logic for transient errors."""
    
    # Transient error types that warrant retry
    TRANSIENT_ERRORS = (
        OSError,  # File system errors
        IOError,  # I/O errors
        asyncio.TimeoutError,  # Timeout errors
        PermissionError,  # Temporary permission issues
    )
    
    # Specific error codes that are transient
    TRANSIENT_ERRNO = {
        11,   # EAGAIN - Resource temporarily unavailable
        35,   # EWOULDBLOCK - Operation would block
        4,    # EINTR - Interrupted system call
        116,  # ESTALE - Stale file handle
    }
    
    @staticmethod
    def is_transient_error(error: Exception) -> bool:
        """Check if an error is transient and worth retrying.
        
        Args:
            error: The exception to check
            
        Returns:
            True if error is transient
        """
        # Check error type
        if isinstance(error, RetryHandler.TRANSIENT_ERRORS):
            # Check specific errno for OS errors
            if hasattr(error, 'errno') and error.errno in RetryHandler.TRANSIENT_ERRNO:
                return True
            
            # Permission errors on network drives can be transient
            if isinstance(error, PermissionError):
                return True
            
            # Timeout is always transient
            if isinstance(error, asyncio.TimeoutError):
                return True
            
            # Generic OSError/IOError might be transient
            if isinstance(error, (OSError, IOError)):
                # Check for specific messages
                msg = str(error).lower()
                transient_patterns = [
                    'temporarily unavailable',
                    'resource busy',
                    'device not ready',
                    'network',
                    'connection',
                ]
                return any(pattern in msg for pattern in transient_patterns)
        
        return False
    
    @staticmethod
    async def retry_async(
        func: Callable[..., T],
        *args,
        max_attempts: int = 3,
        backoff_base: float = 0.1,
        backoff_max: float = 2.0,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Tuple[T, int]:
        """Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            *args: Positional arguments for func
            max_attempts: Maximum retry attempts
            backoff_base: Base backoff time in seconds
            backoff_max: Maximum backoff time
            on_retry: Optional callback for retry events
            **kwargs: Keyword arguments for func
            
        Returns:
            Tuple of (result, attempts_used)
            
        Raises:
            The last exception if all retries fail
        """
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                return result, attempt
                
            except Exception as e:
                last_error = e
                
                # Check if error is transient
                if not RetryHandler.is_transient_error(e) or attempt >= max_attempts:
                    raise
                
                # Calculate backoff
                backoff = min(
                    backoff_base * (2 ** (attempt - 1)),
                    backoff_max
                )
                
                # Notify retry callback
                if on_retry:
                    on_retry(attempt, e)
                
                # Wait before retry
                await asyncio.sleep(backoff)
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise RuntimeError("Retry logic error")
    
    @staticmethod
    def should_retry_file_operation(path: Path, error: Exception) -> bool:
        """Check if a file operation should be retried.
        
        Args:
            path: File path involved
            error: The error that occurred
            
        Returns:
            True if operation should be retried
        """
        # Don't retry if file doesn't exist
        if isinstance(error, FileNotFoundError):
            return False
        
        # Don't retry if path is invalid
        if not path or not str(path).strip():
            return False
        
        # Check general transient errors
        return RetryHandler.is_transient_error(error)