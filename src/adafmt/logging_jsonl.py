# =============================================================================
# adafmt - Ada Language Formatter
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# Licensed under the MIT License. See LICENSE file in the project root.
# =============================================================================

"""JSON Lines (JSONL) logging for adafmt operations.

This module provides a simple logger that writes JSON objects, one per line,
to a file. The JSONL format is ideal for logging structured data that can be
easily processed by other tools.

JSONL format:
    - Each line is a valid JSON object
    - Lines are separated by newlines (\n)
    - File can be processed line-by-line without loading entire content
    - Easy to grep, tail, and process with streaming tools

Typical log entries:
    {"path": "/src/file.ads", "status": "ok", "note": ""}
    {"path": "/src/bad.adb", "status": "failed", "note": "invalid syntax"}
    {"file": "/src/complex.ads", "notes": ["warning: long line", "info: formatted"]}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

class JsonlLogger:
    """Logger that writes JSON objects to a file, one per line.
    
    The logger overwrites the log file on each run rather than appending
    to previous runs. This ensures each adafmt execution has a clean log.
    
    Attributes:
        path: Path to the JSONL log file
        _file: Open file handle (managed internally)
    """
    
    def __init__(self, path: str) -> None:
        """Initialize the logger with a file path.
        
        Args:
            path: Path where the JSONL file will be written.
                  Parent directories are created if needed.
        """
        self.path = Path(path)
        self._file = None

    def __enter__(self):
        """Context manager entry - opens the log file."""
        self.start_fresh()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the log file."""
        self.close()
        return False

    def start_fresh(self) -> None:
        """Create a fresh log file, removing any existing content.
        
        This method:
        1. Creates parent directories if they don't exist
        2. Opens the file in write mode (truncating if exists)
        3. Keeps the file open for subsequent writes
        
        Note:
            This is called automatically when using the logger as a
            context manager, but can be called explicitly.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._file:
            self._file.close()
        self._file = self.path.open("w", encoding="utf-8")

    def write(self, record: Dict[str, Any]) -> None:
        """Write a single record as a JSON line.
        
        Args:
            record: Dictionary to serialize as JSON. Common fields:
                    - path: File path being processed
                    - status: Processing result (ok, changed, failed)
                    - note: Additional information or error details
                    
        Note:
            - Uses ensure_ascii=False to preserve Unicode characters
            - Writes to the open file handle
            - Flushes after each write for crash safety
            
        Example:
            >>> logger.write({"path": "test.ads", "status": "ok"})
            # Appends: {"path": "test.ads", "status": "ok"}\n
        """
        if not self._file:
            self.start_fresh()
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()  # Ensure crash safety
    
    def close(self) -> None:
        """Close the log file if open."""
        if self._file:
            self._file.close()
            self._file = None

    def append_notes(self, file: str, notes: List[str]) -> None:
        """Write a record containing multiple notes for a file.
        
        This is a convenience method for logging multiple messages
        about a single file as an array.
        
        Args:
            file: Path to the file these notes relate to
            notes: List of note messages
            
        Note:
            Does nothing if notes list is empty
            
        Example:
            >>> logger.append_notes("complex.ads", [
            ...     "reformatted 15 lines",
            ...     "fixed indentation",  
            ...     "normalized casing"
            ... ])
            # Appends: {"file": "complex.ads", "notes": [...]}\n
        """
        if not notes:
            return
        self.write({"file": file, "notes": notes})
