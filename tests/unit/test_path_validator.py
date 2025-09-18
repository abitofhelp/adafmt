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
            "/path with spaces/file.txt",  # Spaces now allowed
            "/path(with)parens/file.adb",  # Parentheses allowed
            "/path[with]brackets/file.ads",  # Brackets allowed
            "/path{with}braces/file.adb",  # Braces allowed
            "/path@with@at/file.gpr",  # @ symbol allowed
            "/path+with+plus/file.ada",  # Plus allowed
            "/path~with~tilde/file.adb",  # Tilde allowed
            "/path!with!exclaim/file.ads",  # Exclamation allowed
            "/path$with$dollar/file.adb",  # Dollar allowed
            "/path'with'quotes/file.gpr",  # Single quotes allowed
            "/path,with,comma/file.ada",  # Comma allowed
            "/path=with=equals/file.adb",  # Equals allowed
        ]
        
        for path in valid_paths:
            assert validate_path(path) is None, f"Path '{path}' should be valid"
    
    def test_empty_path(self):
        """Test empty path validation."""
        assert validate_path("") == "Path cannot be empty"
        
    def test_whitespace_characters(self):
        """Test paths with various whitespace characters."""
        # Regular space is now allowed
        assert validate_path("/path with space/file.txt") is None
        
        # Other whitespace characters are still rejected
        test_cases = [
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
    
    def test_url_schemes(self):
        """Test detection of URL schemes."""
        test_cases = [
            "http://example.com/file.ada",
            "https://github.com/user/project.gpr",
            "file:///home/user/project.adb",
            "ftp://server.com/ada/files",
            "HTTP://EXAMPLE.COM/FILE.ADA",  # Case insensitive
            "File:///C:/Users/test.adb",    # Windows file URL
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{path}' should be detected as URL"
            assert "appears to be a URL" in result
            assert "filesystem path instead" in result
    
    def test_url_encoded_paths(self):
        """Test detection of URL-encoded paths."""
        test_cases = [
            "/path%20with%20spaces",  # %20 = space
            "/path%2Fwith%2Fslash",   # %2F = /
            "/file%3Aname.txt",       # %3A = :
            "/path%21exclamation",    # %21 = !
            "/%E2%9C%93checkmark",    # %E2%9C%93 = ✓ (UTF-8 encoded)
            "/mixed%20path/normal",   # Mix of encoded and normal
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{path}' should be detected as URL-encoded"
            assert "URL-encoded" in result
            assert "decoded path instead" in result
    
    def test_percent_without_encoding(self):
        """Test paths with % that aren't URL-encoded."""
        # These have % but not in %XX format, so should fail for different reason
        test_cases = [
            "/path%with%percent",     # % not followed by 2 hex digits
            "/path%Gwrong",          # %G - G is not hex
            "/path%2",               # %2 - only one hex digit
            "/path%%double",         # %% - not valid encoding
        ]
        
        for path in test_cases:
            result = validate_path(path)
            assert result is not None, f"Path '{path}' should be invalid"
            # Should fail for illegal character, not URL encoding
            assert "illegal character '%'" in result
            assert "URL-encoded" not in result
    
    def test_illegal_characters(self):
        """Test paths with characters not in allowed set."""
        test_cases = [
            ("/path<with>angle", '<', 5),
            ("/path|with|pipe", '|', 5),
            ("/path\\with\\backslash", '\\', 5),
            ("/path\"with\"quotes", '"', 5),
            ("/path#with#hash", '#', 5),
            ("/path%with%percent", '%', 5),
            ("/path^with^caret", '^', 5),
            ("/path*with*star", '*', 5),
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
            "/Users/mike/Ada Projects/my lib.gpr",  # Spaces are now allowed
            "/home/user/My Documents/Ada Code/project.gpr",  # Multiple spaces
        ]
        
        for path in valid:
            assert validate_path(path) is None, f"Path '{path}' should be valid"
        
        # Invalid Ada project paths
        invalid = [
            "/home/developer/ada\tproject/src.adb",  # Tab
            "C:\\Users\\Developer\\ada.gpr",  # Backslashes
            "http://example.com/project.gpr",  # URL scheme
        ]
        
        for path in invalid:
            assert validate_path(path) is not None, f"Path '{repr(path)}' should be invalid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])