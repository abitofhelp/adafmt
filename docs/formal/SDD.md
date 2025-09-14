# Software Design Document (SDD)
# adafmt - Ada Language Formatter

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

## 1. Introduction

### 1.1 Purpose

This Software Design Document (SDD) describes the architecture, components, and implementation details of adafmt. It serves as a technical reference for developers working on or with the system.

### 1.2 Scope

This document covers:
- System architecture and component relationships
- Detailed design of each major component
- Key algorithms and data flows
- Interface specifications
- Design decisions and trade-offs

### 1.3 Related Documents

- [Software Requirements Specification (SRS)](SRS.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [README](../README.md)

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                         │
│                           (cli.py)                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
       ┌───────────────┴───────────────┬────────────────┐
       │                               │                │
       ▼                               ▼                ▼
┌──────────────┐             ┌──────────────┐  ┌──────────────┐
│     TUI      │             │  ALS Client  │  │     File     │
│   Manager    │             │   (Async)    │  │  Discovery   │
│  (tui.py)    │             │(als_client.py)│  │(file_disc.py)│
└──────────────┘             └──────┬───────┘  └──────────────┘
                                     │
                            ┌────────┴────────┐
                            │                 │
                            ▼                 ▼
                    ┌──────────────┐  ┌──────────────┐
                    │    Edits     │  │   Logger     │
                    │   Engine     │  │   (JSONL)    │
                    │ (edits.py)   │  │(logging.py)  │
                    └──────────────┘  └──────────────┘
```

### 2.2 Component Overview

| Component | Responsibility | Key Interfaces |
|-----------|---------------|----------------|
| CLI | Command parsing, orchestration | ArgParser, main() |
| TUI Manager | UI mode selection and display | CursesUI factory |
| ALS Client | LSP communication, process management | ALSClient class |
| File Discovery | Ada source file location | discover_files() |
| Edits Engine | TextEdit application, diff generation | apply_text_edits() |
| Logger | Structured logging | JsonlLogger class |
| Utils | Path validation, atomic writes | Various utilities |

### 2.3 Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Async-First**: Core processing uses Python asyncio for non-blocking I/O
3. **Fail-Safe**: Errors in one file don't stop processing of others
4. **Observable**: Comprehensive logging for debugging and monitoring
5. **Pluggable**: UI modes can be extended without changing core logic

## 3. Component Design

### 3.1 CLI Component (cli.py)

**Purpose**: Entry point and orchestration layer

**Key Classes/Functions**:
```python
def main() -> int:
    """Main entry point returning exit code"""
    
def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments"""
    
async def process_files(als_client, files, config):
    """Main file processing loop"""
```

**Flow**:
1. Parse arguments with validation
2. Generate a single timestamp at startup for all log files in this run
3. Generate default log filenames with the shared timestamp if not provided (ensures write-only access and correlation)
4. Set up environment (preflight checks)
5. Initialize ALS client
6. Discover files to process
7. Create UI instance
8. Process each file with error handling
9. Display summary and cleanup

**Design Decisions**:
- Uses argparse for robust CLI parsing
- Validates absolute paths early to catch errors
- Supports environment variable defaults
- Single UI instance for entire session
- Generates one timestamp at startup that is shared by all log files for easy correlation
- The shared timestamp ensures JSONL and stderr logs from the same run can be matched

### 3.2 ALS Client Component (als_client.py)

**Purpose**: Manage Ada Language Server communication

**Key Classes**:
```python
class ALSClient:
    """Async client for Ada Language Server communication"""
    
    async def start(self):
        """Start ALS process and initialize"""
        
    async def format_file(self, file_path: str) -> List[TextEdit]:
        """Format a single file"""
        
    async def shutdown(self):
        """Clean shutdown of ALS"""
```

**Protocol Implementation**:
- JSON-RPC 2.0 over stdio
- Request correlation via unique IDs
- Async request/response handling
- Timeout management per request

**Process Management**:
```python
async def _pump_stderr(self):
    """Capture stderr to timestamped file"""
```

**Error Handling**:
- Distinguishes syntax errors (code -32803) from other errors
- Verifies GNATFORMAT syntax errors with compiler
- Tracks false positives separately
- Writes detailed error info to stderr with timestamps

**Design Decisions**:
- Direct subprocess invocation
- Stderr capture for debugging
- Graceful degradation on errors
- Metrics tracking (start_ns, end_ns)
- Compiler verification for syntax error validation

### 3.3 TUI Component (tui.py)

**Purpose**: Provide adaptive terminal UI

**Factory Pattern**:
```python
def make_ui(mode: str = "auto") -> Optional[BaseUI]:
    """Create a UI instance based on mode and environment"""
```

**UI Implementations**:

1. **Pretty Mode** (PrettyCursesUI):
   - Full curses with multi-line footer
   - Header, scrolling content, 5-line footer
   - Color support for status
   - Progress indicators
   - Fixed-width formatting to prevent "dancing"

2. **Basic Mode** (BasicCursesUI):
   - Simplified curses with footer
   - Thread-safe updates from async code
   - Consistent separator coloring

3. **Plain Mode** (PlainUI):
   - Simple print() calls
   - No terminal control
   - CI/redirect friendly
   - Colors failed status in red when TTY detected

**Footer Design**:
```
Files: 100(100%) | ✓ Changed: 50( 50%) | ✓ Unchanged: 45( 45%) | ✗ Failed: 5(  5%)
Elapsed:  123.4s | Rate: 0.8 files/s
Log:     ./adafmt_20250115_100000_log.jsonl (default location)
Stderr:  ./adafmt_20250115_100000_stderr.log (default location)
ALS Log: ~/.als/ada_ls_log.*.log (default location)
```

**Design Decisions**:
- Automatic fallback chain: pretty → basic → plain
- Same interface for all modes (BaseUI)
- Thread-based rendering for curses modes
- Fixed-width formatting for stable UI
- Environment variable support (ADAFMT_UI_FORCE, ADAFMT_UI_DEBUG)

### 3.4 File Discovery Component (file_discovery.py)

**Purpose**: Locate Ada source files

**Key Function**:
```python
def discover_files(
    include_paths: List[str],
    exclude_paths: List[str],
    explicit_files: List[str]
) -> Tuple[List[str], List[str]]:
    """Discover Ada files to process"""
```

**Algorithm**:
1. Process explicit files first
2. Walk include directories
3. Skip exclude directories
4. Filter by extension (.ads, .adb, .ada)
5. Remove duplicates
6. Sort for consistent ordering

**Design Decisions**:
- Explicit files override excludes
- Case-insensitive extension matching
- Absolute path normalization
- Error collection for invalid paths

### 3.5 Edits Component (edits.py)

**Purpose**: Apply LSP TextEdits to files

**Key Functions**:
```python
def apply_text_edits(original: str, edits: List[TextEdit]) -> str:
    """Apply LSP edits to text"""
    
def unified_diff(a: str, b: str, path: str) -> str:
    """Generate unified diff"""
```

**LSP Position Handling**:
- Convert line/character to byte offsets
- Handle UTF-16 positions correctly
- Apply edits in reverse order
- Preserve newline conventions

**Design Decisions**:
- Pure functions (no side effects)
- Efficient offset calculation
- Standard unified diff format
- Handles empty edits arrays

### 3.6 Logger Component (logging_jsonl.py)

**Purpose**: Structured logging for analysis

**Format**:
```json
{"path": "/src/file.ads", "status": "ok", "duration_ms": 125}
{"path": "/src/bad.adb", "status": "failed", "error": "syntax error"}
{"summary": {"total": 100, "ok": 98, "failed": 2, "duration_s": 45.3}}
```

**Stderr Error Format**:
```
[2025-01-13 14:30:22] SYNTAX_ERROR_CONFIRMED: File failed to format
File: /path/to/example.adb
Error: Syntactically invalid code
Details: Missing semicolon at line 42, column 15
Action: Fix syntax errors in the file and retry
```

**Design Decisions**:
- Always-on logging with timestamped default filenames
- Single timestamp generated at startup and shared by all log files in the same run
- Default log files use "./" prefix (e.g., ./adafmt_20250113_143022_log.jsonl, ./adafmt_20250113_143022_stderr.log)
- Default paths display with "(default location)" suffix for clarity
- One JSON object per line
- Always write mode (never append) - guaranteed by unique timestamped filenames
- Human-readable timestamps
- Structured error details
- Environment variable support (ADAFMT_LOG_FILE_PATH)
- User-provided paths are displayed as-is, default paths show with "./" prefix and "(default location)"
- Log files persist beyond formatting run completion for post-run analysis
- Timestamps ensure unique filenames preventing overwrites between runs
- Multiple formatting runs accumulate separate log files enabling historical debugging
- Shared timestamp allows easy correlation of JSONL and stderr logs from the same run
- **Efficient File Handling**: Log files are opened once at startup and kept open for the entire session
- **Performance Optimization**: Avoids the overhead of repeatedly opening/closing files for each log entry
- **Crash Safety**: Each log entry is flushed to disk immediately after writing to ensure data persistence
- **Proper Cleanup**: All log files are properly closed during shutdown to prevent data loss
- **Universal Application**: This efficient file handling pattern applies to all log files (JSONL, stderr, etc.)
- **Dual Stderr Output**: Stderr error messages are written to both the stderr log file AND displayed on terminal simultaneously
- **Structured Error Reporting**: Each stderr error includes timestamp, error type, file path, error message, details, and user action
- **Error Type Classification**: Four distinct error types (SYNTAX_ERROR_CONFIRMED, ALS_PROTOCOL_ERROR, CONNECTION_ERROR, UNEXPECTED_ERROR)
- **Actionable Guidance**: Each error type has specific user actions to help resolve the issue
- **Real-time Display**: Errors appear on terminal immediately as they occur for better user feedback
- **Human-readable Format**: Stderr uses structured text format optimized for human reading vs JSONL for machine parsing

### 3.7 Utils Component (utils.py)

**Purpose**: Common utilities

**Key Functions**:
- `ensure_abs()`: Path validation
- `atomic_write()`: Safe file updates
- `preflight()`: ALS process management

**Preflight Process Management**:
The `preflight()` function handles existing ALS processes based on the mode:

| Mode | Behavior |
|------|----------|
| `off`/`none` | Skip all checks |
| `warn` | Report ALS processes and stale locks only |
| `fail` | Abort if ANY processes/locks found |
| `safe` (default) | Kill ALS older than `--als-stale-minutes` |
| `kill` | Same as `safe` |
| `kill+clean` | Kill stale ALS + remove stale locks |
| `aggressive` | Kill ALL ALS + remove all stale locks |

Process age is determined by parsing system process information.
Locks are stale if >10min old AND PID is dead.

**Cleanup Handler**:
The `_cleanup_handler()` ensures graceful shutdown:
- Registered for SIGINT, SIGTERM, and atexit
- Gracefully shuts down ALS client
- Closes UI and logger
- Restores original stderr if redirected
- Prevents orphaned ALS processes

**Atomic Write Algorithm**:
1. Write to temp file in same directory
2. Flush and sync to disk
3. Atomic rename to target
4. Handles cross-platform differences

## 4. Data Flow

### 4.1 File Processing Flow

```
File Path
    │
    ▼
Read Content ──────────┐
    │                  │
    ▼                  │
Send to ALS            │
    │                  │
    ▼                  │
Receive Edits          │
    │                  │
    ▼                  │
Apply Edits ───────────┤
    │                  │
    ▼                  ▼
Show Diff          Original
    │               (if error)
    ▼
Write File
(if --write)
```

### 4.2 LSP Message Flow

```
Client                          ALS
  │                              │
  ├──── initialize ─────────────▶│
  │◀──── initialized ────────────┤
  │                              │
  ├──── textDocument/didOpen ───▶│
  │                              │
  ├──── textDocument/formatting ▶│
  │◀──── TextEdit[] ─────────────┤
  │                              │
  ├──── textDocument/didClose ──▶│
  │                              │
  └──── (repeat for each file)   │
```

### 4.3 Error Recovery Flow

```
Format Request
    │
    ▼
Timeout? ──No──▶ Success
    │
   Yes
    │
    ▼
Recoverable? ──No──▶ Mark Failed
    │
   Yes
    │
    ▼
Retry Count? ──No──▶ Mark Failed
    │
   Yes
    │
    ▼
Exponential
Backoff
    │
    ▼
Retry Request
```

### 4.5 Error Reporting Flow

```
File Format Fails
    │
    ▼
Determine Error Type
    │
    ├─── Syntax Error (-32803)
    │    └──▶ SYNTAX_ERROR_CONFIRMED
    │
    ├─── Protocol Error
    │    └──▶ ALS_PROTOCOL_ERROR
    │
    ├─── Connection Lost
    │    └──▶ CONNECTION_ERROR
    │
    └─── Other Errors
         └──▶ UNEXPECTED_ERROR
             │
             ▼
    Format Error Message
             │
             ├──▶ Write to stderr file
             │
             └──▶ Display on terminal
                  │
                  ▼
         [2025-01-13 14:30:22] ERROR_TYPE: File failed to format
         File: /path/to/file.adb
         Error: Detailed error message
         Details: Additional context
         Action: User guidance
```

### 4.4 Error Type Classification

**Syntax Errors (Code -32803)**
- **Description**: Malformed Ada code that violates language grammar rules
- **Detection**: ALS returns error code -32803 "Syntactically invalid code"
- **Behavior**: Formatting fails, file marked as failed
- **Examples**:
  ```ada
  -- Missing semicolon
  procedure Hello is
  begin
    Put_Line("Hello")  -- Error: missing semicolon
  end Hello;
  
  -- Unmatched parentheses
  if (X > 5 then  -- Error: missing closing parenthesis
  ```

**Semantic Errors**
- **Description**: Syntactically valid code with semantic issues
- **Detection**: Compiler reports errors, but ALS formats successfully
- **Behavior**: Formatting succeeds, compilation fails
- **Examples**:
  ```ada
  -- Undefined type
  procedure Process is
    Event : Domain_Event;  -- Error: "Domain_Event" not declared
  begin
    null;
  end Process;
  
  -- Invalid component selection
  Data := Event.Field;  -- Error: invalid prefix in selected component
  ```

**Design Rationale**: ALS (gnatformat) is a syntax-aware formatter, not a semantic analyzer. This separation allows:
- Formatting partially complete code during development
- Working with files that have unresolved dependencies
- Faster formatting without full semantic analysis

## 5. Interface Specifications

### 5.1 CLI Interface

```bash
adafmt [OPTIONS] [FILES...]

Required:
  --project-file-path PATH     Absolute path to .gpr file

Optional:
  --include-path PATH         Include directory (multiple allowed)
  --exclude-path PATH         Exclude directory (multiple allowed)
  --write                     Apply changes (default: dry-run)
  --check                     Exit 1 if changes needed
  --diff/--no-diff           Show unified diffs (default: on)
  --ui-mode MODE             UI mode: pretty|basic|plain|off
  --alr-mode MODE            Alire mode: auto|yes|no
  --crate-dir PATH           Override Alire crate directory
  --log-path PATH            Override JSONL log location (default: ./adafmt_<timestamp>_log.jsonl)
  --stderr-path PATH         Override stderr capture location (default: ./adafmt_<timestamp>_stderr.log)
  --preflight-mode MODE      Handle existing ALS: warn|kill|fail
  --process-timeout N        Overall timeout (default: 300)
  --warmup-seconds N         ALS warmup time (default: 5.0)
  --format-timeout N         Per-file timeout (default: 30.0)
  --max-retry-attempts N     Retry count (default: 3)
```

### 5.2 Python API

```python
# Main entry point
def main() -> int:
    """Run adafmt, return exit code"""

# ALS Client
class ALSClient:
    async def start(self) -> None
    async def format_file(self, path: str) -> List[Dict]
    async def shutdown(self) -> None
    def summary(self) -> str

# File Discovery
def discover_files(
    include_paths: List[str],
    exclude_paths: List[str], 
    explicit_files: List[str]
) -> Tuple[List[str], List[str]]

# Edit Application
def apply_text_edits(
    original: str, 
    edits: List[Dict[str, Any]]
) -> str

# UI Factory
class CursesUI:
    def __new__(cls, title: str, version: str) -> UIProtocol
```

### 5.3 LSP Protocol Usage

**Supported LSP Methods**:
- `initialize`: Setup connection
- `initialized`: Confirm ready
- `textDocument/didOpen`: Open file
- `textDocument/formatting`: Request formatting
- `textDocument/didClose`: Close file
- `shutdown`: Begin shutdown
- `exit`: Terminate process

**TextEdit Structure**:
```json
{
  "range": {
    "start": {"line": 0, "character": 0},
    "end": {"line": 0, "character": 10}
  },
  "newText": "replacement"
}
```

## 6. Design Decisions and Rationale

### 6.1 Async Architecture

**Decision**: Use Python asyncio for all I/O operations

**Rationale**:
- Non-blocking communication with ALS
- Efficient subprocess management
- Future-proof for parallel processing
- Clean timeout handling

### 6.2 UI Factory Pattern

**Decision**: Factory class returning different implementations

**Rationale**:
- Transparent fallback for environments
- Single interface for all modes
- Easy to add new UI modes
- No runtime type checking needed

### 6.3 Atomic File Writes

**Decision**: Write to temp file, then rename

**Rationale**:
- Prevents corruption on crash
- Works across platforms
- Preserves file attributes
- Industry standard approach

### 6.4 Stderr Capture

**Decision**: Capture ALS stderr to timestamped file

**Rationale**:
- Critical for debugging
- Preserves timing information
- Doesn't interfere with JSON-RPC
- Optional for performance

### 6.5 Retry Logic

**Decision**: Exponential backoff for recoverable errors

**Rationale**:
- Handles transient network issues
- Prevents overwhelming ALS
- Configurable for different environments
- Clear distinction of error types

### 6.6 Detailed Stderr Error Reporting

**Decision**: Write structured error information to stderr with timestamps and actionable guidance

**Rationale**:
- Immediate visibility of failures on terminal
- Structured format aids in quick problem identification
- Error type classification helps users understand root cause
- Actionable guidance reduces support burden
- Dual output (terminal + file) supports both interactive and CI use cases
- Human-readable format complements machine-parseable JSONL logs

**Error Type Design**:
- **SYNTAX_ERROR_CONFIRMED**: Clear indication of Ada syntax issues
- **ALS_PROTOCOL_ERROR**: Distinguishes protocol/communication failures
- **CONNECTION_ERROR**: Network/pipe specific errors for retry guidance
- **UNEXPECTED_ERROR**: Catch-all with log file reference for investigation

## 7. Performance Considerations

### 7.1 Optimizations

1. **Single ALS Process**: Reuse for all files
2. **Streaming Reads**: Don't load all files at once
3. **Lazy Imports**: Import curses only when needed
4. **Efficient Diffs**: Use Python's optimized difflib
5. **Minimal Allocations**: Reuse buffers where possible
6. **Efficient Log File I/O**: Keep log files open for the session duration, avoiding repeated open/close operations
7. **Immediate Flush**: Flush after each write for crash safety without sacrificing performance

### 7.2 Bottlenecks

1. **ALS Startup**: Mitigated by warmup period
2. **Large Files**: Consider chunking in future
3. **Network Filesystems**: Atomic writes may be slow
4. **Terminal Output**: UI modes for different needs

## 8. Security Considerations

### 8.1 Input Validation

- All paths validated as absolute
- No shell command injection
- Safe temp file creation
- Proper quote handling

### 8.2 Process Isolation

- ALS runs as subprocess
- No shared memory
- Limited to stdio communication
- Proper cleanup on exit

### 8.3 File Safety

- Atomic writes prevent corruption
- Original preserved until success
- Permission preservation
- No execute bits changed

## 9. Testing Strategy

### 9.1 Unit Tests

- Pure functions (edits, discovery)
- Mock-based (ALS client)
- UI mode selection logic
- Path validation

### 9.2 Integration Tests

- Real ALS communication
- File system operations
- End-to-end formatting
- Error scenarios

### 9.3 System Tests

- Multiple platform testing
- Performance benchmarks
- Stress testing (many files)
- UI mode verification

## 10. Future Enhancements

### 10.1 Parallel Processing

```python
async def format_files_parallel(files: List[str], workers: int = 4):
    """Format multiple files concurrently"""
```

### 10.2 Incremental Formatting

- Cache file hashes
- Format only changed files
- LSP incremental sync

### 10.3 Configuration File

```toml
# .adafmt.toml
[settings]
project_file = "project.gpr"
include_paths = ["src", "tests"]
exclude_paths = ["build"]

[formatting]
timeout = 60
retry_attempts = 5
```

### 10.4 Watch Mode

```python
async def watch_mode(paths: List[str]):
    """Auto-format on file changes"""
```

## 11. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-12-01 | M. Gardner | Initial version |