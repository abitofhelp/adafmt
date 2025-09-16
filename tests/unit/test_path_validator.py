#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for path validation functionality."""

import pytest
from adafmt.path_validator import validate_path, is_supplementary_code_point


class TestSupplementaryCodePoint:
    """Test Unicode supplementary code point detection."""
    
    def test_basic_multilingual_plane(self):
        """Test characters within BMP (U+0000 to U+FFFF)."""
        assert not is_supplementary_code_point('A')  # U+0041
        assert not is_supplementary_code_point('€')  # U+20AC
        assert not is_supplementary_code_point('中')  # U+4E2D
        assert not is_supplementary_code_point('\uFFFF')  # U+FFFF
    
    def test_supplementary_plane(self):
        """Test characters outside BMP (U+10000 and above)."""
        assert is_supplementary_code_point('𐀀')  # U+10000 (Linear B)
        assert is_supplementary_code_point('😀')  # U+1F600 (Emoji)
        assert is_supplementary_code_point('𝐀')  # U+1D400 (Math bold)
        assert is_supplementary_code_point('\U0010FFFF')  # Max Unicode


class TestPathValidation:
    """Test path validation for illegal characters."""
    
    def test_valid_paths(self):
        """Test paths that should pass validation."""
        # Note: The path validator checks resolved paths, so we test absolute paths
        # and simple relative paths without ".." traversal
        valid_paths = [
            "/home/user/project.gpr",
            "/usr/local/bin/ada",
            "/path-with-hyphens/file_with_underscores.ada",
            "/path:with:colons/file.adb",  # Colons allowed
            "/path?with&query=params.txt",  # URL-like chars allowed
        ]
        
        for path in valid_paths:
            assert validate_path(path) is None, f"Path '{path}' should be valid"
    
    def test_empty_path(self):
        """Test empty path validation."""
        assert validate_path("") == "Path cannot be empty"
        
    def test_whitespace_characters(self):
        """Test paths with various whitespace characters."""
        test_cases = [
            ("/path with space/file.txt", 5),
            ("/path\twith\ttab/file.txt", 5),
            ("/path\nwith\nnewline/file.txt", 5),
            ("/path\rwith\rcarriage/file.txt", 5),
            ("/path\vwith\vvertical/file.txt", 5),
            ("/path\fwith\fformfeed/file.txt", 5),
            ("/path\xa0with\xa0nbsp/file.txt", 5),  # Non-breaking space
        ]
        
        for path, position in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{repr(path)}' should be invalid"
            assert f"position {position}" in result
            assert "whitespace character" in result
    
    def test_control_characters(self):
        """Test paths with ISO control characters."""
        test_cases = [
            "/path\x00with\x00null",  # Null character
            "/path\x01with\x01soh",   # Start of heading
            "/path\x1bwith\x1besc",   # Escape
            "/path\x7fwith\x7fdel",   # Delete
            "/path\x80with\x80ctrl",  # Control char
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{repr(path)}' should be invalid"
            assert "control character" in result
    
    def test_illegal_characters(self):
        """Test paths with characters not in allowed set."""
        test_cases = [
            ("/path<with>angle", '<', 5),
            ("/path|with|pipe", '|', 5),
            ("/path{with}braces", '{', 5),
            ("/path[with]brackets", '[', 5),
            ("/path\\with\\backslash", '\\', 5),
            ("/path\"with\"quotes", '"', 5),
            ("/path'with'quotes", "'", 5),
            ("/path@with@at", '@', 5),
            ("/path#with#hash", '#', 5),
            ("/path%with%percent", '%', 5),
            ("/path^with^caret", '^', 5),
            ("/path*with*star", '*', 5),
            ("/path+with+plus", '+', 5),
            ("/path~with~tilde", '~', 5),
            ("/path!with!exclaim", '!', 5),
            ("/path$with$dollar", '$', 5),
            ("/path(with)parens", '(', 5),
        ]
        
        for path, char, position in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{path}' should be invalid"
            assert f"illegal character '{char}'" in result
            assert f"position {position}" in result
    
    def test_unicode_supplementary_characters(self):
        """Test paths with Unicode characters outside BMP."""
        test_cases = [
            "/path/with/😀/emoji",     # Emoji
            "/path/with/𐀀/linearb",   # Linear B
            "/path/with/𝐀/mathbold",   # Mathematical bold
            "/path/with/🎵/music",     # Musical note emoji
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{repr(path)}' should be invalid"
            assert "Unicode supplementary character" in result
    
    def test_directory_traversal(self):
        """Test paths with directory traversal sequences."""
        test_cases = [
            "../../etc/passwd",
            "/path/../../../root",
            "/valid/path/../../danger",
            "foo/../../../bar",
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{path}' should be invalid"
            assert "directory traversal sequence (..)" in result
    
    def test_mixed_valid_invalid(self):
        """Test paths with mix of valid and invalid characters."""
        # Should fail on first invalid character found
        path = "/valid/path/then<bad"
        result = validate_path(path)
        assert result is not None
        assert "illegal character '<'" in result
        assert "position 16" in result  # Position of '<'
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Path with just dots (valid)
        assert validate_path("...") is None
        assert validate_path(".") is None
        
        # Path with single dot segments (valid)
        assert validate_path("./foo/./bar/.") is None
        
        # Very long path (should still validate each character)
        long_path = "/very/" + "long/" * 100 + "path.txt"
        assert validate_path(long_path) is None
        
        # Path ending with separator (valid)
        assert validate_path("/path/to/directory/") is None
        
        # Multiple consecutive separators (valid)
        assert validate_path("/path//to///file") is None
    
    def test_real_world_examples(self):
        """Test real-world path examples."""
        # Valid Ada project paths
        valid = [
            "/Users/mike/Ada/github.com/abitofhelp/abohlib/abohlib.gpr",
            "/home/developer/projects/my-ada-lib/src/main.adb",
            "/opt/GNAT/2024/lib/gcc/x86_64-pc-linux-gnu/13.2.0/adainclude/a-except.ads",
            "C:/Users/Developer/Documents/ada_project/tests/unit_test.adb",  # Windows-style
        ]
        
        for path in valid:
            assert validate_path(path) is None, f"Path '{path}' should be valid"
        
        # Invalid Ada project paths
        invalid = [
            "/Users/mike/Ada Projects/my lib.gpr",  # Spaces
            "/home/developer/ada\tproject/src.adb",  # Tab
            "/opt/GNAT/2024/lib/[ada]/include.ads",  # Brackets
            "C:\\Users\\Developer\\ada.gpr",  # Backslashes
        ]
        
        for path in invalid:
            assert validate_path(path) is not None, f"Path '{repr(path)}' should be invalid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])