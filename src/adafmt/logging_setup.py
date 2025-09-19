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


def setup_loggers(log_path: Path) -> Tuple[JsonlLogger, JsonlLogger, Path]:
    """
    Initialize main and pattern loggers.
    
    Args:
        log_path: Path for main log file
        
    Returns:
        Tuple of (main_logger, pattern_logger, pattern_log_path)
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
    
    return logger, pattern_logger, pattern_log_path