# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""File discovery module for finding Ada source files.

This module provides functionality to discover Ada source files in a project
based on include and exclude path patterns. It recursively searches directories
and filters files by Ada extensions.

Key features:
    - Recursive directory traversal
    - Support for both file and directory paths
    - Exclude path filtering (affects entire directory trees)
    - Case-insensitive extension matching
    - Deterministic sorted output

Supported Ada file extensions:
    - .ada: Generic Ada source files
    - .ads: Ada specification (spec) files
    - .adb: Ada body (implementation) files
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set

ADA_EXTS = {".ada", ".ads", ".adb"}
"""Set of file extensions recognized as Ada source files."""

def collect_files(include_paths: Iterable[Path], exclude_paths: Iterable[Path]) -> List[Path]:
    """Collect all Ada source files from include paths, filtering by exclude paths.
    
    This function implements an optimized algorithm that avoids redundant scanning:
    1. Resolve all exclude paths to a set for fast lookup
    2. For each include path:
       - If it's a file with Ada extension, add it
       - If it's a directory, walk it recursively, skipping excluded paths
    3. Sort results for deterministic output
    
    Args:
        include_paths: Paths to search for Ada files. Can be files or directories.
                      Directories are searched recursively.
        exclude_paths: Paths to exclude from search. If a directory is excluded,
                      all its subdirectories are also excluded.
    
    Returns:
        Sorted list of resolved Path objects for all discovered Ada files
        
    Note:
        - File paths in include_paths are only included if they have Ada extensions
        - Exclude paths affect both directories and files during traversal
        - All paths are resolved to absolute paths before processing
        - Extension matching is case-insensitive (.ADS matches .ads)
        
    Example:
        >>> files = collect_files(
        ...     include_paths=[Path("src"), Path("tests")],
        ...     exclude_paths=[Path("src/generated")]
        ... )
        >>> # Returns all .ads/.adb files in src/ and tests/, except src/generated/
    """
    files: Set[Path] = set()
    
    # Resolve exclude paths once for efficient checking
    excluded_dirs: Set[Path] = set()
    for ex in exclude_paths:
        ex = ex.resolve()
        if ex.exists():
            excluded_dirs.add(ex)
    
    def should_skip(path: Path) -> bool:
        """Check if a path should be skipped based on exclude list."""
        for excluded in excluded_dirs:
            try:
                # Check if path is relative to (under) the excluded directory
                path.relative_to(excluded)
                return True
            except ValueError:
                # Not relative to this excluded path
                continue
        return False
    
    # Process each include path
    for p in include_paths:
        p = p.resolve()
        
        if p.is_file() and p.suffix.lower() in ADA_EXTS:
            # Direct file inclusion
            files.add(p)
        elif p.is_dir() and not should_skip(p):
            # Directory traversal with exclusion checking
            # Use rglob to recursively find all files, following symlinks
            try:
                for f in p.rglob("*"):
                    # Skip symlinks to avoid infinite loops
                    if f.is_symlink():
                        continue
                    if f.is_file() and f.suffix.lower() in ADA_EXTS and not should_skip(f):
                        files.add(f)
            except (OSError, PermissionError):
                # Handle permission errors or other OS errors gracefully
                # Just skip this directory if we can't access it
                pass
    
    # Sort for deterministic output
    return sorted(files)
