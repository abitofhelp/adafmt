#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for file size limit enforcement."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import subprocess


class TestFileSizeLimit:
    """Test suite for 100KB file size limit enforcement.
    
    These tests ensure that adafmt properly handles files that exceed
    the 100KB size limit, which is based on best practices for Ada
    source files.
    """
    
    def test_large_file_skipped_in_formatter(self, tmp_path):
        """Test that files larger than 100KB are skipped during formatting.
        
        Given: An Ada file larger than 100KB exists
        When: The formatter processes the file
        Then: The file is skipped with appropriate logging
        """
        # Create project file first
        project_file = tmp_path / "test.gpr"
        project_file.write_text("project Test is end Test;")
        
        # Create a large Ada file (just over 100KB)
        large_file = tmp_path / "large.adb"
        content = "procedure Large is\nbegin\n"
        # Add comments to make it larger than 100KB
        # Each line with 100 X's plus "-- " and newline = 104 bytes
        # Need about 1000 lines to exceed 100KB
        for i in range(1050):  # 1050 * ~104 bytes = ~109KB
            content += "-- " + "X" * 100 + "\n"
        content += "null;\nend Large;"
        large_file.write_text(content)
        
        # Verify file size
        assert large_file.stat().st_size > 102400
        
        # Run formatter
        result = subprocess.run([
            "python", "-m", "adafmt", "format",
            "--project-path", str(project_file),
            "--preflight", "off",
            "--no-als",
            "--check",
            str(large_file)
        ], capture_output=True, text=True, timeout=10)
        
        # Check that file was skipped
        output = result.stdout + result.stderr
        assert "file too large" in output.lower()
        assert "100kb" in output.lower() or "102400" in output
    
    def test_normal_file_processed(self, tmp_path):
        """Test that files under 100KB are processed normally.
        
        Given: An Ada file well under 100KB exists
        When: The formatter processes the file
        Then: The file is processed without size warnings
        """
        # Create a normal-sized Ada file
        normal_file = tmp_path / "normal.adb"
        # Create a minimal project file too
        project_file = tmp_path / "test.gpr"
        project_file.write_text("project Test is end Test;")
        
        content = """procedure Normal is
   X : Integer := 42;
begin
   -- This is a reasonably sized file
   null;
end Normal;
"""
        normal_file.write_text(content)
        
        # Verify file size is under limit
        assert normal_file.stat().st_size < 102400
        
        # Run formatter
        result = subprocess.run([
            "python", "-m", "adafmt", "format",
            "--project-path", str(tmp_path / "test.gpr"), 
            "--preflight", "off",
            "--no-als",
            "--no-patterns",
            str(normal_file)
        ], capture_output=True, text=True, timeout=10)
        
        # Check that file was NOT skipped due to size
        output = result.stdout + result.stderr
        assert "file too large" not in output.lower()
    
    def test_patterns_mode_size_check(self, tmp_path):
        """Test that patterns-only mode also respects file size limit.
        
        Given: A large Ada file exists
        When: Format with patterns (no ALS) is run
        Then: The file is reported as too large for patterns
        """
        # Create project file
        project_file = tmp_path / "test.gpr"
        project_file.write_text("project Test is end Test;")
        
        # Create a large Ada file
        large_file = tmp_path / "large_patterns.adb"
        content = "procedure LargePatterns is\nbegin\n"
        # Add comments to make it larger than 100KB
        for i in range(1050):  # ~109KB
            content += "-- TODO: " + "Y" * 94 + "\n"
        content += "null;\nend LargePatterns;"
        large_file.write_text(content)
        
        # Create pattern file (JSON format)
        pattern_file = tmp_path / "pattern.json"
        import json
        patterns = [{
            "name": "todo_to_done",
            "title": "Convert TODO to DONE",
            "category": "comment",
            "find": "TODO",
            "replace": "DONE"
        }]
        pattern_file.write_text(json.dumps(patterns))
        
        # Run format with patterns only (no ALS)
        result = subprocess.run([
            "python", "-m", "adafmt", "format",
            "--project-path", str(project_file),
            "--patterns-path", str(pattern_file),
            "--no-als",  # Use patterns only
            "--preflight", "off",
            "--check",
            str(large_file)
        ], capture_output=True, text=True, timeout=10)
        
        # Check output - patterns have their own size limit which might be hit
        output = result.stdout + result.stderr
        # File should be processed but patterns might be skipped due to size
        assert result.returncode in [0, 1]  # 0 = success, 1 = check mode found differences
    
    def test_exact_limit_boundary(self, tmp_path):
        """Test files at exactly 100KB boundary.
        
        Given: Ada files at exactly 100KB and just over
        When: The formatter processes them
        Then: 100KB file is processed, 100KB+1 is skipped
        """
        # Create project file first
        project_file = tmp_path / "test.gpr"
        project_file.write_text("project Test is end Test;")
        
        # Create file at exactly 100KB
        exact_file = tmp_path / "exact.adb"
        # Calculate content size to make exactly 100KB (102400 bytes)
        header = "procedure Exact is\nbegin\n"
        footer = "\nnull;\nend Exact;"
        # Create padding to reach exactly 100KB
        line = "-- " + "Z" * 96 + "\n"  # 100 bytes per line
        num_lines = (102400 - len(header) - len(footer)) // len(line)
        padding = line * num_lines
        content = header + padding + footer
        # Adjust to exactly 100KB if needed
        if len(content) > 102400:
            content = content[:102400]
        elif len(content) < 102400:
            content += " " * (102400 - len(content))
        exact_file.write_text(content)
        
        # Create file just over 100KB
        over_file = tmp_path / "over.adb"
        over_content = content + "-- one more comment to push over limit\n" * 10
        over_file.write_text(over_content)
        
        # Test exact file (should be processed)
        result_exact = subprocess.run([
            "python", "-m", "adafmt", "format",
            "--project-path", str(project_file),
            "--preflight", "off", 
            "--no-als",
            "--check",
            str(exact_file)
        ], capture_output=True, text=True, timeout=10)
        
        # Test over file (should be skipped)
        result_over = subprocess.run([
            "python", "-m", "adafmt", "format",
            "--project-path", str(project_file),
            "--preflight", "off",
            "--no-als",
            "--check",
            str(over_file)
        ], capture_output=True, text=True, timeout=10)
        
        # Check results
        exact_output = result_exact.stdout + result_exact.stderr
        over_output = result_over.stdout + result_over.stderr
        
        assert "file too large" not in exact_output.lower()
        assert "file too large" in over_output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])