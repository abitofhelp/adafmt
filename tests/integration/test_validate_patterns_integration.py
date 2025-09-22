# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for --validate-patterns flag."""

import json
import subprocess
import pytest


class TestValidatePatternsIntegration:
    """Test the --validate-patterns flag functionality."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary Ada project."""
        # Create project file
        project_gpr = tmp_path / "test.gpr"
        project_gpr.write_text("""
project Test is
   for Source_Dirs use ("src");
end Test;
""")
        
        # Create src directory
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        return tmp_path
    
    def test_validate_patterns_success(self, temp_project):
        """Test validation when patterns don't conflict with ALS."""
        # Create a pattern that ALS won't change
        patterns = [
            {
                "name": "comment_norm",
                "title": "Normalize comment spacing",
                "category": "comment",
                "find": " -- ",
                "replace": " --  "  # Standard comment spacing
            }
        ]
        
        patterns_file = temp_project / "adafmt_patterns.json"
        patterns_file.write_text(json.dumps(patterns))
        
        # Create test file
        test_file = temp_project / "src" / "test.adb"
        test_file.write_text("""procedure Test is
begin
   null; -- This is a comment
end Test;
""")
        
        # Run validation
        result = subprocess.run(
            ["adafmt", "format", "--project-path", str(temp_project / "test.gpr"),
             "--include-path", str(temp_project / "src"),
             "--validate-patterns", "--patterns-path", str(patterns_file)],
            capture_output=True,
            text=True,
            cwd=temp_project
        )
        
        # Should succeed
        assert result.returncode == 0
        assert "All 1 files validated successfully!" in result.stdout
    
    def test_validate_patterns_conflict(self, temp_project):
        """Test validation when patterns conflict with ALS formatting."""
        # Create a pattern that removes spaces ALS wants
        patterns = [
            {
                "name": "bad_spacing1",
                "title": "Remove assignment spacing",
                "category": "operator",
                "find": " := ",
                "replace": ":="  # ALS will want to add spaces back
            }
        ]
        
        patterns_file = temp_project / "adafmt_patterns.json"
        patterns_file.write_text(json.dumps(patterns))
        
        # Create test file
        test_file = temp_project / "src" / "test.adb"
        test_file.write_text("""procedure Test is
   X : Integer := 42;
begin
   X := X + 1;
end Test;
""")
        
        # Run validation
        result = subprocess.run(
            ["adafmt", "format", "--project-path", str(temp_project / "test.gpr"),
             "--include-path", str(temp_project / "src"),
             "--validate-patterns", "--patterns-path", str(patterns_file)],
            capture_output=True,
            text=True,
            cwd=temp_project
        )
        
        # Should fail
        assert result.returncode == 1
        assert "validation failed" in result.stdout.lower()
    
    def test_validate_patterns_no_patterns(self, temp_project):
        """Test validation with --no-patterns flag."""
        # Create a test file
        test_file = temp_project / "src" / "test.adb"
        test_file.write_text("procedure Test is begin null; end Test;")
        
        # Run validation with no patterns
        result = subprocess.run(
            ["adafmt", "format", "--project-path", str(temp_project / "test.gpr"),
             "--include-path", str(temp_project / "src"),
             "--validate-patterns", "--no-patterns"],
            capture_output=True,
            text=True,
            cwd=temp_project
        )
        
        # Should fail with error message about conflicting options
        assert result.returncode == 2
        assert "Cannot use --validate-patterns with --no-patterns" in result.stderr
    
    def test_validate_patterns_empty_file(self, temp_project):
        """Test validation with empty pattern file."""
        # Create empty patterns file
        patterns_file = temp_project / "adafmt_patterns.json"
        patterns_file.write_text("[]")
        
        # Run validation
        result = subprocess.run(
            ["adafmt", "format", "--project-path", str(temp_project / "test.gpr"),
             "--include-path", str(temp_project / "src"),
             "--validate-patterns", "--patterns-path", str(patterns_file)],
            capture_output=True,
            text=True,
            cwd=temp_project
        )
        
        # Should fail because no patterns to validate
        assert result.returncode == 1
        assert "No patterns loaded for validation" in result.stdout
    
    def test_validate_patterns_with_multiple_files(self, temp_project):
        """Test validation across multiple files."""
        # Create patterns
        patterns = [
            {
                "name": "ws_trail_sp1",  # Must be 12 chars
                "title": "Remove trailing whitespace",
                "category": "hygiene",
                "find": "[ \\t]+$",
                "replace": "",
                "flags": ["MULTILINE"]
            },
            {
                "name": "eof_newline1",  # Must be 12 chars
                "title": "Ensure newline at EOF",
                "category": "hygiene",
                "find": "(?<![\\n])\\Z",
                "replace": "\\n",
                "flags": ["MULTILINE"]
            }
        ]
        
        patterns_file = temp_project / "adafmt_patterns.json"
        patterns_file.write_text(json.dumps(patterns))
        
        # Create multiple test files
        (temp_project / "src" / "test1.adb").write_text("""procedure Test1 is
begin
   null; -- Comment
end Test1;
""")
        
        (temp_project / "src" / "test2.adb").write_text("""procedure Test2 is
   X : Integer := 1+2;  -- Addition
begin
   null;
end Test2;
""")
        
        # Run validation
        result = subprocess.run(
            ["adafmt", "format", "--project-path", str(temp_project / "test.gpr"),
             "--include-path", str(temp_project / "src"),
             "--validate-patterns", "--patterns-path", str(patterns_file)],
            capture_output=True,
            text=True,
            cwd=temp_project
        )
        
        # Should succeed
        assert result.returncode == 0
        assert "All 2 files validated successfully!" in result.stdout