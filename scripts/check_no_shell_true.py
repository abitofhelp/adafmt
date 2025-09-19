#!/usr/bin/env python3
# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""CI script to detect usage of shell=True in subprocess calls."""

import sys
import re
from pathlib import Path


def check_shell_true(file_path: Path) -> list[tuple[int, str]]:
    """Check a Python file for shell=True usage.
    
    Returns list of (line_number, line_content) tuples.
    """
    violations = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Look for shell=True in subprocess calls
            if 'shell=True' in line and not line.strip().startswith('#'):
                violations.append((line_num, line.strip()))
                
    return violations


def main():
    """Check all Python files in the project for shell=True usage."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / 'src'
    
    total_violations = 0
    files_with_violations = []
    
    # Check all Python files
    for py_file in src_dir.rglob('*.py'):
        violations = check_shell_true(py_file)
        if violations:
            total_violations += len(violations)
            files_with_violations.append((py_file, violations))
    
    # Report results
    if total_violations > 0:
        print(f"❌ Found {total_violations} usage(s) of shell=True in {len(files_with_violations)} file(s):")
        print()
        
        for file_path, violations in files_with_violations:
            relative_path = file_path.relative_to(project_root)
            print(f"  {relative_path}:")
            for line_num, line in violations:
                print(f"    Line {line_num}: {line}")
            print()
        
        print("SECURITY WARNING: Using shell=True can lead to shell injection vulnerabilities.")
        print("Please use list arguments instead of shell=True.")
        sys.exit(1)
    else:
        print("✅ No usage of shell=True found in the codebase.")
        sys.exit(0)


if __name__ == "__main__":
    main()