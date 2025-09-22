# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Additional unit tests for pattern_formatter to achieve >90% coverage.

This module contains additional tests targeting specific coverage gaps.
"""

import json
import signal
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from adafmt.pattern_formatter import (
    PatternFormatter,
    PatternLogger,
    timeout_context,
    REGEX_MODULE
)


class TestAdditionalCoverage:
    """Additional tests for improving coverage."""
    
    def test_load_from_json_with_unknown_flags(self, tmp_path):
        """Test pattern with unknown flags."""
        patterns = [
            {
                "name": "test-rule-01",
                "title": "Test Rule",
                "category": "comment",
                "find": r"test",
                "replace": "TEST",
                "flags": ["MULTILINE", "UNKNOWN_FLAG", "ANOTHER_UNKNOWN"]
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=PatternLogger(mock_logger)
        )
        
        # Pattern should still load, just without the unknown flags
        assert formatter.loaded_count == 1
        assert formatter.rules[0].name == "test-rule-01"
        
        # Check that unknown flags were logged
        assert mock_logger.write.call_count >= 2  # Two unknown flags
        
    def test_load_from_json_no_patterns_ui_message(self, tmp_path):
        """Test UI message when no valid patterns are loaded."""
        patterns = [
            {
                "name": "bad name!",  # Invalid name
                "title": "Bad Pattern",
                "category": "comment",
                "find": r"test",
                "replace": "TEST"
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            ui=mock_ui
        )
        
        assert formatter.loaded_count == 0
        mock_ui.log_line.assert_called_with("[info] No valid patterns loaded")
        
    def test_load_from_json_duplicate_with_ui(self, tmp_path):
        """Test duplicate pattern handling with UI."""
        patterns = [
            {
                "name": "duplicate-01",
                "title": "First Pattern",
                "category": "comment",
                "find": r"test",
                "replace": "TEST1"
            },
            {
                "name": "duplicate-01",  # Duplicate
                "title": "Second Pattern",
                "category": "comment",
                "find": r"test",
                "replace": "TEST2"
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            ui=mock_ui
        )
        
        assert formatter.loaded_count == 1
        mock_ui.log_line.assert_called_with("[warning] Duplicate pattern name: duplicate-01")
        
    def test_apply_with_logger(self, tmp_path):
        """Test pattern application with logging."""
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
        
        mock_logger = Mock()
        content = "test content with test"
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            logger=PatternLogger(mock_logger)
        )
        
        assert result == "TEST content with TEST"
        assert stats.replacements_sum == 2
        
        # Check that pattern application was logged
        mock_logger.write.assert_called_once()
        log_data = mock_logger.write.call_args[0][0]
        assert log_data['ev'] == 'pattern'
        assert log_data['name'] == 'test-rule-01'
        assert log_data['title'] == 'Test Rule'
        assert log_data['category'] == 'comment'
        assert log_data['replacements'] == 2
        
    def test_apply_creates_missing_counters(self, tmp_path):
        """Test that apply creates missing counters if needed."""
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
        
        # Manually remove the counters to simulate missing state
        del formatter.files_touched["test-rule-01"]
        del formatter.replacements["test-rule-01"]
        
        content = "test content"
        result, stats = formatter.apply(Path("test.adb"), content)
        
        assert result == "TEST content"
        assert "test-rule-01" in formatter.files_touched
        assert "test-rule-01" in formatter.replacements
        assert formatter.files_touched["test-rule-01"] == 1
        assert formatter.replacements["test-rule-01"] == 1
        
    def test_regex_module_timeout_feature(self, tmp_path):
        """Test regex module timeout feature when available."""
        if REGEX_MODULE != 'regex':
            pytest.skip("regex module not available")
            
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
        # Should use regex module's built-in timeout
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            timeout_ms=1000  # 1 second timeout
        )
        
        assert result == "TEST content"
        assert stats.replacements_sum == 1
        
    def test_load_generic_exception(self, tmp_path):
        """Test generic exception handling during load."""
        json_file = tmp_path / "patterns.json"
        json_file.write_text('{"valid": "json"}')
        
        mock_logger = Mock()
        
        # Mock the json.load to raise a generic exception
        with patch('json.load', side_effect=Exception("Unexpected error")):
            formatter = PatternFormatter.load_from_json(
                json_file,
                logger=PatternLogger(mock_logger)
            )
            
        assert formatter.loaded_count == 0
        assert not formatter.enabled
        
        # Check that error was logged
        mock_logger.write.assert_called_once()
        log_data = mock_logger.write.call_args[0][0]
        assert log_data['ev'] == 'pattern_error'
        assert 'Unexpected error' in log_data['error']
        
            
    def test_pattern_logger_with_none_logger(self):
        """Test PatternLogger with None logger."""
        logger = PatternLogger(None)
        
        # Should not raise even with None logger
        logger.log({"test": "data"})


class TestWindowsCoverage:
    """Tests specifically for Windows-related code paths."""
    
    @pytest.mark.skipif(hasattr(signal, 'SIGALRM'),
                       reason="Test for Windows/non-SIGALRM platforms")
    def test_timeout_context_no_sigalrm(self):
        """Test timeout_context on platforms without SIGALRM."""
        import time
        
        # Should not raise, just yield
        with timeout_context(0.001):
            time.sleep(0.1)  # Would timeout on POSIX
            result = "completed"
            
        assert result == "completed"