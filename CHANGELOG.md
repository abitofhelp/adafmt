# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pattern validation support for post-ALS formatting rules
- Configurable file size limits with `--max-file-size` option (default: 100KB)
- Cross-platform timeout support via optional `regex` module
- Comprehensive error handling with specific exception types
- Type hints for improved code clarity and static analysis
- Preflight checks for ALS process management
- Pattern formatter with JSON-based configuration
- Metrics collection and reporting system
- Interactive TUI (Terminal User Interface) mode
- Pre and post-hook support for custom workflows
- Extensive test suite with unit and integration tests

### Changed
- Major CLI refactoring: reduced cli.py from over 1000 lines to exactly 500
- Extracted functionality into specialized modules:
  - `file_processor.py` - File processing logic
  - `pattern_formatter.py` - Pattern-based formatting
  - `cleanup_handler.py` - Signal and cleanup handling
  - `als_initializer.py` - ALS client initialization
  - `argument_validator.py` - Command-line argument validation
  - And many more specialized modules
- Improved error messages with file paths and recovery suggestions
- Enhanced timeout handling to prevent indefinite hangs
- Better resource management and cleanup

### Fixed
- Event loop race conditions in cleanup handler
- Resource leaks in ALS client (_reader_loop and _pump_stderr)
- Fire-and-forget async tasks now properly managed
- Signal handling conflicts resolved
- Windows compatibility for pattern timeout handling
- Proper cleanup of pending futures on connection loss

### Security
- Command injection prevention in hook execution (uses shlex.split)
- Path validation to prevent directory traversal
- No shell=True usage in subprocess calls

## [0.0.0] - 2025-09-19

### Added
- Initial release
- Ada Language Server (ALS) integration for formatting
- Basic file discovery and processing
- JSON logging support
