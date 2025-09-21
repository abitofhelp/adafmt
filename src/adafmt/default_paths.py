# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Default path handling for the Ada formatter."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


def get_default_paths(
    log_path: Optional[Path],
    stderr_path: Optional[Path]
) -> Tuple[Path, Path, bool, bool]:
    """
    Generate default paths for log and stderr files if not provided.
    
    Args:
        log_path: User-provided log path or None
        stderr_path: User-provided stderr path or None
        
    Returns:
        Tuple of (log_path, stderr_path, using_default_log, using_default_stderr)
    """
    # Generate timestamp for default filenames (ISO 8601 format)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    # Track if using default paths
    using_default_log = False
    using_default_stderr = False
    
    # Set default log path if not provided (check env var first)
    if log_path is None:
        env_log_path = os.getenv("ADAFMT_LOG_FILE_PATH")
        if env_log_path:
            log_path = Path(env_log_path)
        else:
            log_path = Path(f"./adafmt_{timestamp}_log.jsonl")
            using_default_log = True
    
    # Set default stderr path if not provided  
    if stderr_path is None:
        stderr_path = Path(f"./adafmt_{timestamp}_stderr.log")
        using_default_stderr = True
        
    return log_path, stderr_path, using_default_log, using_default_stderr


def get_debug_paths(
    timestamp: str,
    debug_patterns_path: Optional[Path],
    debug_als_path: Optional[Path]
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Generate paths for debug logs.
    
    Args:
        timestamp: Timestamp string for default filenames
        debug_patterns_path: User-provided debug patterns path or None
        debug_als_path: User-provided debug ALS path or None
        
    Returns:
        Tuple of (resolved_debug_patterns_path, resolved_debug_als_path)
        
    Note:
        If a path is provided as Path(""), it means use the default location.
        If None, debug logging is disabled for that component.
    """
    resolved_patterns_path = None
    resolved_als_path = None
    
    # Handle debug patterns path
    if debug_patterns_path is not None:
        if str(debug_patterns_path) == "" or str(debug_patterns_path) == ".":
            # Use default location
            resolved_patterns_path = Path(f"./adafmt_{timestamp}_debug-patterns.jsonl")
        else:
            resolved_patterns_path = debug_patterns_path
    
    # Handle debug ALS path
    if debug_als_path is not None:
        if str(debug_als_path) == "" or str(debug_als_path) == ".":
            # Use default location
            resolved_als_path = Path(f"./adafmt_{timestamp}_debug-als.jsonl")
        else:
            resolved_als_path = debug_als_path
            
    return resolved_patterns_path, resolved_als_path