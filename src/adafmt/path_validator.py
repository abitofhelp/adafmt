#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Path validation utilities for adafmt.

This module provides functions to validate file and directory paths.
Paths are rejected if they contain:
- Unicode characters outside the Basic Multilingual Plane (U+10000 and above)
- ISO control characters
- Whitespace characters
- Characters not matching the allowed pattern
"""

import re
import unicodedata
from typing import Optional


def is_supplementary_code_point(char: str) -> bool:
    """Check if a character is outside the Basic Multilingual Plane.
    
    Supplementary characters have code points in the range U+10000 to U+10FFFF.
    The Basic Multilingual Plane (BMP) contains characters from U+0000 to U+FFFF.
    
    Args:
        char: Single character to check
        
    Returns:
        True if character is outside BMP, False otherwise
    """
    return ord(char) > 0xFFFF


def validate_path(input_path: str) -> Optional[str]:
    """Validate a file/directory path for illegal characters.
    
    Checks for:
    - URL schemes (http://, https://, file://)
    - URL-encoded sequences (e.g., %20, %2F)
    - Unicode characters outside the Basic Multilingual Plane
    - ISO control characters
    - Whitespace characters other than space
    - Characters not matching the allowed pattern
    
    Args:
        input_path: The path string to validate
        
    Returns:
        None if valid, error message if invalid
    """
    if not input_path:
        return "Path cannot be empty"
    
    # Check for URL schemes
    url_schemes = ['http://', 'https://', 'file://', 'ftp://']
    for scheme in url_schemes:
        if input_path.lower().startswith(scheme):
            return f"Path appears to be a URL ({scheme}). Please provide a filesystem path instead"
    
    # Check for URL-encoded sequences
    if '%' in input_path:
        # Pattern to match URL encoding: %XX where XX are hexadecimal digits
        url_encoded_pattern = re.compile(r'%[0-9A-Fa-f]{2}')
        if url_encoded_pattern.search(input_path):
            return "Path appears to be URL-encoded. Please provide the decoded path instead"
    
    # Updated pattern for allowed characters - now includes space and more common chars
    # Letters, numbers, space, and common path characters
    # Removed: < > | " * ? \ (unsafe across platforms)
    # Kept: & = from original pattern for compatibility
    allowed_pattern = re.compile(r'^[A-Za-z0-9 ._:/@()[\]{},!$+=~`\'&\-]+$')
    
    for i, char in enumerate(input_path):
        # Check for supplementary Unicode characters (outside BMP)
        if is_supplementary_code_point(char):
            return f"Path contains Unicode supplementary character at position {i}"
            
        # Check for whitespace other than regular space
        if char.isspace() and char != ' ':
            return f"Path contains whitespace character '{repr(char)}' at position {i}"
            
        # Check for control characters
        if unicodedata.category(char) in ('Cc', 'Cf', 'Co', 'Cn'):
            return f"Path contains control character '{repr(char)}' at position {i}"
            
        # Check if character matches allowed pattern
        if not allowed_pattern.match(char):
            return f"Path contains illegal character '{char}' at position {i}"
    
    # Additional validation - only check for .. as a complete path segment
    path_segments = input_path.split('/')
    if '..' in path_segments:
        return "Path contains directory traversal sequence (..)"
    
    return None  # Path is valid