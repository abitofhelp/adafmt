# Software Requirements Specification (SRS)
# adafmt - Ada Language Formatter

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document defines the functional and non-functional requirements for adafmt, a command-line tool that formats Ada source code using the Ada Language Server (ALS). This document serves as a comprehensive guide for developers, testers, and stakeholders to understand the system's capabilities and constraints.

### 1.2 Scope

adafmt is designed to:
- Format Ada source files (.ads, .adb, .ada) using the Ada Language Server
- Integrate seamlessly with modern Ada development workflows
- Support standalone GNAT projects
- Provide multiple user interface modes for different use cases
- Enable CI/CD integration through robust exit codes and logging

The system operates as a client to the Ada Language Server, communicating via the Language Server Protocol (LSP) over standard I/O streams.

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|------------|
| ALS | Ada Language Server - The language server implementation for Ada |
| LSP | Language Server Protocol - Microsoft's protocol for language tooling |
| JSON-RPC | JSON Remote Procedure Call protocol used by LSP |
| JSONL | JSON Lines - A format where each line is a valid JSON object |
| GPR | GNAT Project file (.gpr extension) |
| Spec | Ada specification file (.ads) |
| Body | Ada implementation file (.adb) |
| UI | User Interface |
| CI/CD | Continuous Integration/Continuous Deployment |

### 1.4 System Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │────▶│   adafmt    │────▶│     ALS     │
│  (CLI/CI)   │     │   (Python)  │     │   (Ada)     │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │ Ada Source  │
                    │    Files    │
                    └─────────────┘
