# Software Design Document (SDD)
# adafmt - Ada Language Formatter

**Document Version:** 0.0.0  
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
                            ┌────────┴────────────┐
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐      ┌──────────────┐
                    │    Edits     │      │   Pattern    │
                    │   Engine     │─────▶│  Formatter   │
                    │ (edits.py)   │      │(pattern_fmt) │
                    └──────────────┘      └──────────────┘
                            │                     │
                            └──────┬──────────────┘
                                   │
                                   ▼
                           ┌──────────────┐
                           │   Logger     │
                           │   (JSONL)    │
                           │(logging.py)  │
                           └──────────────┘
```

### 2.2 Component Overview

| Component | Responsibility | Key Interfaces |
|-----------|---------------|----------------|
| CLI | Command parsing, orchestration | ArgParser, main() |
| TUI Manager | TTY output and display | Plain text UI |
| ALS Client | LSP communication, process management | ALSClient class |
| File Discovery | Ada source file location | discover_files() |
| Edits Engine | TextEdit application, diff generation | apply_text_edits() |
| Pattern Formatter | Post-ALS pattern-based formatting | PatternFormatter class |
| Logger | Structured logging | JsonlLogger class |
| Utils | Path validation, atomic writes | Various utilities |

### 2.3 Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Async-First**: Core processing uses Python asyncio for non-blocking I/O
3. **Fail-Safe**: Errors in one file don't stop processing of others
4. **Observable**: Comprehensive logging for debugging and monitoring
5. **Clear Output**: Plain text output suitable for all terminals

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
Pat Log: ./adafmt_20250115_100000_patterns.log (default location)
Stderr:  ./adafmt_20250115_100000_stderr.log (default location)
ALS Log: ~/.als/ada_ls_log.*.log (default location)
```

**Design Decisions**:
- Automatic fallback chain: pretty → basic → plain
- Same interface for all modes (BaseUI)
- Thread-based rendering for curses modes
- Fixed-width formatting for stable UI
- Environment variable support (ADAFMT_UI_FORCE, ADAFMT_UI_DEBUG)

#### 3.3.1 Comprehensive Output Format Implementation

**Purpose**: Implements FR-12 standardized output formatting for TTY output

**Output Structure Implementation**:
```python
class OutputFormatter:
    """Handles standardized output formatting across TTY output"""
    
    def format_final_summary(self, 
                           als_metrics: ALSMetrics,
                           pattern_metrics: PatternMetrics, 
                           run_summary: RunSummary,
                           log_paths: LogPaths) -> str:
        """Generate standardized output sections"""
        sections = [
            self._format_als_metrics(als_metrics),
            self._format_pattern_metrics(pattern_metrics),
            self._format_run_summary(run_summary),
            self._format_log_files(log_paths)
        ]
        delimiter = "=" * 80
        return f"{delimiter}\n" + f"\n{delimiter}\n".join(sections) + f"\n{delimiter}"
```

**DateTime Format Implementation**:
- Uses `datetime.strftime('%Y%m%dT%H%M%SZ')` for ISO 8601 UTC timestamps
- Elapsed time formatting: `f"{seconds:.1f}s"` for one decimal place
- Consistent timezone handling through UTC conversion before formatting
- Timestamp generation at run start shared across all log files

**Column Alignment Implementation**:
```python
def _format_metrics_table(self, metrics: List[Tuple]) -> str:
    """Fixed-width column formatting with alignment"""
    # Calculate maximum width for each column
    widths = [max(len(str(row[i])) for row in metrics) for i in range(len(metrics[0]))]
    
    # Apply minimum widths and alignment rules
    format_str = " ".join(f"{{:{width}}}" for width in widths)
    
    # Right-align numeric columns, left-align text columns
    aligned_format = self._apply_column_alignment(format_str, metrics)
    
    return "\n".join(aligned_format.format(*row) for row in metrics)
```

**Cross-Platform Display Implementation**:
- UTF-8 encoding with ASCII fallbacks for special characters
- Terminal width detection using `os.get_terminal_size()` with 80-column minimum
- Windows-specific handling for color codes and character encoding
- Platform-specific path display normalization

