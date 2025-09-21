# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Logging setup and initialization for the Ada formatter."""

from pathlib import Path
from typing import Tuple, Optional

from .logging_jsonl import JsonlLogger


def setup_loggers(log_path: Path, debug_patterns_path: Optional[Path] = None, debug_als_path: Optional[Path] = None) -> Tuple[JsonlLogger, JsonlLogger, Path, Optional[JsonlLogger], Optional[Path], Optional[JsonlLogger], Optional[Path]]:
    """
    Initialize main and pattern loggers.
    
    Args:
        log_path: Path for main log file
        debug_patterns_path: Path for debug patterns log (None to disable, Path to enable with custom location)
        debug_als_path: Path for debug ALS log (None to disable, Path to enable with custom location)
        
    Returns:
        Tuple of (main_logger, pattern_logger, pattern_log_path, 
                 debug_pattern_logger, debug_pattern_log_path,
                 debug_als_logger, debug_als_log_path)
    """
    # Main logger - always create a logger (log_path is always set now)
    logger = JsonlLogger(log_path)
    logger.start_fresh()  # Create empty file, ensuring it exists
    
    # Pattern logger - create pattern log file
    # Try to extract timestamp from log filename, or use current time
    try:
        timestamp = log_path.name.split('_')[1].split('.')[0]  # Extract timestamp from main log filename
    except (IndexError, AttributeError):
        from datetime import datetime as dt
        timestamp = dt.now().strftime('%Y%m%dT%H%M%SZ')
    
    pattern_log_path = log_path.parent / f"adafmt_{timestamp}_patterns.log"
    pattern_logger = JsonlLogger(pattern_log_path)
    pattern_logger.start_fresh()
    
    # Debug pattern logger - only create if path is provided
    debug_pattern_logger = None
    debug_pattern_log_path = None
    if debug_patterns_path is not None:
        # If path is absolute, use as-is; if relative or just filename, resolve relative to log directory
        if debug_patterns_path.is_absolute():
            debug_pattern_log_path = debug_patterns_path
        else:
            debug_pattern_log_path = log_path.parent / debug_patterns_path
        debug_pattern_logger = JsonlLogger(debug_pattern_log_path)
        debug_pattern_logger.start_fresh()
    
    # Debug ALS logger - only create if path is provided
    debug_als_logger = None
    debug_als_log_path = None
    if debug_als_path is not None:
        # If path is absolute, use as-is; if relative or just filename, resolve relative to log directory
        if debug_als_path.is_absolute():
            debug_als_log_path = debug_als_path
        else:
            debug_als_log_path = log_path.parent / debug_als_path
        debug_als_logger = JsonlLogger(debug_als_log_path)
        debug_als_logger.start_fresh()
    
    return logger, pattern_logger, pattern_log_path, debug_pattern_logger, debug_pattern_log_path, debug_als_logger, debug_als_log_path