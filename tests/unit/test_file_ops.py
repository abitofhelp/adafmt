# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for file operations with functional error handling."""

import os
from pathlib import Path

import pytest
from returns.result import Success, Failure

from adafmt.file_ops import (
    read_text,
    write_text,
    exists,
    stat,
    mkdir,
    remove
)
from adafmt.errors import FileError


class TestFileOps:
    """Test safe file operations."""
    
    def test_read_text_success(self, tmp_path):
        """Test successful file reading."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content)
        
        result = read_text(test_file)
        assert isinstance(result, Success)
        assert result.unwrap() == content
    
    def test_read_text_not_found(self):
        """Test reading nonexistent file."""
        result = read_text("/nonexistent/file.txt")
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, FileError)
        assert error.not_found is True
    
    def test_write_text_success(self, tmp_path):
        """Test successful file writing."""
        test_file = tmp_path / "output.txt"
        content = "Test content"
        
        result = write_text(test_file, content)
        assert isinstance(result, Success)
        assert test_file.read_text() == content
    
    def test_exists_true(self, tmp_path):
        """Test exists returns True for existing file."""
        test_file = tmp_path / "exists.txt"
        test_file.touch()
        
        result = exists(test_file)
        assert isinstance(result, Success)
        assert result.unwrap() is True
    
    def test_exists_false(self):
        """Test exists returns False for nonexistent file."""
        result = exists("/nonexistent/file.txt")
        assert isinstance(result, Success)
        assert result.unwrap() is False
    
    def test_stat_success(self, tmp_path):
        """Test successful file stat."""
        test_file = tmp_path / "stat.txt"
        test_file.write_text("content")
        
        result = stat(test_file)
        assert isinstance(result, Success)
        stat_info = result.unwrap()
        assert stat_info.st_size > 0
    
    def test_stat_not_found(self):
        """Test stat on nonexistent file."""
        result = stat("/nonexistent/file.txt")
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, FileError)
        assert error.not_found is True
    
    def test_mkdir_success(self, tmp_path):
        """Test successful directory creation."""
        new_dir = tmp_path / "new_directory"
        
        result = mkdir(new_dir)
        assert isinstance(result, Success)
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_remove_success(self, tmp_path):
        """Test successful file removal."""
        test_file = tmp_path / "remove.txt"
        test_file.write_text("content")
        assert test_file.exists()
        
        result = remove(test_file)
        assert isinstance(result, Success)
        assert not test_file.exists()
    
    def test_remove_not_found(self):
        """Test removing nonexistent file."""
        result = remove("/nonexistent/file.txt")
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, FileError)
        assert error.not_found is True