**Color Formatting Implementation**:
```python
class ColorFormatter:
    """Handles color and visual formatting with fallbacks"""
    
    COLORS = {
        'success': '\033[32m',  # Green
        'warning': '\033[33m',  # Yellow  
        'error': '\033[31m',    # Red
        'header': '\033[1m',    # Bold
        'reset': '\033[0m'      # Reset
    }
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color with NO_COLOR environment variable support"""
        if os.environ.get('NO_COLOR') or not self._supports_color():
            return text
        return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
```

**Error Handling Integration**:
- Partial output display when individual sections fail
- Graceful degradation for missing metrics data
- Error indicators integrated into normal output structure
- Consistent formatting maintained during error conditions

**Format Validation Implementation**:
- Input validation for all metrics data before formatting
- Numeric range checking (percentages 0-100, non-negative counts)
- Timestamp validation and timezone consistency
- Output format verification against FR-12 requirements

#### 3.3.2 UI Mode Format Integration

**Pretty Mode Enhancement**:
- Renders comprehensive output with color highlighting
- Progress indicators during processing with live metric updates
- Interactive elements for large output sections
- Full color scheme implementation per FR-12.9

**Plain Mode Enhancement**:
- Simplified rendering without colors or special characters
- Optimized for log file capture and CI/CD environments
- ASCII-only character set for maximum compatibility
- Structured output suitable for parsing by external tools

**JSON Mode Implementation**:
```python
def format_json_output(self, data: Dict) -> str:
    """Structured JSON output for programmatic consumption"""
    json_events = [
        {"type": "als_metrics", "timestamp": self._now_iso(), "data": data.als_metrics},
        {"type": "pattern_metrics", "timestamp": self._now_iso(), "data": data.pattern_metrics},
        {"type": "run_summary", "timestamp": self._now_iso(), "data": data.run_summary},
        {"type": "log_files", "timestamp": self._now_iso(), "data": data.log_paths}
    ]
    return "\n".join(json.dumps(event, ensure_ascii=False) for event in json_events)
```

**Design Rationale**:
- **Separation of Concerns**: Formatting logic separated from output mode logic
- **Testability**: Each format component independently testable
- **Extensibility**: New output formats can be added without modifying TTY output
- **Performance**: Pre-calculated formatting reduces real-time computation
- **Consistency**: Shared formatting ensures identical output across modes
- **Maintainability**: Single source of truth for format specifications

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

**Pattern Log Format**:
```json
{"ev": "run_start", "ts": "2025-09-15T14:30:22", "patterns_path": "./adafmt_patterns.json", "patterns_loaded": 5, "mode": "dry", "timeout_ms": 50, "max_bytes": 10485760}
{"ev": "file", "ts": "2025-09-15T14:30:23", "path": "/src/main.adb", "als_ok": true, "als_edits": 3, "patterns_applied": ["comment-norm", "operator-add"], "replacements": 5}
{"ev": "pattern", "ts": "2025-09-15T14:30:23", "path": "/src/main.adb", "name": "comment-norm", "title": "Normalize comment spacing", "category": "comment", "replacements": 3}
{"ev": "pattern_timeout", "ts": "2025-09-15T14:30:24", "path": "/src/utils.adb", "name": "complex-rule", "title": "Complex pattern", "category": "hygiene", "timeout_ms": 50}
{"ev": "run_end", "ts": "2025-09-15T14:30:30", "files_total": 10, "files_als_ok": 9, "patterns_loaded": 5, "patterns_summary": {"comment-norm": {"files_touched": 8, "replacements": 24}}}
```

**Pattern Log Design**:
- Separate JSONL file for pattern activity: `adafmt_<timestamp>_patterns.log`
- Shares same timestamp as main log and stderr log for correlation
- Events: `run_start`, `file`, `pattern`, `pattern_error`, `pattern_timeout`, `file_skipped_large`, `validation_check`, `run_end`
- Pattern events include name, title, and category for analysis
- Summary includes only patterns with `files_touched > 0`

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

### 3.8 Pattern Formatter Component (pattern_formatter.py)

**Purpose**: Post-ALS pattern-based formatting to enforce additional style rules

**Architecture**:
```
ALS Formatted Buffer
        │
        ▼
┌──────────────────┐
│Pattern Formatter │
│  - Load patterns │
│  - Apply rules   │
│  - Track metrics │
└────────┬─────────┘
         │
         ├──→ UI Status Update
         ├──→ Pattern Log (JSONL)
         └──→ Final Buffer
```

