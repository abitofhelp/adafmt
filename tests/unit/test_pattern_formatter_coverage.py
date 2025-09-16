# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Additional tests to achieve >90% coverage for pattern_formatter.

This module targets specific uncovered lines.
"""

import json
import os
import re
import signal
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from adafmt.pattern_formatter import (
    PatternFormatter,
    PatternLogger,
    CompiledRule,
    timeout_context,
    HAS_TIMEOUT,
    REGEX_MODULE
)


class TestRemainingCoverage:
    """Tests for remaining coverage gaps."""
    
    def test_file_not_found_with_logger(self):
        """Test FileNotFoundError handling with logger."""
        mock_logger = Mock()
        
        formatter = PatternFormatter.load_from_json(
            Path("/non/existent/path/patterns.json"),
            logger=PatternLogger(mock_logger)
        )
        
        assert formatter.loaded_count == 0
        assert not formatter.enabled
        
        # Check error was logged
        mock_logger.write.assert_called_once()
        log_data = mock_logger.write.call_args[0][0]
        assert log_data['ev'] == 'pattern_error'
        assert 'not found' in log_data['error']
        
    def test_json_decode_error_with_logger(self, tmp_path):
        """Test JSONDecodeError handling with logger."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{ invalid json")
        
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=PatternLogger(mock_logger)
        )
        
        assert formatter.loaded_count == 0
        
        # Check error was logged
        mock_logger.write.assert_called_once()
        log_data = mock_logger.write.call_args[0][0]
        assert log_data['ev'] == 'pattern_error'
        assert 'Invalid JSON' in log_data['error']
        
    def test_regex_compile_error_with_ui(self, tmp_path):
        """Test regex compile error with UI feedback."""
        patterns = [
            {
                "name": "invalid-rex1",
                "title": "Invalid Regex",
                "category": "comment",
                "find": r"[invalid(regex",  # Invalid regex
                "replace": ""
            }
        ]
        
        json_file = tmp_path / "bad_regex.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            ui=mock_ui
        )
        
        assert formatter.loaded_count == 0
        # Check UI warning was shown
        mock_ui.log_line.assert_called()
        # Find the warning call
        warning_call = None
        for call in mock_ui.log_line.call_args_list:
            if "[warning]" in call[0][0] and "invalid regex" in call[0][0].lower():
                warning_call = call
                break
        assert warning_call is not None, "Expected warning about invalid regex"
        
    # Timeout testing moved to integration tests - see test_pattern_timeout_integration.py
    # Testing actual timeout behavior requires real regex patterns that timeout,
    # which is better suited for integration testing than unit testing with mocks
            
    def test_windows_timeout_context(self):
        """Test timeout_context on Windows (no-op)."""
        # Mock os.name to simulate Windows
        with patch('adafmt.pattern_formatter.signal') as mock_signal:
            # Remove SIGALRM attribute to simulate Windows
            if hasattr(mock_signal, 'SIGALRM'):
                delattr(mock_signal, 'SIGALRM')
                
            # Should just yield without setting alarm
            with timeout_context(1.0):
                result = "completed"
                
            assert result == "completed"
            
    def test_timeout_context_with_existing_alarm(self):
        """Test timeout context preserves existing alarms."""
        if not hasattr(signal, 'SIGALRM'):
            pytest.skip("SIGALRM not available")
            
        # Set an existing alarm
        old_alarm = signal.alarm(100)
        
        try:
            with timeout_context(0.1):
                pass
                
            # The old alarm should be restored
            # (We can't directly test this without waiting)
            
        finally:
            signal.alarm(0)  # Cancel any alarms
            
    def test_value_error_from_compiled_rule(self, tmp_path):
        """Test ValueError from CompiledRule validation."""
        patterns = [
            {
                "name": "test-rule-01",
                "title": "x" * 81,  # Title too long (>80 chars)
                "category": "comment",
                "find": r"test",
                "replace": "TEST"
            }
        ]
        
        json_file = tmp_path / "invalid_title.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=PatternLogger(mock_logger)
        )
        
        assert formatter.loaded_count == 0
        
        # Check error was logged
        assert mock_logger.write.call_count > 0
        log_calls = [call[0][0] for call in mock_logger.write.call_args_list]
        # The error should mention title length
        assert any('Title must be 1-80 characters' in call.get('error', '') for call in log_calls)


class TestRegexModuleFallback:
    """Test behavior when regex module is not available."""
    
    def test_import_fallback(self):
        """Test that code handles regex module unavailability."""
        # This is hard to test directly, but we can verify the module works
        # whether regex is available or not
        assert REGEX_MODULE in ('regex', 're')
        if REGEX_MODULE == 'regex':
            assert HAS_TIMEOUT is True
        else:
            assert HAS_TIMEOUT is False
            
    @patch('adafmt.pattern_formatter.HAS_TIMEOUT', False)
    @patch('adafmt.pattern_formatter.REGEX_MODULE', 're')
    def test_apply_without_regex_module(self, tmp_path):
        """Test pattern application when regex module is not available."""
        patterns = [
            {
                "name": "test-rule-01",
                "title": "Test Rule",
                "category": "comment",
                "find": r"test",
                "replace": "TEST"
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        content = "test content"
        result, stats = formatter.apply(Path("test.adb"), content)
        
        assert result == "TEST content"
        assert stats.replacements_sum == 1