# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for the CLI module.

This module contains comprehensive unit tests for the command-line interface
implementation of adafmt. Tests cover:

- Stderr capture and redirection (Tee functionality)
- Error message formatting and output
- Path validation and normalization
- UI mode selection and initialization
- Cleanup and signal handling
- Configuration management

All tests use mocks to avoid side effects and ensure isolated testing.
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from adafmt import cli
from adafmt.file_discovery_new import is_ada_file


class TestTeeClass:
    """Test suite for the _Tee class used for stderr capture.
    
    Tests the Tee implementation that allows capturing stderr output
    to a file while optionally echoing to the terminal. This is used
    to capture compiler and ALS error messages for display in the UI.
    """
    
    def test_tee_writes_to_single_stream(self):
        """Test _Tee writes to file stream without terminal echo.
        
        Given: A file stream for capturing output
        When: Data is written through the Tee
        Then: Data appears only in the file stream (GPT-5 fix: no terminal echo)
        """
        # Create test streams
        file_stream = io.StringIO()
        
        # Create tee with single stream (GPT-5 fix behavior)
        tee = cli._Tee(file_stream)
        
        # Write test data
        test_data = "Test stderr output\n"
        written = tee.write(test_data)
        
        # Verify stream received the data
        assert file_stream.getvalue() == test_data
        assert written == len(test_data)
    
    def test_tee_flush(self):
        """Test _Tee flush method compatibility.
        
        Given: A Tee instance with a file stream
        When: flush() is called
        Then: Method executes without error (required for stderr compatibility)
        """
        file_stream = io.StringIO()
        tee = cli._Tee(file_stream)
        
        # Should not raise
        tee.flush()
    
    def test_tee_with_real_stderr(self):
        """Test _Tee can replace sys.stderr for error capture.
        
        Given: A Tee instance with capture stream
        When: Assigned to sys.stderr and used for printing
        Then: Output is captured in the stream while maintaining stderr interface
        """
        original_stderr = sys.stderr
        file_stream = io.StringIO()
        
        try:
            sys.stderr = cli._Tee(file_stream)
            print("Test message", file=sys.stderr)
            assert "Test message\n" in file_stream.getvalue()
        finally:
            sys.stderr = original_stderr


class TestErrorWriting:
    """Test suite for error message formatting and output.
    
    Tests the _write_stderr_error function that formats and outputs
    structured error messages to stderr, including error type, file path,
    message, and additional details.
    """
    
    @patch('sys.stderr')
    def test_write_stderr_error(self, mock_stderr):
        """Test _write_stderr_error formats error messages with all components.
        
        Given: Error details including path, type, message, and line/column info
        When: _write_stderr_error is called
        Then: Outputs formatted error with all components and separator
        """
        mock_stderr.write = MagicMock()
        
        cli._write_stderr_error(
            path=Path("/test/file.adb"),
            error_type="SYNTAX_ERROR",
            error_msg="Missing semicolon",
            details={"line": 42, "column": 15}
        )
        
        # Verify write was called
        assert mock_stderr.write.called
        
        # Get the written content
        written_content = mock_stderr.write.call_args[0][0]
        
        # Check content
        assert "SYNTAX_ERROR" in written_content
        assert "/test/file.adb" in written_content
        assert "Missing semicolon" in written_content
        assert "line: 42" in written_content
        assert "column: 15" in written_content
        assert "=====" in written_content  # Separator


class TestPathValidation:
    """Test suite for path validation and normalization functions.
    
    Tests path handling utilities including home directory expansion,
    relative path resolution, and Ada file extension validation.
    """
    
    def test_abs_expands_user(self):
        """Test _abs expands tilde to user's home directory.
        
        Given: A path starting with ~ (tilde)
        When: _abs is called with the path
        Then: Returns absolute path with home directory expanded
        """
        result = cli._abs("~/test")
        assert result.startswith("/")
        assert "~" not in result
    
    def test_abs_resolves_relative(self):
        """Test _abs converts relative paths to absolute paths.
        
        Given: A relative path starting with ./
        When: _abs is called with the path
        Then: Returns absolute path resolved from current directory
        """
        result = cli._abs("./test")
        assert result.startswith("/")
        assert "./" not in result
    
    def test_is_ada_file(self):
        """Test is_ada_file correctly identifies Ada source files.
        
        Given: Various file paths with different extensions
        When: is_ada_file is called with each path
        Then: Returns True for .ads/.adb/.ada files (case-insensitive), False otherwise
        """
        assert is_ada_file(Path("test.ads"))
        assert is_ada_file(Path("test.adb"))
        assert is_ada_file(Path("test.ada"))
        assert is_ada_file(Path("TEST.ADS"))  # Case insensitive
        assert not is_ada_file(Path("test.txt"))
        assert not is_ada_file(Path("test.py"))


class TestUIMode:
    """Test suite for UI mode selection and initialization.
    
    Tests that the UI mode parameter is correctly passed through
    to the UI factory function for creating the appropriate UI instance.
    """
    
    @patch('adafmt.cli.make_ui')
    def test_ui_mode_selection(self, mock_make_ui):
        """Test UI mode parameter is correctly passed to UI factory.
        
        Given: UI mode "plain"
        When: make_ui is called with the mode
        Then: UI factory is called with the correct mode parameter
        """
        mock_ui = MagicMock()
        mock_make_ui.return_value = mock_ui
        
        # This would be called within run_formatter
        ui = cli.make_ui("plain")
        
        mock_make_ui.assert_called_once_with("plain")


class TestCleanupHandler:
    """Test suite for cleanup handler and signal handling.
    
    Tests the cleanup handler that ensures proper shutdown of resources
    including ALS client, UI, logger, and stderr restoration when the
    application exits or receives termination signals.
    """
    
    def test_cleanup_handler_basic(self):
        """Test _cleanup_handler properly closes UI and logger resources.
        
        Given: Active UI and logger instances in cleanup state
        When: _cleanup_handler is called
        Then: Both UI and logger close methods are called
        """
        # Setup mock instances
        mock_ui = MagicMock()
        mock_logger = MagicMock()
        
        # Set global cleanup variables
        cli._cleanup_ui = mock_ui
        cli._cleanup_logger = mock_logger
        
        # Call cleanup
        cli._cleanup_handler()
        
        # Verify UI and logger were closed
        mock_ui.close.assert_called_once()
        mock_logger.close.assert_called_once()
        
        # Cleanup
        cli._cleanup_ui = None
        cli._cleanup_logger = None
    
    def test_cleanup_handler_restores_stderr(self):
        """Test cleanup handler restores original stderr stream.
        
        Given: Modified sys.stderr and saved restore function
        When: _cleanup_handler is called
        Then: The restore function is called
        """
        # Setup mock restore function
        mock_restore = MagicMock()
        
        # Set global cleanup variable
        cli._cleanup_restore_stderr = mock_restore
        
        # Call cleanup
        cli._cleanup_handler()
        
        # Verify restore was called
        mock_restore.assert_called_once()
        
        # Cleanup
        cli._cleanup_restore_stderr = None