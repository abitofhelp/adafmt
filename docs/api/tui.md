# tui Module

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `tui` module provides Terminal User Interface components for interactive formatting sessions.

## Overview

This module implements multiple UI modes:
- **Pretty**: Rich interactive UI with progress bars and Unicode
- **Plain**: Simple text-based progress output
- **JSON**: Machine-readable structured output
- **Quiet**: Minimal output for scripts

## Functions

### make_ui()

```python
def make_ui(
    mode: UIMode,
    total_files: int,
    output_stream: TextIO = sys.stdout,
    use_color: bool = True
) -> UserInterface:
    """Create a user interface instance based on the specified mode.

    Args:
        mode: The UI mode to use (pretty, plain, json, quiet)
        total_files: Total number of files to process
        output_stream: Output stream for UI (default: stdout)
        use_color: Whether to use ANSI colors (default: True)

    Returns:
        UserInterface instance appropriate for the mode

    Example:
        >>> ui = make_ui(UIMode.PRETTY, total_files=50)
        >>> ui.start()
        >>> for file in files:
        ...     ui.update_file(file)
        ...     # Process file
        ...     ui.report_result(file, changed=True)
        >>> ui.finish()
    """
```

## Classes

### UserInterface (Abstract Base)

```python
class UserInterface(ABC):
    """Abstract base class for all UI implementations.

    Defines the interface that all UI modes must implement.
    Handles the lifecycle of a formatting session.
    """

    @abstractmethod
    def start(self) -> None:
        """Initialize the UI and display initial state."""

    @abstractmethod
    def update_file(self, file_path: Path) -> None:
        """Update UI to show current file being processed."""

    @abstractmethod
    def report_result(self, file_path: Path, changed: bool, error: Optional[str] = None) -> None:
        """Report the result of processing a file."""

    @abstractmethod
    def finish(self) -> None:
        """Finalize the UI and display summary."""

    @abstractmethod
    def error(self, message: str) -> None:
        """Display an error message."""
```

### PrettyUI

```python
class PrettyUI(UserInterface):
    """Rich terminal UI with progress bars and live updates.

    Features:
        - Unicode progress bar with percentage
        - Live statistics in footer
        - Color-coded results
        - Spinner animation during processing
        - Automatic terminal size detection

    Example output:
        Formatting Ada files... ━━━━━━━━━━ 45% 23/51 files
        Files: 51(45%) | ✓ Changed: 12(52%) | ✓ Unchanged: 11(48%) | ✗ Failed: 0(0%)
    """
```

#### Terminal Requirements

- Supports ANSI escape codes
- UTF-8 encoding for Unicode characters
- Minimum width: 80 columns
- Automatic fallback to PlainUI if unsupported

#### Footer Format

```
Files: {total}({percentage}%) | ✓ Changed: {changed}({changed_pct}%) | ✓ Unchanged: {unchanged}({unchanged_pct}%) | ✗ Failed: {failed}({failed_pct}%)
Elapsed: {time}s | Rate: {files_per_second} files/s | ETA: {estimated_time}s
```

### PlainUI

```python
class PlainUI(UserInterface):
    """Simple text-based UI for basic terminals and CI environments.

    Features:
        - Line-by-line progress updates
        - No special characters or colors
        - Works in any terminal
        - Suitable for log files

    Example output:
        Formatting 51 Ada files...
        [1/51] Formatting src/main.adb... done
        [2/51] Formatting src/utils.ads... changed
        [3/51] Formatting src/config.adb... error: syntax error

        Summary: 51 files processed (12 changed, 38 unchanged, 1 failed)
    """
```

### JsonUI

```python
class JsonUI(UserInterface):
    """Machine-readable JSON output for programmatic consumption.

    Outputs newline-delimited JSON (JSONL) for easy parsing.
    Each line is a complete JSON object representing an event.

    Event types:
        - start: Formatting session started
        - progress: File being processed
        - result: File processing complete
        - error: Error occurred
        - summary: Final statistics

    Example output:
        {"event": "start", "total_files": 51, "timestamp": "2025-01-14T10:30:45.123Z"}
        {"event": "progress", "file": "src/main.adb", "current": 1, "total": 51}
        {"event": "result", "file": "src/main.adb", "changed": true, "duration_ms": 125}
        {"event": "summary", "total": 51, "changed": 12, "unchanged": 38, "failed": 1}
    """
```