**Key Classes**:
```python
class PatternFormatter:
    """Manages pattern-based post-processing"""
    
    def __init__(self, rules: Tuple[CompiledRule, ...], enabled: bool):
        self.rules = rules
        self.enabled = enabled
        self.files_touched: Dict[str, int] = {}
        self.replacements: Dict[str, int] = {}
    
    @classmethod
    def load_from_json(cls, path: Path, logger, ui) -> PatternFormatter:
        """Load and compile patterns from JSON file"""
    
    def apply(self, path: Path, text: str, logger, ui) -> Tuple[str, FileApplyResult]:
        """Apply patterns to text with timeout protection"""

class CompiledRule:
    """Compiled pattern rule"""
    name: str  # 12-char identifier
    title: str  # Human-readable description
    category: str  # comment|operator|delimiter|declaration|attribute|hygiene
    find: Pattern  # Compiled regex
    replace: str  # Replacement text
```

**Pattern Loading**:
1. Load JSON file at startup (default: `./adafmt_patterns.json`)
2. Validate schema:
   - `name`: exactly 12 chars, `^[a-z0-9_-]{12}$`
   - `title`: 1-80 characters
   - `category`: predefined set
   - `find`/`replace`: required strings
3. Compile regex patterns with flags
4. Close file immediately (even on exception)
5. Sort by name for deterministic order

**Pattern Application**:
1. Skip if ALS failed (only process syntactically valid code)
2. Check file size limit (default 10MB)
3. Apply patterns sequentially with timeout (default 50ms)
4. Count replacements per pattern
5. Update UI status line
6. Log to pattern log

**Safety Features**:
- **Regex timeout**: Prevent ReDoS attacks via regex module timeout
- **File size limit**: Skip large files to prevent memory issues
- **Error isolation**: Pattern errors don't break formatting pipeline
- **Validation mode**: Optional ALS re-check of pattern output

**Pattern Validation Mode** (`--validate-patterns`):
```
Pattern Output → ALS Format Check → Report Conflicts
```

**Design Decisions**:
- Immutable pattern set after loading
- Per-pattern timeout enforcement
- Deterministic application order
- Separate pattern log for debugging
- Integration with existing UI/logging

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
    ▼                  │
Pattern Formatter      │
(if enabled)           │
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

### 4.6 Pattern Processing Flow

```
ALS Success?
    │
    ├──No──▶ Skip Patterns
    │
   Yes
    │
    ▼
File Size Check
    │
    ├──>10MB──▶ Log file_skipped_large
    │
   ≤10MB
    │
    ▼
For Each Pattern (sorted by name):
    │
    ▼
Apply with Timeout
    │
    ├──Timeout──▶ Log pattern_timeout
    │             Continue to next
    │
    ├──Error────▶ Log pattern_error
    │             Continue to next
    │
   Success
    │
    ▼
Count Replacements
    │
    ▼
Next Pattern
    │
    ▼
Update UI Status
    │
    ▼
Write Pattern Log
```

### 4.7 Pattern Validation Flow (`--validate-patterns`)

```
Pattern Output
    │
    ▼
Send to ALS for Format Check
    │
    ▼
ALS Would Make Changes?
    │
    ├──Yes──▶ Log validation_check
    │         │
    │         ├──warn mode──▶ Continue
    │         │
    │         └──strict mode──▶ Track for exit code
    │
   No
    │
    ▼
Pattern Valid
```

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
  --diff/--no-diff           Show unified diffs (default: on)
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
- Easy to add new TTY output
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

### 6.7 Pattern Formatter Design

**Decision**: Post-ALS pattern application as a separate stage

**Rationale**:
- Clear separation of concerns (ALS handles syntax, patterns handle style)
- Only process syntactically valid code (safer and more predictable)
- Patterns can be disabled without affecting core formatting
- Easier to test and debug patterns in isolation
- Allows gradual adoption of style rules

**Safety Decisions**:
- **Regex timeouts**: Prevent ReDoS attacks and hanging
- **File size limits**: Avoid memory exhaustion on large files
- **Error isolation**: Pattern errors don't break the formatter
- **Immutable patterns**: Load once, never modify during run
- **Deterministic order**: Sort by name for reproducible results

