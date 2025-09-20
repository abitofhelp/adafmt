# adafmt API Documentation

**Version:** 1.0.1
**Date:** 2025-09-20T00:34:23.357320Z
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

## Overview

The `adafmt` package provides a comprehensive Ada Language Formatter that leverages the Ada Language Server (ALS) to format Ada source code. This documentation covers the complete API reference for all modules, classes, and functions.

## Package Structure

```
adafmt/
├── __init__.py              # Package initialization and version management
├── __main__.py              # Entry point for python -m adafmt
├── als_client.py            # Ada Language Server client implementation
├── als_initializer.py       # ALS path resolution and verification
├── cli.py                   # Command-line interface using Typer
├── cli_helpers.py           # CLI helper functions and utilities
├── edits.py                 # Text edit operations and diff management
├── file_discovery.py        # Ada file discovery and filtering
├── file_processor.py        # File processing orchestration
├── logging_jsonl.py         # JSONL structured logging
├── logging_setup.py         # Logging configuration
├── pattern_formatter.py     # Pattern-based post-formatting
├── pattern_loader.py        # Pattern configuration loading
├── pattern_validator.py     # Pattern validation
├── metrics.py               # Metrics collection
├── metrics_reporter.py      # Metrics reporting
├── tui.py                   # Terminal User Interface components
├── utils.py                 # Utility functions and helpers
└── ... (additional modules) # Error handling, path validation, etc.
```

## Core Modules

### [als_client](./als_client.md)
The heart of adafmt - manages communication with the Ada Language Server using the Language Server Protocol (LSP).

**Key Components:**
- `ALSClient`: Main client class for ALS interaction
- LSP protocol implementation
- Request/response handling
- Error recovery and retry logic

### [cli](./cli.md)
Modern command-line interface built with Typer, providing the main entry point for users.

**Key Features:**
- Plain text TTY output with color-coded status
- Comprehensive error handling
- Progress tracking and reporting
- Configuration management

### [edits](./edits.md)
Handles text transformations and edit operations returned by ALS.

**Key Functions:**
- `apply_edits()`: Apply LSP TextEdit operations
- Edit validation and conflict resolution
- Text diff generation

### [file_discovery](./file_discovery.md)
Discovers and filters Ada source files for formatting.

**Key Functions:**
- `collect_files()`: Recursive file discovery
- Path filtering and exclusion
- Ada file type detection

### [logging_jsonl](./logging_jsonl.md)
Structured logging in JSON Lines format for debugging and analysis.

**Key Features:**
- Thread-safe JSONL output
- Automatic timestamp generation
- Structured event logging
- Performance metrics

### [tui](./tui.md)
Terminal User Interface components for interactive formatting sessions.

**UI Modes:**
- Pretty: Interactive progress with Unicode
- Plain: Simple text progress
- JSON: Machine-readable output
- Quiet: Minimal output

### [utils](./utils.md)
Utility functions for process management and system operations.

**Key Functions:**
- `preflight()`: Pre-execution validation
- `run_hook()`: Hook execution system
- Process cleanup utilities

## Quick Start

```python
from adafmt import ALSClient, collect_files, apply_edits

# Initialize ALS client
async with ALSClient(project_path="project.gpr") as client:
    # Discover Ada files
    files = collect_files(
        include_paths=["src/"],
        exclude_paths=["tests/"]
    )

    # Format each file
    for file in files:
        edits = await client.format_file(file)
        if edits:
            apply_edits(file, edits)
```

## Design Principles

1. **Reliability First**: Robust error handling and recovery
2. **Performance**: Asynchronous operations and efficient file processing
3. **Extensibility**: Clean interfaces for custom formatting rules
4. **Debugging**: Comprehensive logging and diagnostics
5. **User Experience**: Multiple UI modes for different use cases

## Error Handling

All modules follow consistent error handling patterns:

```python
try:
    result = await operation()
except ALSProtocolError as e:
    # Handle LSP protocol errors
    logger.log_error(e)
except Exception as e:
    # Handle unexpected errors
    logger.log_exception(e)
    raise
```

## Threading Model

- Main thread: UI and user interaction
- Worker thread: ALS communication
- Async operations: File I/O and LSP requests

## Performance Considerations

- Batch file processing to minimize ALS restarts
- Concurrent file discovery
- Lazy loading of large files
- Efficient edit application algorithms

## Integration Examples

### CI/CD Integration

```bash
# GitHub Actions
- name: Format Ada Code
  run: |
    pip install adafmt
    adafmt --project-path project.gpr --check
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: adafmt
        name: Format Ada files
        entry: adafmt
        language: system
        files: \.(ads|adb|ada)$
        args: [--project-path, project.gpr, --write]
```

## See Also

- [Developer Guide](../DEVELOPER_GUIDE.md) - Contributing and development setup
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions
- [SRS](../SRS.md) - Software Requirements Specification
- [SDD](../SDD.md) - Software Design Document
