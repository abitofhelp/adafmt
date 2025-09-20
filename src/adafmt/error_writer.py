# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Error writing utilities for the Ada formatter."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .utils import to_iso8601_basic


def write_stderr_error(path: Path, error_type: str, error_msg: str, details: Optional[dict] = None) -> None:
    """Write detailed error information to stderr with timestamp.
    
    Args:
        path: The file that failed
        error_type: Type of error (e.g., "ALS_SYNTAX_ERROR", "TIMEOUT", etc.)
        error_msg: The error message
        details: Optional additional details as a dictionary
    """
    # Only write to stderr if it has been properly redirected to a file
    # This prevents error details from appearing in the UI output
    if hasattr(sys.stderr, '_streams') and sys.stderr._streams:
        timestamp = to_iso8601_basic(datetime.now(timezone.utc))
        stderr_msg = f"{timestamp} | ERROR | {error_type} | {path}\n"
        stderr_msg += f"{timestamp} | ERROR | Message: {error_msg}\n"
        
        if details:
            for key, value in details.items():
                stderr_msg += f"{timestamp} | ERROR | {key}: {value}\n"
        
        stderr_msg += f"{timestamp} | ERROR | {'=' * 60}\n"
        sys.stderr.write(stderr_msg)
        sys.stderr.flush()