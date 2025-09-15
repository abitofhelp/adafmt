"""Unit tests for the pattern_formatter module.

This module contains comprehensive tests for the PatternFormatter class
and related functionality including pattern loading, application, error
handling, and safety features.
"""

import json
import os
import re
import signal
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open
import pytest

from adafmt.pattern_formatter import (
    PatternFormatter,
    PatternLogger,
    CompiledRule,
    FileApplyResult,
    timeout_context,
    PATTERN_NAME_REGEX,
    HAS_TIMEOUT,
    REGEX_MODULE,
    VALID_CATEGORIES
)
from adafmt.logging_jsonl import JsonlLogger


class TestPatternLogger:
    """Test suite for PatternLogger adapter class."""
    
    def test_init(self):
        """Test PatternLogger initialization with JsonlLogger."""
        jsonl_logger = Mock(spec=JsonlLogger)
        logger = PatternLogger(jsonl_logger)
        assert logger._logger is jsonl_logger
    
    def test_log(self):
        """Test PatternLogger forwards log calls to JsonlLogger."""
        jsonl_logger = Mock(spec=JsonlLogger)
        logger = PatternLogger(jsonl_logger)
        
        test_data = {"event": "test", "value": 42}
        logger.log(test_data)
        
        jsonl_logger.write.assert_called_once_with(test_data)


class TestCompiledRule:
    """Test suite for CompiledRule dataclass."""
    
    def test_creation(self):
        """Test CompiledRule creation with all fields."""
        pattern = re.compile(r"test")
        rule = CompiledRule(
            name="test-rule-01",  # Must be 12 chars
            title="Test Rule",
            category="comment",  # Must be valid category
            find=pattern,
            replace="replacement"
        )
        
        assert rule.name == "test-rule-01"
        assert rule.title == "Test Rule"
        assert rule.category == "comment"
        assert rule.find is pattern
        assert rule.replace == "replacement"
    
    def test_post_init_frozen(self):
        """Test that CompiledRule is frozen after creation."""
        pattern = re.compile(r"test")
        rule = CompiledRule(
            name="test-rule-01",
            title="Test Rule",
            category="comment",
            find=pattern,
            replace="replacement"
        )
        
        # Should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            rule.name = "new_name"
    
    def test_validation_errors(self):
        """Test CompiledRule validation in __post_init__."""
        pattern = re.compile(r"test")
        
        # Test invalid name format
        with pytest.raises(ValueError, match="Invalid pattern name format"):
            CompiledRule(
                name="bad_name",  # Not 12 chars
                title="Test",
                category="comment",
                find=pattern,
                replace=""
            )
        
        # Test invalid title length
        with pytest.raises(ValueError, match="Title must be 1-80 characters"):
            CompiledRule(
                name="test-rule-01",
                title="",  # Empty title
                category="comment",
                find=pattern,
                replace=""
            )
        
        # Test invalid category
        with pytest.raises(ValueError, match="Invalid category"):
            CompiledRule(
                name="test-rule-01",
                title="Test",
                category="invalid",  # Not in VALID_CATEGORIES
                find=pattern,
                replace=""
            )


class TestFileApplyResult:
    """Test suite for FileApplyResult dataclass."""
    
    def test_creation(self):
        """Test FileApplyResult creation with default values."""
        result = FileApplyResult()
        
        assert result.applied_names == []
        assert result.replacements_sum == 0
    
    def test_with_replacements(self):
        """Test FileApplyResult with replacement data."""
        result = FileApplyResult(
            applied_names=["rule1", "rule2"],
            replacements_sum=5
        )
        
        assert result.applied_names == ["rule1", "rule2"]
        assert result.replacements_sum == 5


class TestTimeoutContext:
    """Test suite for timeout_context context manager."""
    
    @pytest.mark.skipif(not HAS_TIMEOUT and os.name != 'posix', 
                       reason="Timeout not supported on this platform")
    def test_timeout_success(self):
        """Test timeout_context with successful execution."""
        with timeout_context(1.0):
            # This should complete successfully
            result = 2 + 2
        assert result == 4
    
    # Timeout tests with real delays moved to integration tests
    # See tests/integration/test_timeout_context_integration.py