## 7. Performance Considerations

### 7.1 Optimizations

1. **Single ALS Process**: Reuse for all files
2. **Streaming Reads**: Don't load all files at once
3. **Lazy Imports**: Import curses only when needed
4. **Efficient Diffs**: Use Python's optimized difflib
5. **Minimal Allocations**: Reuse buffers where possible
6. **Efficient Log File I/O**: Keep log files open for the session duration, avoiding repeated open/close operations
7. **Immediate Flush**: Flush after each write for crash safety without sacrificing performance
8. **Pattern Compilation**: Compile patterns once at startup, not per file
9. **Pattern Timeouts**: 50ms default prevents hanging on complex patterns

### 7.2 Bottlenecks

1. **ALS Startup**: Mitigated by warmup period
2. **Large Files**: Consider chunking in future
3. **Network Filesystems**: Atomic writes may be slow
4. **Terminal Output**: TTY output for different needs
5. **Pattern Complexity**: Mitigated by timeouts and file size limits

## 8. Security Considerations

### 8.1 Input Validation

#### Path Validation
- Relative paths are resolved to absolute paths using current working directory
- Resolved paths are validated for illegal characters:
  - Unicode characters outside BMP (U+10000+)
  - ISO control characters
  - Whitespace characters
  - Characters not matching: [A-Za-z0-9?&=._:/-]
  - Directory traversal sequences (..)
- No shell command injection
- Safe temp file creation
- Proper quote handling

#### Command-Line Flag Validation Matrix

The CLI validates flag combinations to prevent conflicting or nonsensical operations:

| Flag Combination | Validation Rule | Error Message | Exit Code |
|------------------|----------------|---------------|-----------|
| `--no-als` + `--no-patterns` | Mutually exclusive | "Cannot use both --no-patterns and --no-als (nothing to do)" | 2 |
| `--validate-patterns` + `--no-als` | Validation requires ALS | "Cannot use --validate-patterns with --no-als (validation requires ALS)" | 2 |
| `--validate-patterns` + `--no-patterns` | No patterns to validate | "Cannot use --validate-patterns with --no-patterns (no patterns to validate)" | 2 |
| `--write` + `--check` | Conflicting output modes | "Cannot use both --write and --check modes" | 2 |
| No paths + No files | Input required | "No files or directories to process. You must provide --include-path or specific files." | 2 |

#### Validation Implementation

```python
def validate_cli_args(args):
    """Validate command-line arguments for conflicts"""
    # Flag combination checks
    if args.no_als and args.no_patterns:
        raise ValueError("Cannot use both --no-patterns and --no-als")
    
    if args.validate_patterns and args.no_als:
        raise ValueError("Cannot use --validate-patterns with --no-als")
    
    # Path validation
    for path in args.include_paths + args.exclude_paths:
        error = validate_path(path)
        if error:
            raise ValueError(f"Invalid path: {error}")
    
    # Input requirement check
    if not args.include_paths and not args.files:
        raise ValueError("No input files or directories specified")
```

This validation ensures:
1. Users cannot specify contradictory options
2. All paths are safe and well-formed
3. The tool has sufficient input to operate
4. Clear error messages guide users to correct usage

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

### 8.4 Pattern Security

- **ReDoS Protection**: Regex timeout enforcement prevents attacks
- **Trusted Input**: Pattern files must be from trusted sources
- **Memory Limits**: File size caps prevent exhaustion
- **Error Isolation**: Malformed patterns can't crash formatter
- **No Code Execution**: Patterns are data, not executable code

## 9. Testing Strategy

### 9.1 Unit Tests

- Pure functions (edits, discovery)
- Mock-based (ALS client)
- output mode selection logic
- Path validation
- Pattern loading and validation
- Pattern timeout enforcement
- Pattern application logic

### 9.2 Integration Tests

- Real ALS communication
- File system operations
- End-to-end formatting
- Error scenarios
- Pattern formatter with ALS
- Pattern validation mode
- Large file handling

### 9.3 System Tests

- Multiple platform testing
- Performance benchmarks
- Stress testing (many files)
- output mode verification
- Pattern performance impact
- ReDoS prevention verification

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
| 0.0.0 | January 2025 | M. Gardner | Initial version |