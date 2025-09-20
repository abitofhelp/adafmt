# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Terminal User Interface (TUI) module for adafmt.

Provides a simple plain text UI implementation for the formatter.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class UIState:
    """Shared state for UI implementation.
    
    This dataclass holds the display information that the UI renders.
    """
    # Header info
    header: str = "Ada Formatter"
    version: str = ""
    mode: str = ""
    
    # Progress tracking
    done_count: int = 0
    total_count: int = 0
    failed_count: int = 0
    
    # Log entries
    log_entries: list[str] = None
    
    # Footer status line
    footer_status: str = ""
    
    # Footer timing
    footer_timing: str = ""
    
    # Footer log paths
    footer_jsonl_log: str = ""
    footer_pattern_log: str = ""
    footer_stderr_log: str = ""
    footer_als_log: str = ""
    
    def __post_init__(self):
        if self.log_entries is None:
            self.log_entries = []


class BaseUI:
    """Abstract base class for all UI implementations.
    
    Defines the common interface that all UI classes must implement.
    This ensures consistent behavior across different UI types.
    """
    
    def __init__(self):
        """Initialize the UI with shared state."""
        self.state = UIState()
        self._lock = threading.Lock()
        self._closed = False
    
    def set_header(self, title: str, version: str = "", mode: str = "") -> None:
        """Update the header information.
        
        Args:
            title: Application title to display
            version: Version string (optional)
            mode: Operation mode (e.g., "DRY RUN", "WRITE MODE")
        """
        with self._lock:
            self.state.header = title
            self.state.version = version
            self.state.mode = mode
    
    def set_progress(self, done: int, total: int) -> None:
        """Update progress counters.
        
        Args:
            done: Number of completed items
            total: Total number of items
        """
        with self._lock:
            self.state.done_count = done
            self.state.total_count = total
    
    def close(self) -> None:
        """Clean up UI resources.
        
        This method should be called when the UI is no longer needed
        to clean up threads or other resources.
        """
        self._closed = True
    
    def log_line(self, msg: str) -> None:
        """Add a log message to the UI.
        
        Args:
            msg: Message to display
        """
        raise NotImplementedError
    
    def show_error(self, msg: str) -> None:
        """Display an error message prominently.
        
        Args:
            msg: Error message to display
        """
        raise NotImplementedError
    
    def wait_for_key(self) -> None:
        """Wait for user to press a key.
        
        This is typically used at the end of execution to prevent
        the UI from closing immediately.
        """
        raise NotImplementedError
    
    def set_footer_status(self, status: str) -> None:
        """Update the footer status line.
        
        Args:
            status: Status message to display
        """
        with self._lock:
            self.state.footer_status = status
    
    def set_footer_timing(self, timing: str) -> None:
        """Update the footer timing information.
        
        Args:
            timing: Timing information to display
        """
        with self._lock:
            self.state.footer_timing = timing
    
    def set_log_paths(self, jsonl_log: Optional[str] = None,
                     pattern_log: Optional[str] = None,
                     stderr_log: Optional[str] = None,
                     als_log: Optional[str] = None) -> None:
        """Update log file paths in footer.
        
        Args:
            jsonl_log: Path to JSON Lines log file
            pattern_log: Path to pattern log file
            stderr_log: Path to stderr log file
            als_log: Path to ALS log file
        """
        with self._lock:
            if jsonl_log:
                self.state.footer_jsonl_log = f"   JSONL log: {jsonl_log}"
            if pattern_log:
                self.state.footer_pattern_log = f" Pattern log: {pattern_log}"
            if stderr_log:
                self.state.footer_stderr_log = f"  Stderr log: {stderr_log}"
            if als_log:
                self.state.footer_als_log = f"     ALS log: {als_log}"
    
    def update_footer_stats(self, total: int, changed: int, unchanged: int, 
                          failed: int, elapsed: float, rate: float,
                          jsonl_log: str = "", als_log: str = "", 
                          stderr_log: str = "", pattern_log: str = "") -> None:
        """Update footer statistics.
        
        Args:
            total: Total number of files
            changed: Number of changed files
            unchanged: Number of unchanged files
            failed: Number of failed files
            elapsed: Elapsed time in seconds
            rate: Processing rate in files/second
            jsonl_log: Path to JSON Lines log file
            als_log: Path to ALS log file
            stderr_log: Path to stderr log file
            pattern_log: Path to pattern log file
        """
        raise NotImplementedError


# Import lock to avoid recursive imports
import threading


class PlainUI(BaseUI):
    """Simple stdout-only UI implementation.
    
    This UI writes all output directly to stdout with no terminal
    control sequences. It's suitable for:
    - Non-TTY environments (pipes, redirects)
    - Environments without curses support
    - Simple logging requirements
    - CI/CD pipelines
    
    Features:
    - Direct stdout output
    - Timestamped log entries  
    - Error highlighting
    - Progress tracking via log messages
    """
    
    def __init__(self):
        """Initialize plain UI."""
        super().__init__()
        self._start_time = time.time()
    
    def log_line(self, msg: str) -> None:
        """Add a timestamped log message.
        
        Messages are written directly to stdout with timestamps.
        Special formatting is applied to error messages.
        
        Args:
            msg: Message to log
        """
        if self._closed:
            return
        
        with self._lock:
            self.state.log_entries.append(msg)
            
            # Special handling for file processing messages
            if msg.startswith("[") and ("/") in msg and ("] [") in msg:
                # Use the CLI color function for consistent coloring
                from .cli import _print_colored_line
                _print_colored_line(msg)
            else:
                # Regular message, just print it
                print(msg)
    
    def show_error(self, msg: str) -> None:
        """Display an error message.
        
        Errors are prefixed with [error] and logged normally.
        
        Args:
            msg: Error message to display
        """
        self.log_line(f"[error] {msg}")
    
    def wait_for_key(self) -> None:
        """No-op for plain UI.
        
        Unlike curses UIs that update a persistent footer,
        plain UI doesn't need to wait for key press.
        """
        pass
    
    def update_footer_stats(self, total: int, changed: int, unchanged: int, 
                          failed: int, elapsed: float, rate: float,
                          jsonl_log: str = "", als_log: str = "", 
                          stderr_log: str = "", pattern_log: str = "") -> None:
        """Update footer statistics - no-op for plain UI.
        
        Unlike curses UIs that maintain a persistent footer,
        plain UI shows stats at the end of execution.
        """
        pass


def dbg(msg: str) -> None:
    """Debug helper that writes to stderr if ADAFMT_UI_DEBUG is set.
    
    Args:
        msg: Debug message to potentially display
    """
    if os.environ.get("ADAFMT_UI_DEBUG"):
        print(f"[UI_DEBUG] {msg}", file=sys.stderr, flush=True)


def make_ui(mode: str = "plain") -> BaseUI:
    """Factory function to create appropriate UI instance.
    
    Args:
        mode: UI mode - only "plain" is supported now
    
    Returns:
        PlainUI instance
    
    Environment variables:
        ADAFMT_UI_FORCE: Force specific UI mode (overrides auto-detection)
        ADAFMT_UI_DEBUG: Enable debug output
    """
    # Check for forced mode via environment
    forced_mode = os.environ.get("ADAFMT_UI_FORCE")
    if forced_mode:
        dbg(f"ADAFMT_UI_FORCE={forced_mode}")
        mode = forced_mode
    
    # Always return PlainUI
    dbg(f"mode={mode} -> plain")
    return PlainUI()