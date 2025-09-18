# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Pattern loading and initialization for the Ada formatter."""

from pathlib import Path
from typing import Optional, Any, Tuple

from .pattern_formatter import PatternFormatter, PatternLogger
from .logging_jsonl import JsonlLogger


def load_patterns(
    patterns_path: Optional[Path],
    no_patterns: bool,
    using_default_patterns: bool,
    pattern_logger: JsonlLogger,
    ui: Optional[Any] = None,
    client: Optional[Any] = None
) -> Tuple[Optional[PatternFormatter], Optional[Path]]:
    """
    Load pattern formatter from configuration.
    
    Args:
        patterns_path: Path to patterns file (may be None for default)
        no_patterns: If True, skip pattern loading
        using_default_patterns: Whether using default patterns path
        pattern_logger: Logger for pattern events
        ui: UI instance for logging
        client: ALS client (for shutdown on error)
        
    Returns:
        Tuple of (pattern_formatter, actual_patterns_path)
        
    Raises:
        SystemExit: If explicitly provided patterns file not found
    """
    pattern_formatter = None
    
    if not no_patterns:
        # Use default path if not provided
        if patterns_path is None:
            patterns_path = Path("./adafmt_patterns.json")
            using_default_patterns = True
        
        # Check if patterns file exists when explicitly provided
        if not using_default_patterns and not patterns_path.exists():
            if ui:
                ui.log_line(f"[error] Patterns file not found: {patterns_path}")
                ui.close()
            else:
                print(f"[error] Patterns file not found: {patterns_path}")
            if client:
                import asyncio
                asyncio.create_task(client.shutdown())
            raise SystemExit(2)
        
        # For default path, it's OK if it doesn't exist
        if patterns_path.exists():
            if ui:
                ui.log_line(f"[patterns] Loading patterns from: {patterns_path}")
            
            try:
                pattern_formatter = PatternFormatter.load_from_json(
                    patterns_path,
                    logger=PatternLogger(pattern_logger),
                    ui=ui
                )
                
                # Check if patterns file is empty (no patterns loaded)
                if pattern_formatter.loaded_count == 0:
                    if ui:
                        ui.log_line("[patterns] Warning: Pattern file is empty, only ALS formatting will be performed")
                    else:
                        print("[patterns] Warning: Pattern file is empty, only ALS formatting will be performed")
                    pattern_formatter = None  # Same as --no-patterns
                else:
                    if ui:
                        ui.log_line(f"[patterns] Loaded {pattern_formatter.loaded_count} patterns")
                        
            except Exception:
                raise
        else:
            # Default patterns file doesn't exist - that's OK, continue without patterns
            if ui:
                ui.log_line("[patterns] No patterns file found, only ALS formatting will be performed")
            else:
                print("[patterns] No patterns file found, only ALS formatting will be performed")
    else:
        if ui:
            ui.log_line("[patterns] Pattern processing disabled (--no-patterns)")
        else:
            print("[patterns] Pattern processing disabled (--no-patterns)")
            
    return pattern_formatter, patterns_path