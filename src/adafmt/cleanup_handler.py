# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Cleanup and signal handling for the Ada formatter."""

import atexit
import asyncio
import contextlib
import signal
import sys
from typing import Optional, Any

from .als_client import ALSClient
from .logging_jsonl import JsonlLogger


# Global cleanup state
cleanup_client: Optional[ALSClient] = None
cleanup_ui: Optional[Any] = None
cleanup_logger: Optional[JsonlLogger] = None
cleanup_pattern_logger: Optional[JsonlLogger] = None
cleanup_restore_stderr: Optional[Any] = None


def cleanup_handler(signum=None, frame=None):
    """Clean up resources on exit or signal."""
    try:
        if cleanup_client:
            # Force sync shutdown of ALS client
            try:
                try:
                    # Try to get the running loop
                    loop = asyncio.get_running_loop()
                    # Schedule shutdown task
                    loop.create_task(cleanup_client.shutdown())
                except RuntimeError:
                    # No running loop, create new one for shutdown
                    asyncio.run(cleanup_client.shutdown())
            except Exception:
                # Force kill the process if graceful shutdown fails
                if hasattr(cleanup_client, '_proc') and cleanup_client._proc:
                    try:
                        cleanup_client._proc.terminate()
                    except Exception:
                        pass
        
        if cleanup_ui:
            with contextlib.suppress(Exception):
                cleanup_ui.close()
        
        if cleanup_logger:
            with contextlib.suppress(Exception):
                cleanup_logger.close()
        
        if cleanup_pattern_logger:
            with contextlib.suppress(Exception):
                cleanup_pattern_logger.close()
                
        if cleanup_restore_stderr:
            with contextlib.suppress(Exception):
                cleanup_restore_stderr()
                
    except Exception:
        pass  # Don't let cleanup errors crash the cleanup
        
    if signum:
        sys.exit(1)


def setup_cleanup_handlers():
    """Register signal handlers and atexit handler."""
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    atexit.register(cleanup_handler)


def set_cleanup_client(client: Optional[ALSClient]):
    """Set the ALS client for cleanup."""
    global cleanup_client
    cleanup_client = client


def set_cleanup_ui(ui: Optional[Any]):
    """Set the UI for cleanup."""
    global cleanup_ui
    cleanup_ui = ui


def set_cleanup_logger(logger: Optional[JsonlLogger]):
    """Set the main logger for cleanup."""
    global cleanup_logger
    cleanup_logger = logger


def set_cleanup_pattern_logger(logger: Optional[JsonlLogger]):
    """Set the pattern logger for cleanup."""
    global cleanup_pattern_logger
    cleanup_pattern_logger = logger


def set_cleanup_restore_stderr(restore_fn: Optional[Any]):
    """Set the stderr restore function for cleanup."""
    global cleanup_restore_stderr
    cleanup_restore_stderr = restore_fn