class TestPatternFormatter:
    """Test suite for PatternFormatter class."""
    
    def test_init(self):
        """Test PatternFormatter initialization."""
        formatter = PatternFormatter()
        
        assert formatter.enabled is False  # Starts disabled
        assert formatter.rules == ()
        assert formatter.loaded_count == 0
        assert formatter.files_touched == {}
        assert formatter.replacements == {}
    
    def test_pattern_name_validation(self):
        """Test pattern name validation regex."""
        # Valid names (12 characters, lowercase, numbers, dash, underscore)
        valid_names = [
            "test-rule-01",
            "comment_eol1",
            "range_dots01",
            "decl_colon01"
        ]
        
        for name in valid_names:
            assert PATTERN_NAME_REGEX.match(name) is not None
        
        # Invalid names
        invalid_names = [
            "short",  # Too short
            "this-is-way-too-long",  # Too long
            "UPPERCASE-NO",  # Uppercase not allowed
            "special!char",  # Special characters not allowed
            "space name 1",  # Spaces not allowed
        ]
        
        for name in invalid_names:
            assert PATTERN_NAME_REGEX.match(name) is None
    
    def test_load_from_json_file_not_found(self):
        """Test loading from non-existent JSON file."""
        formatter = PatternFormatter.load_from_json(
            Path("/non/existent/file.json"),
            logger=None,
            ui=None
        )
        
        assert formatter.enabled is False  # No patterns loaded
        assert formatter.loaded_count == 0
        assert len(formatter.rules) == 0
    
    def test_load_from_json_invalid_json(self, tmp_path):
        """Test loading from invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{ invalid json")
        
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=None,
            ui=mock_ui
        )
        
        assert formatter.loaded_count == 0
        mock_ui.show_error.assert_called_once()
    
    def test_load_from_json_valid_patterns(self, tmp_path):
        """Test loading valid patterns from JSON."""
        patterns = [
            {
                "name": "test-rule-01",
                "title": "Test Rule",
                "category": "hygiene",
                "find": r"\s+$",
                "replace": "",
                "flags": ["MULTILINE"]
            },
            {
                "name": "comment_eol1",
                "title": "EOL comment spacing",
                "category": "comment",
                "find": r"(\S)\s*--\s*(.*)$",
                "replace": r"\1  --  \2",
                "flags": ["MULTILINE"]
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        assert formatter.enabled is True  # Enabled when patterns loaded
        assert formatter.loaded_count == 2
        assert len(formatter.rules) == 2
        # Rules are sorted by name, so comment_eol1 comes before test-rule-01
        assert formatter.rules[0].name == "comment_eol1"
        assert formatter.rules[1].name == "test-rule-01"
    
    def test_load_from_json_invalid_pattern_structure(self, tmp_path):
        """Test handling of invalid pattern structures."""
        patterns = [
            "not a dict",  # Should be skipped
            {
                "name": "missing-find",
                "title": "Missing Find",
                "category": "comment",
                # Missing 'find' field
                "replace": ""
            },
            {
                "name": "bad name!",  # Invalid name
                "title": "Bad Name",
                "category": "comment",
                "find": r"test",
                "replace": "test"
            },
            {
                "name": "valid-rule-1",
                "title": "Valid Rule",
                "category": "comment",
                "find": r"test",
                "replace": "replacement"
            }
        ]
        
        json_file = tmp_path / "mixed_patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=mock_logger,
            ui=mock_ui
        )
        
        # Only the last valid pattern should load
        assert formatter.loaded_count == 1
        assert len(formatter.rules) == 1
        assert formatter.rules[0].name == "valid-rule-1"
        
        # Check that errors were logged
        assert mock_logger.log.call_count > 0
    
    def test_load_from_json_duplicate_names(self, tmp_path):
        """Test handling of duplicate pattern names."""
        patterns = [
            {
                "name": "duplicate-01",
                "title": "First Pattern",
                "category": "comment",
                "find": r"first",
                "replace": "1st"
            },
            {
                "name": "duplicate-01",  # Duplicate name
                "title": "Second Pattern",
                "category": "comment",
                "find": r"second",
                "replace": "2nd"
            }
        ]
        
        json_file = tmp_path / "duplicates.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=mock_logger
        )
        
        # Only first pattern with the name should load
        assert formatter.loaded_count == 1
        assert len(formatter.rules) == 1
        assert formatter.rules[0].title == "First Pattern"
    
    def test_load_from_json_regex_compile_error(self, tmp_path):
        """Test handling of invalid regex patterns."""
        patterns = [
            {
                "name": "invalid-rex",
                "title": "Invalid Regex",
                "category": "comment",
                "find": r"[invalid(regex",  # Invalid regex
                "replace": ""
            }
        ]
        
        json_file = tmp_path / "bad_regex.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=mock_logger
        )
        
        assert formatter.loaded_count == 0
        assert len(formatter.rules) == 0
        # Should log the regex compile error
        mock_logger.log.assert_called()
    
    def test_apply_no_patterns(self):
        """Test apply with no loaded patterns."""
        formatter = PatternFormatter()
        content = "test content"
        
        result, stats = formatter.apply(Path("test.ada"), content)
        
        assert result == content  # Content unchanged
        assert stats.applied_names == []
        assert stats.replacements_sum == 0
    
    def test_apply_with_patterns(self, tmp_path):
        """Test applying patterns to content."""
        patterns = [
            {
                "name": "trail-space1",
                "title": "Remove trailing spaces",
                "category": "hygiene",
                "find": r"\s+$",
                "replace": "",
                "flags": ["MULTILINE"]
            },
            {
                "name": "comment_eol1",
                "title": "EOL comment spacing",
                "category": "comment",
                "find": r"(\S)\s*--\s*(.*)$",
                "replace": r"\1  --  \2",
                "flags": ["MULTILINE"]
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        content = """procedure Test is
   X : Integer;   
   Y : Integer;--comment
