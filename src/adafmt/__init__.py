# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""adafmt - Ada Language Formatter using Ada Language Server.

This package provides a command-line tool for formatting Ada source code
using the Ada Language Server (ALS). It supports various UI modes, Alire
integration, and robust error handling.

Modules:
    cli: Command-line interface and main entry point
    als_client: Async client for communicating with ALS via JSON-RPC
    edits: LSP text edit utilities for applying formatting changes
    file_discovery: Ada source file discovery with include/exclude patterns
    logging_jsonl: JSON Lines logger for structured logging
    utils: Utility functions for paths, processes, and file operations
    tui: Terminal UI implementations with graceful fallback

Key Features:
    - Formats .ads, .adb, and .ada files using ALS
    - Multiple UI modes: pretty (curses), basic, plain, or off
    - Automatic Alire workspace detection with --crate-dir override
    - ALS stderr capture to file with timestamps
    - Retry logic for transient errors
    - Dry-run mode by default with --write flag for actual changes
    - JSONL logging for debugging
    - CI-friendly --check mode

Version History:
    1.0.0 - Initial release with core formatting functionality

"""

__all__ = ["cli", "als_client", "edits", "file_discovery", "logging_jsonl", "utils", "tui"]
# Version is dynamically read from package metadata
try:
    from importlib.metadata import version
    __version__ = version("adafmt")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.0.0"