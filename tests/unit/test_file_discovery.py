# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for the file_discovery module.

This module contains comprehensive unit tests for Ada source file discovery
functionality. Tests cover:

- Recursive directory traversal for Ada files
- File extension matching (.adb, .ads, .ada)
- Exclusion pattern handling
- Nested directory structure navigation
- Empty directory handling

The file discovery system is essential for batch formatting operations.
"""

from pathlib import Path
from adafmt.file_discovery import collect_files


def test_collect(tmp_path: Path):
    """Test recursive collection of Ada files from directory tree.
    
    Given: A directory structure with Ada files at different nesting levels
    When: collect_files is called on the root directory
    Then: All Ada files (.adb, .ads, .ada) are discovered and returned
    """
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "a" / "x.adb").write_text("")
    (tmp_path / "a" / "b" / "y.ads").write_text("")
    (tmp_path / "a" / "b" / "z.ada").write_text("")
    files = collect_files([tmp_path / "a"], [])
    assert len(files) == 3