```

## 2. Functional Requirements

### 2.1 File Discovery and Selection (FR-1)

**Description:** The system shall discover Ada source files for formatting based on user-specified criteria.

**Requirements:**
- FR-1.1: SHALL support recursive directory traversal for `--include-path` directories
- FR-1.2: SHALL exclude directories specified via `--exclude-path` from traversal
- FR-1.3: SHALL recognize files with extensions: `.ads`, `.adb`, `.ada`
- FR-1.4: SHALL support explicit file paths as positional arguments
- FR-1.5: SHALL process explicitly named files even if they're in excluded directories
- FR-1.6: SHALL require all path arguments to be absolute paths

**Acceptance Criteria:**
- Given a directory structure, the system correctly identifies all Ada files
- Excluded directories are not traversed
- Mixed explicit files and directory scanning work correctly

### 2.2 ALS Process Management (FR-2)

**Description:** The system shall manage the Ada Language Server lifecycle.

**Requirements:**
- FR-2.1: SHALL spawn ALS as a subprocess with JSON-RPC over stdio
- FR-2.2: SHALL support three ALS invocation modes:
  - Direct: `ada_language_server` command
  - Direct: `ada_language_server`
- FR-2.3: SHALL detect and report existing ALS processes via preflight checks
- FR-2.4: SHALL support killing existing ALS processes when requested
- FR-2.5: SHALL wait for ALS initialization (configurable warmup period)
- FR-2.6: SHALL cleanly terminate ALS on exit or error
- FR-2.7: SHALL capture ALS stderr to a timestamped file when requested
- FR-2.8: SHALL track ALS process metrics (start time, end time, stderr lines)
- FR-2.9: SHALL register cleanup handlers for SIGINT, SIGTERM, and normal exit
- FR-2.10: SHALL perform cleanup operations including:
  - Graceful ALS client shutdown
  - UI closure
  - Logger closure
  - Stderr restoration if redirected

**Acceptance Criteria:**
- ALS starts successfully in all three modes
- Proper cleanup occurs even on errors
- Stderr capture includes timestamps and is human-readable

### 2.3 ALS Startup and Health Check (FR-3)

**Description:** The system shall intelligently manage ALS startup with health checks to minimize wait times.

**Requirements:**
- FR-3.1: SHALL perform a health check probe after ALS startup by default
- FR-3.2: SHALL skip fixed warmup delay if health check succeeds
- FR-3.3: SHALL fall back to warmup delay if health check fails or times out
- FR-3.4: SHALL support `--no-startup-health-check` to disable health probe
- FR-3.5: SHALL support `--health-timeout` to configure probe timeout (default: 5s)
- FR-3.6: SHALL support `--health-retries` to configure probe retry attempts (default: 1)
- FR-3.7: SHALL capture both ALS stderr and application stderr simultaneously
- FR-3.8: SHALL implement consecutive timeout breaker to abort after N timeouts
- FR-3.9: SHALL support `--max-consecutive-timeouts` to configure breaker (default: 5)

**Acceptance Criteria:**
- ALS readiness is detected quickly when server is responsive
- Graceful fallback to fixed delay when health check fails
- No data loss from stderr capture
- Formatting stops after consecutive timeout threshold

### 2.4 File Formatting (FR-4)

**Description:** The system shall format individual Ada source files using ALS.

**Requirements:**
- FR-4.1: SHALL send textDocument/formatting requests to ALS
- FR-4.2: SHALL apply returned TextEdit arrays to source content
- FR-4.3: SHALL implement per-file timeout (default 30 seconds)
- FR-4.4: SHALL retry failed operations with exponential backoff
- FR-4.5: SHALL distinguish between recoverable and non-recoverable errors
- FR-4.6: SHALL preserve file permissions and attributes
- FR-4.7: SHALL use atomic file writes to prevent corruption

**Acceptance Criteria:**
- Files are formatted correctly according to ALS rules
- Retry logic handles transient failures
- No data loss occurs even on crashes

### 2.5 Output Modes (FR-5)

**Description:** The system shall provide multiple output modes for different use cases.

**Requirements:**
- FR-5.1: SHALL support dry-run mode by default (no file changes)
- FR-5.2: SHALL support `--write` mode for applying changes
- FR-5.3: SHALL support `--check` mode that exits 1 if changes needed
- FR-5.4: SHALL support `--diff` display (unified diff format)
- FR-5.5: SHALL support suppressing diffs via `--no-diff`
- FR-5.6: SHALL display summary line showing files processed and timing

**Acceptance Criteria:**
- Default mode makes no changes
- Check mode returns correct exit codes
- Diffs accurately show changes

### 2.6 User Interface Modes (FR-6)

**Description:** The system shall provide multiple UI modes for different environments.

**Requirements:**
- FR-6.1: SHALL support "pretty" mode using curses for rich terminal UI
- FR-6.2: SHALL support "basic" mode with simple text progress
- FR-6.3: SHALL support "plain" mode with minimal output for scripts
- FR-6.4: SHALL support "off" mode showing only diffs and errors
- FR-6.5: SHALL automatically fall back from curses to basic when:
  - Terminal doesn't support curses
  - Output is redirected (not a TTY)
  - Curses initialization fails
- FR-6.6: SHALL respect NO_COLOR environment variable

**Acceptance Criteria:**
- Each UI mode displays appropriate information
- Fallback occurs gracefully without errors
- CI environments get appropriate output

### 2.7 Logging and Diagnostics (FR-7)

**Description:** The system shall provide comprehensive logging for debugging.

**Requirements:**
- FR-7.1: SHALL always write structured logs in JSONL format to a default file
- FR-7.2: SHALL use timestamped default filename (./adafmt_<timestamp>_log.jsonl) when --log-path not specified
- FR-7.3: SHALL support --log-path flag to override default log location
- FR-7.4: SHALL log file processing status (ok, changed, failed)
- FR-7.5: SHALL log error details and stack traces
- FR-7.6: SHALL capture ALS communication for debugging
- FR-7.7: SHALL always write log files (never append), ensured by unique timestamped filenames
- FR-7.8: SHALL create parent directories as needed
- FR-7.9: SHALL include timing information in logs
- FR-7.10: SHALL always capture ALS stderr to a default file (./adafmt_<timestamp>_stderr.log)
- FR-7.11: SHALL support --stderr-path flag to override default stderr location
- FR-7.12: SHALL display default log paths with "./" prefix in UI and terminal output
- FR-7.13: SHALL append "(default location)" to log paths when using default filenames
- FR-7.14: SHALL honor ADAFMT_LOG_FILE_PATH environment variable when set
- FR-7.15: SHALL persist log files beyond the formatting run completion
- FR-7.16: SHALL ensure timestamps in filenames prevent overwriting logs from previous runs
- FR-7.17: SHALL allow accumulation of multiple log files from different formatting runs
- FR-7.18: SHALL generate a single timestamp at the start of execution that is used for all log files in that run
- FR-7.19: SHALL use the same timestamp for both the JSONL log file and stderr log file names
- FR-7.20: SHALL ensure log files from the same run can be easily identified and correlated by their matching timestamps
- FR-7.21: SHALL open log files once at the start of logging and keep them open for the duration of the session
- FR-7.22: SHALL NOT open and close log files for each log entry (performance requirement)
- FR-7.23: SHALL flush log entries to disk after each write to ensure crash safety
- FR-7.24: SHALL properly close all log files when logging is complete
- FR-7.25: SHALL apply efficient file handling to ALL log files in the application (JSONL log, stderr log, etc.)
- FR-7.26: SHALL write detailed error information to stderr with timestamps when a file fails to format
- FR-7.27: SHALL include the following information in stderr error messages: timestamp, error type, file path, error message, and additional details
- FR-7.28: SHALL distinguish between different error types in stderr output: SYNTAX_ERROR_CONFIRMED, ALS_PROTOCOL_ERROR, CONNECTION_ERROR, UNEXPECTED_ERROR
- FR-7.29: SHALL include actionable information in each stderr error entry about what went wrong and what the user should do
- FR-7.30: SHALL write stderr output both to the stderr log file AND display it on the terminal simultaneously
- FR-7.31: SHALL format stderr error messages in a human-readable format with clear structure and formatting
- FR-7.32: SHALL ensure stderr error messages provide sufficient context for debugging without requiring access to the JSONL log

**Acceptance Criteria:**
- JSONL logs are valid and parseable
- Error conditions are logged with sufficient detail
- Log files aid in debugging issues
- Log files from previous runs remain available for post-run analysis
- Multiple runs create separate timestamped log files that do not overwrite each other
- Log files from the same run share the same timestamp in their filenames for easy correlation
- Log files remain open throughout the session for efficient I/O operations
- Data integrity is maintained through proper flushing after each write
- Stderr error messages are displayed on terminal in real-time as failures occur
- Stderr error messages include all required fields (timestamp, error type, file path, etc.)
- Users can understand and act upon error messages without additional documentation

### 2.8 Error Handling and Recovery (FR-8)

**Description:** The system shall handle errors gracefully with appropriate recovery.

**Requirements:**
- FR-8.1: SHALL retry transient errors with exponential backoff
- FR-8.2: SHALL distinguish between:
  - Recoverable: Connection reset, broken pipe, timeout
  - Non-recoverable: File not found, syntax errors, permission denied
- FR-8.3: SHALL distinguish between syntax and semantic errors:
  - Syntax errors: Malformed code that cannot be parsed (prevents formatting)
  - Semantic errors: Valid syntax but incorrect meaning (does NOT prevent formatting)
- FR-8.4: SHALL format files with semantic errors (undefined types, missing imports)
- FR-8.5: SHALL continue processing remaining files after errors
- FR-8.6: SHALL report all errors clearly to the user
- FR-8.7: SHALL return appropriate exit codes:
  - 0: Success (or no changes in check mode)
  - 1: Changes needed (check mode only)
  - 2: Errors occurred
- FR-8.8: SHALL provide detailed error reporting to stderr with the following format:
  ```
  [TIMESTAMP] ERROR_TYPE: File failed to format
  File: /path/to/file.adb
  Error: Detailed error message
  Details: Additional context about the error
  Action: What the user should do to resolve this
  ```
- FR-8.9: SHALL categorize errors with specific types for stderr reporting:
  - SYNTAX_ERROR_CONFIRMED: Ada syntax errors preventing formatting
  - ALS_PROTOCOL_ERROR: Communication failures with ALS
  - CONNECTION_ERROR: Network/pipe errors during formatting
  - UNEXPECTED_ERROR: Other errors not falling into above categories
- FR-8.10: SHALL provide specific user actions for each error type:
  - SYNTAX_ERROR_CONFIRMED: "Fix syntax errors in the file and retry"
  - ALS_PROTOCOL_ERROR: "Check ALS installation and try --preflight-mode kill"
  - CONNECTION_ERROR: "Retry the operation or restart ALS"
  - UNEXPECTED_ERROR: "Check the log file for more details"

**Acceptance Criteria:**
- Transient errors are recovered automatically
- Clear error messages help users fix issues
- Exit codes enable CI integration
- Stderr error output follows the specified format consistently
- Each error type has appropriate user-actionable guidance
- Error messages appear on terminal immediately when failures occur

### 2.9 Configuration Management (FR-9)

**Description:** The system shall support configuration through CLI arguments and environment variables.

**Requirements:**
- FR-9.1: SHALL support all configuration via command-line arguments
- FR-9.2: SHALL support environment variable defaults:
  - ADAFMT_PROJECT_FILE_PATH
  - ADAFMT_LOG_FILE_PATH
  - ADAFMT_UI_MODE
- FR-9.3: SHALL validate all path arguments as absolute
- FR-9.4: SHALL provide sensible defaults for all optional parameters
- FR-9.5: SHALL support --version and --help flags

**Acceptance Criteria:**
- CLI arguments override environment variables
- Invalid configuration is caught early
- Help text is comprehensive

### 2.10 UI Footer Display (FR-10)

**Description:** The system shall display comprehensive status information in the UI footer.

**Requirements:**
- FR-10.1: SHALL display a multi-line footer with the following information:
  - Line 1: File statistics (total, changed, unchanged, failed) with percentages
  - Line 2: Timing information (elapsed time, processing rate)
  - Line 3: JSONL log file path
  - Line 4: Stderr log file path
  - Line 5: ALS log file path
- FR-10.2: SHALL use fixed-width formatting for percentage values to prevent UI element movement
- FR-10.3: SHALL display percentages as 3-digit fixed width (e.g., "  0%", " 50%", "100%")
- FR-10.4: SHALL use fixed-width formatting for elapsed time to maintain consistent separator positions
- FR-10.5: SHALL ensure vertical bar separators align between statistics and timing lines
- FR-10.6: SHALL use consistent coloring for all separator elements (bold white)
- FR-10.7: SHALL maintain separator color consistency across different UI states (success/failure)
- FR-10.8: SHALL display log paths in the order: Log, Stderr, ALS
- FR-10.9: SHALL show "(default location)" suffix for automatically generated log files
- FR-10.10: SHALL use "./{filename}" format for default log paths in current directory
- FR-10.11: SHALL display brief error messages on TTY with "(details in the stderr log)" suffix
- FR-10.12: SHALL write comprehensive error details to stderr log file without echoing to terminal

**Acceptance Criteria:**
- Footer displays all required information clearly
- UI elements remain at fixed positions throughout execution
- Percentages transition smoothly from 0% to 100% without causing movement
- Vertical bars align perfectly between the stats and timing lines
- All separators maintain consistent appearance
- TTY shows concise error messages while stderr log contains full details

## 3. Non-Functional Requirements

### 3.1 Performance (NFR-1)

**Requirements:**
- NFR-1.1: SHALL format files at >100 lines per second on average
- NFR-1.2: SHALL start up in <1 second (excluding ALS warmup)
- NFR-1.3: SHALL use <100MB RAM for typical operations
- NFR-1.4: SHALL handle projects with >1000 source files
- NFR-1.5: SHALL process files in parallel where possible
- NFR-1.6: SHALL minimize file I/O operations by keeping log files open for the session duration
- NFR-1.7: SHALL maintain data integrity through immediate flushing without compromising performance

**Measurement:**
- Time formatting a large Ada project
- Monitor resource usage during operation
- Measure I/O operations and file handle usage
- Verify log data persistence after crashes

### 3.2 Reliability (NFR-2)

**Requirements:**
- NFR-2.1: SHALL never corrupt or lose source file data
- NFR-2.2: SHALL handle ALS crashes gracefully
- NFR-2.3: SHALL clean up resources on all exit paths
- NFR-2.4: SHALL work with ALS versions 22.0 through current
- NFR-2.5: SHALL handle malformed LSP responses

**Measurement:**
- Stress testing with process kills
- Testing with various ALS versions

### 3.3 Usability (NFR-3)

**Requirements:**
- NFR-3.1: SHALL provide clear error messages with remediation hints
- NFR-3.2: SHALL have intuitive command-line interface
- NFR-3.3: SHALL integrate easily into existing workflows
- NFR-3.4: SHALL provide comprehensive --help documentation
- NFR-3.5: SHALL show progress for long operations

**Measurement:**
- User feedback on error messages
- Time to integrate into projects

### 3.4 Portability (NFR-4)

**Requirements:**
- NFR-4.1: SHALL run on Linux, macOS, and Windows
- NFR-4.2: SHALL work with Python 3.8 through 3.12
- NFR-4.3: SHALL handle different filesystem path formats
- NFR-4.4: SHALL work in containers and CI environments
- NFR-4.5: SHALL handle different terminal encodings

**Measurement:**
- CI testing on multiple platforms
- User reports from different environments

### 3.5 Security (NFR-5)

**Requirements:**
- NFR-5.1: SHALL validate all file paths to prevent directory traversal
- NFR-5.2: SHALL not execute arbitrary commands from user input
- NFR-5.3: SHALL handle untrusted Ada source safely
- NFR-5.4: SHALL not expose sensitive information in logs
- NFR-5.5: SHALL use secure temp file creation

**Measurement:**
- Security testing with malicious inputs
- Code review for security issues

### 3.6 Maintainability (NFR-6)

**Requirements:**
- NFR-6.1: SHALL have >80% test coverage
- NFR-6.2: SHALL follow Python PEP-8 style guidelines
- NFR-6.3: SHALL have comprehensive docstrings
- NFR-6.4: SHALL minimize external dependencies
- NFR-6.5: SHALL use type hints throughout

**Measurement:**
- Coverage reports
- Static analysis results

## 4. Constraints

### 4.1 Technical Constraints

- **Language:** Must be implemented in Python 3.8+
- **Dependencies:** Minimize external packages (no heavy frameworks)
- **ALS Communication:** Must use LSP protocol over stdio only
- **File System:** Must handle case-sensitive and case-insensitive systems

### 4.2 Business Constraints

- **License:** Must be MIT licensed for broad adoption
- **Backwards Compatibility:** Should work with older ALS versions
- **Resource Usage:** Must work on modest developer machines

## 5. Command-Line Interface

### 5.1 Basic Usage

```bash
adafmt --project-path /path/to/project.gpr [options]
```

### 5.2 Key Options

**Required:**
- `--project-path PATH`: Path to GNAT project file (.gpr)

**File Selection:**
- `--include-path PATH`: Directory to search for Ada files (can be repeated)
- `--exclude-path PATH`: Directory to exclude from search (can be repeated)
- `files...`: Specific Ada files to format

**Output Control:**
- `--write`: Apply changes to files (default: dry-run)
- `--check`: Exit with code 1 if files need formatting
- `--diff/--no-diff`: Show unified diffs (default: --diff)

**UI Options:**
- `--ui {off,auto,pretty,basic,plain}`: UI mode (default: auto)

**ALS Control:**
- `--no-startup-health-check`: Skip ALS readiness probe
- `--warmup-seconds N`: Fixed warmup delay if health check fails (default: 10)
- `--health-timeout N`: Health probe timeout in seconds (default: 5)
- `--health-retries N`: Health probe retry attempts (default: 1)
- `--max-consecutive-timeouts N`: Abort after N consecutive timeouts (default: 5)

**Timeout Options:**
- `--init-timeout N`: ALS initialization timeout (default: 180)
- `--format-timeout N`: Per-file formatting timeout (default: 60)
- `--max-attempts N`: Retry attempts for transient errors (default: 2)

**Process Management:**
- `--preflight {off,warn,safe,kill,kill+clean,aggressive,fail}`: Handle existing ALS processes (default: safe)
- `--als-stale-minutes N`: Age for considering ALS stale (default: 30)

#### 5.1 Preflight Levels

The `--preflight` option controls how adafmt handles existing ALS processes and lock files before formatting:

- **`off` / `none`**: Skip all preflight checks and cleanup
- **`warn`**: Report count of ALS processes and stale locks but take no action
- **`fail`**: Report issues and abort if ANY ALS processes or locks are found (exit code 2)
- **`safe`** (default): Kill ALS processes older than `--als-stale-minutes` (current user only)
- **`kill`**: Same as `safe` - kills stale ALS processes only
- **`kill+clean`**: Kill stale ALS processes AND remove stale `.als-alire` lock directories
- **`aggressive`**: Kill ALL ALS processes for current user AND remove all stale locks

Lock directories are considered stale if:
- They are older than 10 minutes AND
- The PID file in the lock either doesn't exist or references a dead process

**Logging:**
- `--log-path PATH`: JSONL log file location (default: ./adafmt_<timestamp>_log.jsonl)
- `--stderr-path PATH`: Stderr capture location (default: ./adafmt_<timestamp>_stderr.log)

## 6. Assumptions

- Ada Language Server is installed and accessible
- Users have appropriate file system permissions
- Python environment supports required standard library modules
- Terminal supports UTF-8 encoding for proper output
- GNAT project files are valid and loadable by ALS

## 6. Dependencies

### 6.1 External Systems

- **Ada Language Server:** Core formatting engine
- **Python Runtime:** Version 3.8 or higher

### 6.2 Python Standard Library

- `asyncio`: Asynchronous subprocess management
- `typer`: Modern command-line interface framework
- `curses`: Terminal UI (optional, with fallback)
- `json`: JSON-RPC communication
- `pathlib`: Cross-platform path handling
- `difflib`: Unified diff generation

## 7. Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ALS protocol changes | High | Low | Support multiple protocol versions |
| ALS crashes frequently | High | Medium | Implement robust retry logic |
| Performance with large files | Medium | Medium | Add file size limits/chunking |
| Platform differences | Medium | High | Extensive cross-platform testing |
| Curses not available | Low | High | Automatic fallback to basic UI |

## 8. Future Enhancements

The following features are under consideration for future releases:

1. **Configuration Files:** Support .adafmt.toml for project settings
2. **Parallel Processing:** Format multiple files concurrently
3. **Incremental Formatting:** Format only changed regions
4. **Style Options:** Pass formatting preferences to ALS
5. **Integration:** Direct IDE/editor plugins
6. **Caching:** Cache formatted files to speed up re-runs
7. **Watch Mode:** Auto-format on file changes
8. **Remote ALS:** Connect to ALS over network

## 9. Success Criteria

The project will be considered successful when:

1. **Adoption:** Used by >10 real Ada projects
2. **Reliability:** <1% failure rate in production use
3. **Performance:** Formats large projects in reasonable time
4. **Integration:** Included in Ada project templates
5. **Community:** Active issue reports and contributions

## 10. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-12-01 | M. Gardner | Initial version |