#### JSON Event Schemas

**Start Event:**
```json
{
    "event": "start",
    "total_files": 51,
    "timestamp": "2025-01-14T10:30:45.123Z",
    "version": "1.0.0"
}
```

**Progress Event:**
```json
{
    "event": "progress",
    "file": "src/main.adb",
    "current": 1,
    "total": 51,
    "timestamp": "2025-01-14T10:30:45.234Z"
}
```

**Result Event:**
```json
{
    "event": "result",
    "file": "src/main.adb",
    "changed": true,
    "duration_ms": 125,
    "edits": 5,
    "timestamp": "2025-01-14T10:30:45.345Z"
}
```

**Error Event:**
```json
{
    "event": "error",
    "file": "src/config.adb",
    "error": "Syntax error at line 42",
    "timestamp": "2025-01-14T10:30:45.456Z"
}
```

### QuietUI

```python
class QuietUI(UserInterface):
    """Minimal UI that only outputs errors and final summary.

    Features:
        - No progress updates
        - Only errors are displayed
        - Exit code indicates success/failure
        - Ideal for scripts and automation

    Example output:
        Error: src/config.adb - Syntax error at line 42
        1 file failed formatting
    """
```

## UI State Management

### FormattingState

```python
@dataclass
class FormattingState:
    """Tracks the state of a formatting session.

    Attributes:
        total_files: Total number of files to process
        processed: Number of files processed
        changed: Number of files that were modified
        unchanged: Number of files that were already formatted
        failed: Number of files that failed to format
        current_file: File currently being processed
        start_time: When formatting started

    Properties:
        percentage: Completion percentage (0-100)
        elapsed_time: Seconds since start
        files_per_second: Current processing rate
        estimated_remaining: Estimated seconds to completion
    """
```

## Terminal Handling

### Terminal Detection

```python
def detect_terminal_capabilities() -> TerminalCapabilities:
    """Detect terminal capabilities for UI selection.

    Returns:
        TerminalCapabilities with:
            - is_tty: Whether stdout is a terminal
            - supports_unicode: UTF-8 support
            - supports_color: ANSI color support
            - width: Terminal width in columns
            - height: Terminal height in rows
    """
```

### Color Support

```python
class Colors:
    """ANSI color codes for terminal output."""

    # Status colors
    SUCCESS = "\033[32m"    # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    INFO = "\033[34m"       # Blue

    # UI elements
    PROGRESS = "\033[36m"   # Cyan
    FOOTER = "\033[90m"     # Bright black (gray)

    # Reset
    RESET = "\033[0m"

    @staticmethod
    def strip_colors(text: str) -> str:
        """Remove ANSI color codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]+m', '', text)
```

## Progress Bar Implementation

### Unicode Progress Bar

```python
def draw_progress_bar(
    current: int,
    total: int,
    width: int = 40,
    filled_char: str = "━",
    empty_char: str = "━",
    style: str = "default"
) -> str:
    """Draw a Unicode progress bar.

    Args:
        current: Current progress value
        total: Maximum progress value
        width: Bar width in characters
        filled_char: Character for completed portion
        empty_char: Character for remaining portion
        style: Visual style (default, blocks, dots)

    Returns:
        Formatted progress bar string

    Example:
        >>> draw_progress_bar(45, 100, width=20)
        '━━━━━━━━━━          '
    """
```

### Progress Styles

```python
PROGRESS_STYLES = {
    "default": {
        "filled": "━",
        "empty": "━",
        "start": "",
        "end": "",
    },
    "blocks": {
        "filled": "█",
        "empty": "░",
        "start": "▐",
        "end": "▌",
    },
    "dots": {
        "filled": "●",
        "empty": "○",
        "start": "[",
        "end": "]",
    },
}
```

## Custom UI Implementation

### Creating a Custom UI

