# =============================================================================
# adafmt - Ada Language Formatter
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# Licensed under the MIT License. See LICENSE file in the project root.
# =============================================================================

"""Terminal User Interface (TUI) module for adafmt.

Provides multiple UI implementations with graceful fallback:
    - PrettyCursesUI: Full-featured curses interface with progress bar
    - BasicCursesUI: Simpler curses interface with scrolling log
    - PlainUI: Stdout-only interface for non-TTY environments

The UI automatically selects the best available option based on:
    - Terminal capabilities (TTY detection)
    - Curses library availability
    - User preference via --ui flag
    - Environment variables (ADAFMT_UI_FORCE, ADAFMT_UI_DEBUG)

Fallback chain:
    pretty → basic → plain
    basic → plain
    auto → pretty (if TTY+curses) → plain

All UI classes share the same interface, allowing transparent switching
between implementations without changing the calling code.
"""

from __future__ import annotations

import os
import re
import sys
import time
import threading
from dataclasses import dataclass
from typing import Optional

# We import curses lazily inside classes to avoid import errors when not in a TTY.


@dataclass
class UIState:
    """Shared state for all UI implementations.
    
    This dataclass holds the display information that UI classes render.
    Using a shared state pattern allows consistent data across different
    UI implementations and simplifies updates.
    
    Attributes:
        title: Main application title shown in header
        version: Version string appended to title
        footer_left: Text shown in bottom-left (typically ALS log path)
        footer_right: Text shown in bottom-right (typically file count)
        progress_total: Total number of items to process
        progress_done: Number of items completed
    """
    title: str = "Ada Formatter"
    version: str = ""
    footer_left: str = ""
    footer_right: str = ""
    progress_total: int = 0
    progress_done: int = 0
    # Multi-line footer data
    footer_stats: str = ""
    footer_timing: str = ""
    footer_jsonl_log: str = ""
    footer_pattern_log: str = ""
    footer_als_log: str = ""
    footer_stderr_log: str = ""
    failed_count: int = 0
    changed_count: int = 0
    unchanged_count: int = 0
    mode: str = ""  # For "DRY RUN" or "WRITE MODE"


