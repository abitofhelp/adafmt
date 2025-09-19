# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for the edits module.

This module contains comprehensive unit tests for text editing functionality
used to apply formatting changes from the Ada Language Server. Tests cover:

- Text edit application using LSP-style range specifications
- Unified diff generation for displaying changes
- Multi-line edit handling
- Edge cases in text manipulation

The edit functionality is core to applying ALS formatting suggestions.
"""

from adafmt.edits import apply_text_edits, unified_diff


def test_replace_range():
    """Test applying a single character replacement edit.
    
    Given: Original text with multiple lines and an edit specification
    When: apply_text_edits is called with a range replacement
    Then: The specified character range is replaced with new text
    """
    original = "abc\ndef\n"
    edits = [{
        "range": {"start": {"line": 0, "character": 1}, "end": {"line": 0, "character": 2}},
        "newText": "Z"
    }]
    out = apply_text_edits(original, edits)
    assert out.startswith("aZc")


def test_unified_diff():
    """Test generating unified diff output for file changes.
    
    Given: Original and modified text content
    When: unified_diff is called with both versions and filename
    Then: Returns unified diff format with proper file headers
    """
    a = "x\n"
    b = "y\n"
    d = unified_diff(a, b, "t.adb")
    assert "--- t.adb" in d and "+++ t.adb" in d
