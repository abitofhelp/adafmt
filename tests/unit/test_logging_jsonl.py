# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for the logging_jsonl module.

This module contains comprehensive unit tests for JSONL (JSON Lines) logging
functionality used to track formatting operations. Tests cover:

- Logger initialization and file handling
- Single and multiple record writing
- Unicode support
- File creation and overwriting
- Note appending functionality
- Context manager support
- Complex nested data structures

JSONL logging provides structured, machine-readable logs of all formatting operations.
"""
import json
from pathlib import Path
import pytest

from adafmt.logging_jsonl import JsonlLogger


class TestJsonlLogger:
    """Test suite for the JsonlLogger class.
    
    Tests the JSON Lines logger implementation used for structured logging
    of formatting operations, including file handling, data serialization,
    and various usage patterns.
    """
    
    def test_init_creates_path_object(self, tmp_path):
        """Test logger initialization converts string paths to Path objects.
        
        Given: A string path to the log file
        When: JsonlLogger is initialized
        Then: The path is stored internally as a Path object
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        assert isinstance(logger.path, Path)
        assert logger.path == log_path
    
    def test_start_fresh_creates_empty_file(self, tmp_path):
        """Test start_fresh creates a new empty log file.
        
        Given: A logger with a non-existent log file path
        When: start_fresh() is called
        Then: Creates an empty file at the specified path
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        logger.start_fresh()
        
        assert log_path.exists()
        assert log_path.read_text() == ""
    
    def test_start_fresh_overwrites_existing(self, tmp_path):
        """Test start_fresh overwrites existing log files.
        
        Given: An existing log file with content
        When: start_fresh() is called
        Then: The file is truncated to empty
        """
        log_path = tmp_path / "test.jsonl"
        log_path.write_text("existing content\n")
        
        logger = JsonlLogger(str(log_path))
        logger.start_fresh()
        
        assert log_path.read_text() == ""
    
    def test_start_fresh_creates_parent_dirs(self, tmp_path):
        """Test start_fresh creates necessary parent directories.
        
        Given: A log file path with non-existent parent directories
        When: start_fresh() is called
        Then: Creates all parent directories and the log file
        """
        log_path = tmp_path / "logs" / "deep" / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        logger.start_fresh()
        
        assert log_path.exists()
        assert log_path.parent.is_dir()
    
    def test_write_single_record(self, tmp_path):
        """Test writing a single JSON record to the log.
        
        Given: A dictionary record with formatting status
        When: write() is called with the record
        Then: The record is serialized as JSON and written as a single line
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        record = {"path": "test.ads", "status": "ok"}
        logger.write(record)
        
        content = log_path.read_text()
        assert content.strip() == json.dumps(record, ensure_ascii=False)
    
    def test_write_multiple_records(self, tmp_path):
        """Test writing multiple records creates proper JSONL format.
        
        Given: Multiple dictionary records with different statuses
        When: write() is called for each record
        Then: Each record is written as a separate JSON line
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        records = [
            {"path": "test1.ads", "status": "ok"},
            {"path": "test2.ads", "status": "changed"},
            {"path": "test3.ads", "status": "failed", "error": "syntax error"}
        ]
        
        for record in records:
            logger.write(record)
        
        lines = log_path.read_text().strip().split('\n')
        assert len(lines) == 3
        
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed == records[i]
    
    def test_write_unicode(self, tmp_path):
        """Test writing records with Unicode characters.
        
        Given: A record containing Unicode characters (Cyrillic, Chinese, emoji)
        When: write() is called with the record
        Then: Unicode is preserved correctly in the output
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        record = {"path": "файл.ads", "message": "Ошибка 错误 🚀"}
        logger.write(record)
        
        content = log_path.read_text(encoding='utf-8')
        parsed = json.loads(content.strip())
        assert parsed == record
    
    def test_write_creates_file_if_missing(self, tmp_path):
        """Test write automatically creates log file if it doesn't exist.
        
        Given: A logger without calling start_fresh()
        When: write() is called
        Then: The log file is created automatically
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        # Don't call start_fresh
        logger.write({"test": "data"})
        
        assert log_path.exists()
    
    def test_append_notes_empty_list(self, tmp_path):
        """Test append_notes with empty notes list does nothing.
        
        Given: An empty list of notes
        When: append_notes() is called
        Then: No record is written to the log
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        logger.append_notes("test.ads", [])
        
        # File might not even be created
        if log_path.exists():
            assert log_path.read_text() == ""
    
    def test_append_notes_single_note(self, tmp_path):
        """Test append_notes with a single note message.
        
        Given: A file path and single note message
        When: append_notes() is called
        Then: Creates a record with file and notes array
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        logger.append_notes("test.ads", ["formatting complete"])
        
        content = log_path.read_text().strip()
        parsed = json.loads(content)
        assert parsed == {"file": "test.ads", "notes": ["formatting complete"]}
    
    def test_append_notes_multiple(self, tmp_path):
        """Test append_notes with multiple note messages.
        
        Given: A file path and list of multiple notes
        When: append_notes() is called
        Then: Creates a record with all notes in order
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        notes = [
            "reformatted 15 lines",
            "fixed indentation",
            "normalized casing"
        ]
        logger.append_notes("complex.ads", notes)
        
        content = log_path.read_text().strip()
        parsed = json.loads(content)
        assert parsed["file"] == "complex.ads"
        assert parsed["notes"] == notes
    
    def test_complex_nested_data(self, tmp_path):
        """Test writing complex nested data structures to JSONL.
        
        Given: A deeply nested record with stats, arrays, and metadata
        When: write() is called with the complex structure
        Then: The entire structure is preserved in JSON serialization
        """
        log_path = tmp_path / "test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        record = {
            "file": "test.ads",
            "stats": {
                "lines": 100,
                "changes": 15,
                "duration_ms": 123.45
            },
            "edits": [
                {"line": 10, "type": "indent"},
                {"line": 25, "type": "whitespace"}
            ],
            "metadata": {
                "als_version": "23.0.0",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }
        
        logger.write(record)
        
        content = log_path.read_text().strip()
        parsed = json.loads(content)
        assert parsed == record
    
    def test_context_manager_usage(self, tmp_path):
        """Test JsonlLogger can be used as a context manager.
        
        Given: A JsonlLogger used in a with statement
        When: Multiple writes occur within the context
        Then: File is properly closed after exiting the context
        """
        log_path = tmp_path / "context.jsonl"
        
        with JsonlLogger(str(log_path)) as logger:
            logger.write({"source": "test", "id": 1})
            logger.write({"source": "test", "id": 2})
        
        # File should be closed after context
        lines = log_path.read_text().strip().split('\n')
        assert len(lines) == 2
        
        data = [json.loads(line) for line in lines]
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2
        
    def test_close_behavior(self, tmp_path):
        """Test explicit file handle close and automatic reopen behavior.
        
        Given: An active logger with open file handle
        When: close() is called and then write() is called again
        Then: File is closed and automatically reopened on next write
        """
        log_path = tmp_path / "close_test.jsonl"
        logger = JsonlLogger(str(log_path))
        
        logger.write({"test": "data"})
        assert logger._file is not None
        
        logger.close()
        assert logger._file is None
        
        # Writing after close should reopen
        logger.write({"more": "data"})
        assert logger._file is not None
        
        logger.close()