class BaseUI:
    """Abstract base class for all UI implementations.
    
    Defines the interface that all UI classes must implement. This ensures
    that different UI modes can be used interchangeably without changing
    the calling code.
    
    The base implementation provides simple stdout printing, which derived
    classes can override with more sophisticated rendering.
    """
    
    def __init__(self) -> None:
        """Initialize the UI with default state."""
        self.state = UIState()
        self._closed = False
        self._wait_for_key = False

    # ----- lifecycle -----
    def close(self) -> None:
        """Clean up UI resources.
        
        Called when formatting is complete. Derived classes should override
        to clean up curses, threads, or other resources.
        """
        self._closed = True

    # ----- header/footer -----
    def set_header(self, title: str, version: str = "", mode: str = "") -> None:
        """Set the header text displayed at the top of the UI.
        
        Args:
            title: Main title text (e.g., "Ada Formatter")
            version: Optional version string to append
            mode: Optional mode string (e.g., "DRY RUN" or "WRITE MODE")
        """
        self.state.title, self.state.version, self.state.mode = title, version, mode

    def set_footer(self, left: str = "", right: str = "") -> None:
        """Set the footer text displayed at the bottom of the UI.
        
        Args:
            left: Text for bottom-left (e.g., "ALS Log: /path/to/log")
            right: Text for bottom-right (e.g., "Files: 42")
        """
        self.state.footer_left, self.state.footer_right = left, right
    
    def update_footer_stats(self, total: int, changed: int, unchanged: int, failed: int, 
                           elapsed: float, rate: float, jsonl_log: str, als_log: str, 
                           stderr_log: str = "", pattern_log: str = "") -> None:
        """Update the multi-line footer statistics.
        
        Args:
            total: Total number of files
            changed: Number of changed files
            unchanged: Number of unchanged files  
            failed: Number of failed files
            elapsed: Elapsed time in seconds
            rate: Processing rate (files/second)
            jsonl_log: Path to JSONL log file
            als_log: Path to ALS log file
            stderr_log: Path to stderr log file
            pattern_log: Path to pattern log file
        """
        # Calculate percentages
        done = changed + unchanged + failed
        pct_done = (done * 100 // total) if total > 0 else 0
        pct_changed = (changed * 100 // total) if total > 0 else 0
        pct_unchanged = (unchanged * 100 // total) if total > 0 else 0
        pct_failed = (failed * 100 // total) if total > 0 else 0
        
        # Update state - use fixed-width formatting for percentages to prevent bar movement
        self.state.footer_stats = f"Files: {total}({pct_done:3d}%) | ✓ Changed: {changed}({pct_changed:3d}%) | ✓ Unchanged: {unchanged}({pct_unchanged:3d}%) | ✗ Failed: {failed}({pct_failed:3d}%)"
        # Build timing line with fixed positioning to align with stats line above
        # Format elapsed with right-aligned padding to maintain consistent width
        elapsed_str = f"{elapsed:6.1f}"  # Right-aligned, 6 chars total (e.g., "  10.5")
        # This ensures the bar position never moves
        self.state.footer_timing = f"Elapsed: {elapsed_str}s | Rate: {rate:.1f} files/s"
        self.state.footer_jsonl_log = f"Log:     {jsonl_log}"
        self.state.footer_pattern_log = f"Pat Log: {pattern_log}" if pattern_log else ""
        self.state.footer_als_log = f"ALS Log: {als_log}"
        self.state.footer_stderr_log = f"Stderr:  ./{stderr_log}" if stderr_log and not stderr_log.startswith("./") else f"Stderr:  {stderr_log}"
        self.state.failed_count = failed
        self.state.changed_count = changed
        self.state.unchanged_count = unchanged

    # ----- progress -----
    def set_progress(self, done: int, total: int) -> None:
        """Update the progress indicator.
        
        Args:
            done: Number of items completed
            total: Total number of items to process
        """
        self.state.progress_done, self.state.progress_total = done, total

    # ----- lines -----
    def log_line(self, msg: str) -> None:
        """Add a line to the scrolling log area.
        
        Args:
            msg: Message to display (e.g., "[   1/10] [ok     ] file.ads")
        """
        print(msg)
    
    def wait_for_key(self) -> None:
        """Wait for user to press a key before continuing."""
        self._wait_for_key = True


class PlainUI(BaseUI):
    """Minimal stdout UI that works in any environment.
    
    This is the fallback UI when:
    - Not running in a terminal (e.g., piped output)
    - Curses is not available
    - User explicitly requests --ui plain
    
    Features:
    - Prints title banner once at startup
    - Shows each file as it is processed
    - Prints footer summary when complete
    - No live updates or progress bars
    """

    def __init__(self) -> None:
        """Initialize the plain UI."""
        super().__init__()
        self._start_banner_printed = False

    def _print_banner_once(self) -> None:
        """Print the application banner on first output.
        
        Ensures the banner is only printed once, even if log_line
        is called multiple times before any output.
        """
        if not self._start_banner_printed:
            ver = f" v{self.state.version}" if self.state.version else ""
            print(f"{self.state.title}{ver}")
            self._start_banner_printed = True

    def log_line(self, msg: str) -> None:
        """Print a message line, ensuring banner is shown first.
        
        Args:
            msg: Line to print
            
        Note:
            Exceptions are silently caught to handle broken pipes
            when output is piped to commands like 'head'.
        """
        self._print_banner_once()
        try:
            # Color [failed ] in bright red if present and we're in a terminal
            if "[failed ]" in msg and _have_tty():
                start_idx = msg.find("[failed ]")
                end_idx = start_idx + len("[failed ]")
                # Print with ANSI color codes for bright red
                colored_msg = msg[:start_idx] + "\033[91m\033[1m[failed ]\033[0m" + msg[end_idx:]
                print(colored_msg)
            else:
                print(msg)
        except Exception:
            pass

    def set_progress(self, done: int, total: int) -> None:
        """Update progress state without displaying it.
        
        Plain UI does not show live progress since it cannot update
        lines in place. Progress is only shown in the final footer.
        """
        self.state.progress_done, self.state.progress_total = done, total

    def set_footer(self, left: str = "", right: str = "") -> None:
        """Print footer information immediately.
        
        Unlike curses UIs that update a persistent footer,
        plain UI prints the footer as a regular line.
        """
        if left or right:
            print(f"{left}  {right}".rstrip())


class BasicCursesUI(BaseUI):
    """Curses-based UI with scrolling log and live footer.
    
    Features:
    - Header with title and version
    - Scrolling log area showing recent messages
    - Live-updating footer with progress percentage
    - Thread-safe updates from async code
    
    The UI runs in a separate thread to avoid blocking async operations.
    All updates are thread-safe through the shared UIState.
    """

    def __init__(self) -> None:
        """Initialize curses UI and start render thread."""
        super().__init__()
        self._lines: list[str] = []
        self._thr: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._key_pressed = threading.Event()
        self._start_curses()

    def _start_curses(self) -> None:
        """Start the curses rendering loop in a background thread.
        
        The rendering loop:
        1. Clears the screen
        2. Draws header with title
        3. Shows scrolling log of recent messages
        4. Updates footer with progress
        5. Refreshes at ~20 FPS
        
        Uses curses.wrapper to ensure proper terminal cleanup.
        """
        import curses  # lazy import

        def loop(stdscr) -> None:
            """Main rendering loop running in curses.wrapper context."""
            curses.curs_set(0)
            stdscr.nodelay(True)
            
            # Initialize colors if supported
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
                curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
                curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # For DRY RUN
            
            popup_win = None
            while not self._stop.is_set():
                stdscr.erase()
                h, w = stdscr.getmaxyx()
                
                # Build header with mode right-aligned
                title = self.state.title
                if self.state.version:
                    title += f"  v{self.state.version}"
                
                # Calculate positions for right-aligned mode
                if self.state.mode:
                    mode_text = f"Mode: {self.state.mode}"
                    mode_len = len(mode_text)
                    title_len = len(title)
                    
                    # Ensure we have enough space
                    if title_len + mode_len + 5 < w:
                        # Display title on the left
                        stdscr.addstr(0, 0, title)
                        
                        # Display mode on the right
                        mode_x = w - mode_len - 1
                        stdscr.addstr(0, mode_x, "Mode: ")
                        
                        # Colorize mode in bright yellow
                        if curses.has_colors():
                            stdscr.addstr(0, mode_x + 6, self.state.mode, curses.color_pair(2) | curses.A_BOLD)
                        else:
                            stdscr.addstr(0, mode_x + 6, self.state.mode)
                    else:
                        # Not enough space, just show title
                        stdscr.addstr(0, 0, title[: w - 1])
                else:
                    stdscr.addstr(0, 0, title[: w - 1])
                
                stdscr.hline(1, 0, "-", w)

                # body - leave room for 5-line footer
                footer_height = 6  # 5 lines + separator
                max_body = max(0, h - 3 - footer_height)  # Header, separator, and footer
                for i, line in enumerate(self._lines[-max_body:]):
                    # Special highlighting for specific lines
                    if "Press any key to exit..." in line:
                        if curses.has_colors():
                            stdscr.addstr(2 + i, 0, line[: w - 1], curses.color_pair(1) | curses.A_BOLD)
                        else:
                            stdscr.addstr(2 + i, 0, line[: w - 1], curses.A_REVERSE)
                    elif "[failed ]" in line:
                        # Color the failed status in bright red
                        if curses.has_colors():
                            # Find where [failed ] starts
                            start_idx = line.find("[failed ]")
                            end_idx = start_idx + len("[failed ]")
                            
                            # Print the prefix
                            if start_idx > 0:
                                stdscr.addstr(2 + i, 0, line[:start_idx])
                            
                            # Print [failed ] in bright red
                            stdscr.addstr(2 + i, start_idx, "[failed ]", curses.color_pair(3) | curses.A_BOLD)
                            
                            # Print the rest of the line
                            if end_idx < len(line) and end_idx < w - 1:
                                rest = line[end_idx:w - 1]
                                stdscr.addstr(2 + i, end_idx, rest)
                        else:
                            stdscr.addstr(2 + i, 0, line[: w - 1])
                    else:
                        stdscr.addstr(2 + i, 0, line[: w - 1])

                # Draw 5-line footer
                if self.state.footer_stats:
                    footer_y = h - footer_height
                    
                    # Separator line
                    stdscr.hline(footer_y, 0, "-", w)
                    
                    # Line 1: Stats (with color for failed)
                    stats_line = self.state.footer_stats
                    if self.state.failed_count > 0 and curses.has_colors():
                        # Print stats line with proper coloring (with red for failures)
                        # Parse the stats line to extract individual components
                        # Updated pattern to handle fixed-width percentages with spaces
                        stats_pattern = r"Files: (\d+\(\s*\d+%\)) \| ✓ Changed: (\d+\(\s*\d+%\)) \| ✓ Unchanged: (\d+\(\s*\d+%\)) \| ✗ Failed: (\d+\(\s*\d+%\))"
                        match = re.match(stats_pattern, stats_line)
                        
                        if match:
                            x_pos = 0
                            y_pos = footer_y + 1
                            
                            # Files: XXX(XX%)
                            files_text = f"Files: {match.group(1)}"
                            stdscr.addstr(y_pos, x_pos, files_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(files_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✓ Changed: XXX(XX%)
                            stdscr.addstr(y_pos, x_pos, "✓ ", curses.A_BOLD)  # Checkmark in default
                            x_pos += 2
                            changed_text = f"Changed: {match.group(2)}"
                            stdscr.addstr(y_pos, x_pos, changed_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(changed_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✓ Unchanged: XXX(XX%)
                            stdscr.addstr(y_pos, x_pos, "✓ ", curses.A_BOLD)  # Checkmark in default
                            x_pos += 2
                            unchanged_text = f"Unchanged: {match.group(3)}"
                            stdscr.addstr(y_pos, x_pos, unchanged_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(unchanged_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✗ Failed: XXX(XX%) - in RED
                            stdscr.addstr(y_pos, x_pos, "✗ ", curses.A_BOLD)  # Cross in default
                            x_pos += 2
                            failed_text = f"Failed: {match.group(4)}"
                            stdscr.addstr(y_pos, x_pos, failed_text[: w - x_pos - 1], curses.color_pair(3) | curses.A_BOLD)
                        else:
                            # Fallback to simple display
                            parts = stats_line.split(" | ")
                            y_pos = footer_y + 1
                            x_pos = 0
                            for i, part in enumerate(parts):
                                if i > 0:
                                    stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                                    x_pos += 3
                                if "Failed:" in part:
                                    stdscr.addstr(y_pos, x_pos, part[: w - x_pos - 1], curses.color_pair(3) | curses.A_BOLD)
                                else:
                                    stdscr.addstr(y_pos, x_pos, part[: w - x_pos - 1], curses.color_pair(1) | curses.A_BOLD)
                                x_pos += len(part)
                    else:
                        # Print stats line with proper coloring
                        # Parse the stats line to extract individual components
                        # Updated pattern to handle fixed-width percentages with spaces
                        stats_pattern = r"Files: (\d+\(\s*\d+%\)) \| ✓ Changed: (\d+\(\s*\d+%\)) \| ✓ Unchanged: (\d+\(\s*\d+%\)) \| ✗ Failed: (\d+\(\s*\d+%\))"
                        match = re.match(stats_pattern, stats_line)
                        
                        if match:
                            x_pos = 0
                            y_pos = footer_y + 1
                            
                            # Files: XXX(XX%)
                            files_text = f"Files: {match.group(1)}"
                            stdscr.addstr(y_pos, x_pos, files_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(files_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✓ Changed: XXX(XX%)
                            stdscr.addstr(y_pos, x_pos, "✓ ", curses.A_BOLD)  # Checkmark in default
                            x_pos += 2
                            changed_text = f"Changed: {match.group(2)}"
                            stdscr.addstr(y_pos, x_pos, changed_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(changed_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✓ Unchanged: XXX(XX%)
                            stdscr.addstr(y_pos, x_pos, "✓ ", curses.A_BOLD)  # Checkmark in default
                            x_pos += 2
                            unchanged_text = f"Unchanged: {match.group(3)}"
                            stdscr.addstr(y_pos, x_pos, unchanged_text, curses.color_pair(1) | curses.A_BOLD)
                            x_pos += len(unchanged_text)
                            
                            # Separator
                            stdscr.addstr(y_pos, x_pos, " | ", curses.A_BOLD)
                            x_pos += 3
                            
                            # ✗ Failed: XXX(XX%)
                            stdscr.addstr(y_pos, x_pos, "✗ ", curses.A_BOLD)  # Cross in default
                            x_pos += 2
                            failed_text = f"Failed: {match.group(4)}"
                            stdscr.addstr(y_pos, x_pos, failed_text[: w - x_pos - 1], curses.color_pair(1) | curses.A_BOLD)
                        else:
                            # Fallback to simple display
                            stdscr.addstr(footer_y + 1, 0, stats_line[: w - 1], curses.color_pair(1) | curses.A_BOLD)
                    
                    # Line 2: Timing with proper coloring
                    if self.state.footer_timing:
                        # Parse timing line to extract components
                        # Updated regex to handle right-aligned numbers with spaces
                        timing_match = re.match(r"(Elapsed:\s+\s*[0-9.]+s)\s*\|\s*(Rate:\s+[0-9.]+ files/s)", self.state.footer_timing)
                        
                        if timing_match:
                            x_pos = 0
                            y_pos = footer_y + 2
                            
                            # Draw elapsed part
                            elapsed_text = timing_match.group(1)
                            stdscr.addstr(y_pos, x_pos, elapsed_text, curses.color_pair(1) | curses.A_BOLD)
                            
                            # Calculate actual position of the bar based on the format string
                            # "Elapsed: XXXXXX.Xs " where X is space or digit
                            # Position = "Elapsed: " (9) + 6 chars for number + "s " (2) = 17
                            bar_x_pos = 9 + 6 + 2  # Fixed at position 17
                            
                            # Separator at fixed position
                            stdscr.addstr(y_pos, bar_x_pos, "| ", curses.A_BOLD)
                            x_pos = bar_x_pos + 2
                            
                            # Rate: XXX.X files/s
                            rate_text = timing_match.group(2)
                            stdscr.addstr(y_pos, x_pos, rate_text[: w - x_pos - 1], curses.color_pair(1) | curses.A_BOLD)
                        else:
                            # Fallback - use fixed position for bar
                            x_pos = 0
                            y_pos = footer_y + 2
                            # Fixed bar position at column 17
                            bar_x_pos = 17
                            sep_idx = self.state.footer_timing.find('|')
                            if sep_idx > 0:
                                # Draw elapsed part
                                stdscr.addstr(y_pos, x_pos, self.state.footer_timing[:sep_idx], curses.color_pair(1) | curses.A_BOLD)
                                # Draw separator at fixed position
                                stdscr.addstr(y_pos, bar_x_pos, "| ", curses.A_BOLD)
                                # Draw rate part
                                stdscr.addstr(y_pos, bar_x_pos + 2, self.state.footer_timing[sep_idx+2:w-1], curses.color_pair(1) | curses.A_BOLD)
                            else:
                                stdscr.addstr(footer_y + 2, 0, self.state.footer_timing[: w - 1], curses.color_pair(1) | curses.A_BOLD)
                    
                    # Line 3: JSONL Log
                    if self.state.footer_jsonl_log:
                        stdscr.addstr(footer_y + 3, 0, self.state.footer_jsonl_log[: w - 1], curses.color_pair(2) | curses.A_BOLD)
                    
                    # Line 4: Pattern Log
                    if self.state.footer_pattern_log:
                        stdscr.addstr(footer_y + 4, 0, self.state.footer_pattern_log[: w - 1], curses.color_pair(2) | curses.A_BOLD)
                    
                    # Line 5: Stderr
                    if self.state.footer_stderr_log:
                        stdscr.addstr(footer_y + 5, 0, self.state.footer_stderr_log[: w - 1], curses.color_pair(2) | curses.A_BOLD)
                    
                    # Line 6: ALS Log
                    if self.state.footer_als_log:
                        stdscr.addstr(footer_y + 6, 0, self.state.footer_als_log[: w - 1], curses.color_pair(2) | curses.A_BOLD)

                # Draw popup if waiting for key
                if self._wait_for_key and not popup_win:
                    # Create popup window
                    popup_h, popup_w = 7, 40
                    popup_y = (h - popup_h) // 2
                    popup_x = (w - popup_w) // 2
                    
                    popup_win = curses.newwin(popup_h, popup_w, popup_y, popup_x)
                    popup_win.nodelay(True)
                
                if popup_win and self._wait_for_key:
                    # Draw popup
                    popup_win.clear()
                    popup_win.border()
                    
                    # Add title and message
                    popup_win.addstr(1, 2, "Complete!", curses.A_BOLD)
                    popup_win.addstr(3, 2, "Press any key to exit...")
                    
                    # Center footer
                    footer = "[ OK ]"
                    popup_win.addstr(5, (popup_w - len(footer)) // 2, footer)
                    
                    popup_win.refresh()
                    
                    # Check for keypress on popup window
                    key = popup_win.getch()
                    if key != -1:  # Key was pressed
                        self._key_pressed.set()
                        self._wait_for_key = False
                        popup_win = None
                
                stdscr.refresh()
                time.sleep(0.05)

        import curses
        self._thr = threading.Thread(target=curses.wrapper, args=(loop,), daemon=True)
        self._thr.start()

    def log_line(self, msg: str) -> None:
        """Add a message to the scrolling log.
        
        Thread-safe: Can be called from the main async thread.
        The render thread will pick up new lines on next refresh.
        """
        self._lines.append(msg)

    def close(self) -> None:
        """Stop the render thread and clean up curses.
        
        Signals the background thread to stop and waits up to
        2 seconds for it to finish. This ensures curses properly
        restores the terminal.
        """
        self._stop.set()
        if self._thr and self._thr.is_alive():
            self._thr.join(timeout=2.0)
        super().close()
    
    def wait_for_key(self) -> None:
        """Wait for user to press a key."""
        self._wait_for_key = True
        self._key_pressed.clear()
        # Block until key is pressed
        self._key_pressed.wait()


class PrettyCursesUI(BasicCursesUI):
    """Enhanced curses UI with visual progress bar.
    
    Currently inherits all functionality from BasicCursesUI.
    Future enhancements could include:
    - Visual progress bar with Unicode blocks
    - Color support for status (green=ok, yellow=changed, red=failed)
    - Spinner animation during processing
    - ETA calculation based on processing rate
    """

    def __init__(self) -> None:
        """Initialize the pretty UI."""
        super().__init__()

    # We reuse BasicCursesUI rendering for stability in this drop.


def _have_tty() -> bool:
    """Check if stdout is connected to a terminal.
    
    Returns:
        True if stdout is a TTY, False if piped/redirected or on error
        
    Note:
        Returns False on any exception to safely fall back to plain UI
        in unusual environments.
    """
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _env_true(name: str) -> bool:
    """Check if an environment variable is set to a truthy value.
    
    Args:
        name: Environment variable name
        
    Returns:
        True if the variable contains: 1, true, yes, or on (case-insensitive)
        
    Example:
        ADAFMT_UI_DEBUG=1 enables debug output
        ADAFMT_UI_DEBUG=TRUE also works
    """
    return os.getenv(name, "").lower() in ("1", "true", "yes", "on")


def make_ui(mode: str = "auto") -> Optional[BaseUI]:
    """Create a UI instance based on mode and environment.
    
    Args:
        mode: UI mode selection:
            - "off": No UI (returns None)
            - "plain": Force plain stdout UI
            - "basic": Try basic curses, fall back to plain
            - "pretty": Try pretty curses, fall back to basic then plain
            - "auto": Automatically select best available (default)
            
    Returns:
        UI instance appropriate for the environment, or None if mode="off"
        
    Environment variables:
        ADAFMT_UI_FORCE: Override the mode parameter
        ADAFMT_UI_DEBUG: Enable debug output during UI selection
        
    The selection process considers:
    1. Terminal capabilities (TTY detection)
    2. Curses library availability
    3. User preference (mode parameter or ADAFMT_UI_FORCE)
    4. Graceful fallback on initialization errors
    """
    force = os.getenv("ADAFMT_UI_FORCE")
    debug = _env_true("ADAFMT_UI_DEBUG")
    if force:
        mode = force

    def dbg(msg: str) -> None:
        # Print debug message if ADAFMT_UI_DEBUG is set.
        if debug:
            print(f"[ui-debug] {msg}")

    if mode == "off":
        return None

    if mode == "plain":
        dbg("selected plain (explicit)")
        return PlainUI()

    if mode in ("pretty", "basic", "auto"):
        if not _have_tty():
            dbg("no TTY -> plain")
            return PlainUI()
        # try curses
        try:
            import curses  # noqa: F401
        except Exception as e:
            dbg(f"curses import failed: {e!r} -> plain")
            return PlainUI()

        if mode == "auto":
            dbg("auto -> pretty (TTY+curses detected)")
            return PrettyCursesUI()
        if mode == "pretty":
            try:
                dbg("trying PrettyCursesUI")
                return PrettyCursesUI()
            except Exception as e:
                dbg(f"pretty failed: {e!r} -> basic")
                try:
                    return BasicCursesUI()
                except Exception as e2:
                    dbg(f"basic failed: {e2!r} -> plain")
                    return PlainUI()
        if mode == "basic":
            try:
                dbg("trying BasicCursesUI")
                return BasicCursesUI()
            except Exception as e:
                dbg(f"basic failed: {e!r} -> plain")
                return PlainUI()

    # Unknown mode -> safest
    dbg("unknown mode -> plain")
    return PlainUI()