begin
   null;  
end Test;"""
        
        expected = """procedure Test is
   X : Integer;
   Y : Integer;  --  comment
begin
   null;
end Test;"""
        
        result, stats = formatter.apply(Path("test.adb"), content)
        
        assert result == expected
        assert stats.replacements_sum == 3  # 2 trailing spaces + 1 comment
        assert "trail-space1" in stats.applied_names
        assert "comment_eol1" in stats.applied_names
    
    # Pattern timeout test moved to integration tests
    # See tests/integration/test_pattern_timeout_integration.py
    
    def test_apply_with_file_logging(self, tmp_path):
        """Test pattern application with file tracking."""
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
        
        # Apply to multiple files
        content1 = "test file one"
        result1, stats1 = formatter.apply(Path("file1.adb"), content1)
        
        content2 = "another test file"
        result2, stats2 = formatter.apply(Path("file2.adb"), content2)
        
        content3 = "no matches here"
        result3, stats3 = formatter.apply(Path("file3.adb"), content3)
        
        # Check results
        assert result1 == "TEST file one"
        assert result2 == "another TEST file"
        assert result3 == "no matches here"
        
        # Check tracking
        assert formatter.files_touched["test-rule-01"] == 2  # Applied to 2 files
        assert formatter.replacements["test-rule-01"] == 2  # 2 total replacements
    
    def test_get_summary(self, tmp_path):
        """Test get_summary method."""
        patterns = [
            {
                "name": "rule-one-001",  # Must be 12 chars
                "title": "Rule One",
                "category": "comment",
                "find": r"one",
                "replace": "ONE"
            },
            {
                "name": "rule-two-002",  # Must be 12 chars
                "title": "Rule Two",
                "category": "comment",
                "find": r"two",
                "replace": "TWO"
            }
        ]
        
        json_file = tmp_path / "patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        # Create a mock logger to catch any errors
        mock_logger = Mock()
        formatter = PatternFormatter.load_from_json(json_file, logger=PatternLogger(mock_logger))
        
        # Apply patterns to build up stats
        result1, stats1 = formatter.apply(Path("file1.adb"), "one two three")
        result2, stats2 = formatter.apply(Path("file2.adb"), "one more time")
        result3, stats3 = formatter.apply(Path("file3.adb"), "two by two")
        
        summary = formatter.get_summary()
        
        # The issue is that files_touched is incremented per pattern application,
        # not per unique file. Let's check the actual implementation
        assert "rule-one-001" in summary
        # rule-one-001 is applied to file1 and file2
        assert summary["rule-one-001"]["files_touched"] == 2
        assert summary["rule-one-001"]["replacements"] == 2
        
        assert "rule-two-002" in summary  
        # rule-two-002 is applied to file1 and file3
        assert summary["rule-two-002"]["files_touched"] == 2
        assert summary["rule-two-002"]["replacements"] == 3
    
    def test_disabled_formatter(self):
        """Test that disabled formatter doesn't apply patterns."""
        formatter = PatternFormatter()
        formatter.enabled = False
        
        content = "test content"
        result, stats = formatter.apply(Path("test.adb"), content)
        
        assert result == content
        assert stats.replacements_sum == 0
    
    def test_apply_with_exception(self, tmp_path):
        """Test exception handling during pattern application."""
        patterns = [
            {
                "name": "error-rule-1",
                "title": "Rule that errors",
                "category": "comment",
                "find": r"test",
                "replace": r"\9"  # Invalid backreference
            }
        ]
        
        json_file = tmp_path / "error.json"
        json_file.write_text(json.dumps(patterns))
        
        mock_logger = Mock()
        mock_ui = Mock()
        formatter = PatternFormatter.load_from_json(
            json_file,
            logger=mock_logger
        )
        
        content = "test content"
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            logger=PatternLogger(mock_logger),
            ui=mock_ui
        )
        
        # Content should be unchanged due to error
        assert result == content
        assert "error-rule-1" not in stats.applied_names
        # Should log the error
        mock_logger.write.assert_called()

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_load_with_io_error(self):
        """Test handling of I/O errors during load."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            formatter = PatternFormatter.load_from_json(Path("test.json"))
            assert formatter.loaded_count == 0
            assert not formatter.enabled
    
    def test_pattern_with_zero_timeout(self, tmp_path):
        """Test pattern with zero timeout."""
        patterns = [{
            "name": "zero-time-01",
            "title": "Zero timeout",
            "category": "comment",
            "find": r"test",
            "replace": "TEST",
            "timeout": 0
        }]
        
        json_file = tmp_path / "zero.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        # Should still work with 0 timeout (no timeout)
        result, stats = formatter.apply(Path("test.adb"), "test code")
        assert result == "TEST code"