```python
class CustomUI(UserInterface):
    """Example custom UI implementation."""

    def __init__(self, total_files: int):
        self.total_files = total_files
        self.processed = 0
        self.results = []

    def start(self):
        print(f"🚀 Starting format of {self.total_files} files...")

    def update_file(self, file_path: Path):
        print(f"📝 Processing {file_path.name}...", end="", flush=True)

    def report_result(self, file_path: Path, changed: bool, error: Optional[str] = None):
        self.processed += 1

        if error:
            print(f" ❌ Error: {error}")
        elif changed:
            print(" ✅ Changed")
        else:
            print(" ✓ Already formatted")

        self.results.append({
            "file": file_path,
            "changed": changed,
            "error": error
        })

    def finish(self):
        changed = sum(1 for r in self.results if r["changed"])
        failed = sum(1 for r in self.results if r["error"])

        print(f"\n📊 Summary: {changed} changed, {failed} failed")

    def error(self, message: str):
        print(f"⚠️  {message}", file=sys.stderr)
```

## Async UI Updates

### Thread-Safe Updates

```python
class ThreadSafeUI(UserInterface):
    """UI that can be updated from multiple threads."""

    def __init__(self, base_ui: UserInterface):
        self.base_ui = base_ui
        self.lock = threading.Lock()

    def update_file(self, file_path: Path):
        with self.lock:
            self.base_ui.update_file(file_path)

    def report_result(self, file_path: Path, changed: bool, error: Optional[str] = None):
        with self.lock:
            self.base_ui.report_result(file_path, changed, error)
```

### Async Event Loop

```python
class AsyncUI(UserInterface):
    """Async UI for use with asyncio."""

    def __init__(self, total_files: int):
        self.total_files = total_files
        self.queue = asyncio.Queue()
        self.task = None

    async def start(self):
        self.task = asyncio.create_task(self._process_events())

    async def update_file(self, file_path: Path):
        await self.queue.put(("update", file_path))

    async def _process_events(self):
        while True:
            event_type, data = await self.queue.get()
            if event_type == "stop":
                break
            elif event_type == "update":
                self._render_update(data)
```

## Testing UI Components

### Mock Terminal

```python
class MockTerminal:
    """Mock terminal for testing UI components."""

    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self.output = []

    def write(self, text: str):
        self.output.append(text)

    def get_output(self) -> str:
        return "".join(self.output)

    def clear(self):
        self.output.clear()

# Test example
def test_pretty_ui():
    terminal = MockTerminal()
    ui = PrettyUI(total_files=10, output_stream=terminal)

    ui.start()
    ui.update_file(Path("test.adb"))
    ui.report_result(Path("test.adb"), changed=True)
    ui.finish()

    output = terminal.get_output()
    assert "━" in output  # Progress bar
    assert "100%" in output  # Completion
```

## Performance Considerations

### Update Throttling

```python
class ThrottledUI(UserInterface):
    """UI that throttles updates to prevent flicker."""

    def __init__(self, base_ui: UserInterface, min_interval: float = 0.1):
        self.base_ui = base_ui
        self.min_interval = min_interval
        self.last_update = 0

    def update_file(self, file_path: Path):
        now = time.time()
        if now - self.last_update >= self.min_interval:
            self.base_ui.update_file(file_path)
            self.last_update = now
```

### Buffered Output

```python
class BufferedUI(UserInterface):
    """UI with buffered output for performance."""

    def __init__(self, base_ui: UserInterface, buffer_size: int = 1024):
        self.base_ui = base_ui
        self.buffer = []
        self.buffer_size = buffer_size

    def _flush_buffer(self):
        if self.buffer:
            self.base_ui.write("".join(self.buffer))
            self.buffer.clear()

    def write(self, text: str):
        self.buffer.append(text)
        if sum(len(s) for s in self.buffer) >= self.buffer_size:
            self._flush_buffer()
```

## Best Practices

1. **Auto-detect Terminal**: Use AUTO mode to select appropriate UI
2. **Handle Interrupts**: Gracefully handle Ctrl+C
3. **Test All Modes**: Ensure all UI modes work correctly
4. **Respect NO_COLOR**: Honor the NO_COLOR environment variable
5. **Buffer Output**: Use buffering for high-frequency updates
6. **Thread Safety**: Ensure UI updates are thread-safe

## See Also

- [CLI Module](./cli.md) - UI mode selection
- [Rich Library](https://rich.readthedocs.io/) - Advanced terminal UI
- [ANSI Escape Codes](https://en.wikipedia.org/wiki/ANSI_escape_code)
