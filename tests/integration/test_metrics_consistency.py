#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for metrics consistency across different modes."""

import json
import re
import subprocess
import tempfile
from pathlib import Path
import pytest

@pytest.mark.integration
class TestMetricsConsistency:
    """Test that metrics are consistent across ALS-only, patterns-only, and combined modes."""
    
    @pytest.fixture
    def test_project(self):
        """Create a temporary test project with Ada files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create project file
            gpr_content = """project Test is
   for Source_Dirs use (".");
end Test;"""
            (project_dir / "test.gpr").write_text(gpr_content)
            
            # Create test files with various formatting issues
            test_files = {
                "file1.adb": """procedure File1 is
   X:Integer:=5;  -- spacing issues with := operator
   Y : Integer  :=  10  ;   -- more spacing issues    
begin
   X:=X+1;
   Y  :=  Y  +  2  ;     
end File1;""",
                
                "file2.adb": """procedure File2 is
   A,B,C:Integer;  -- comma spacing
   Range_Val : Integer := 1..10;  -- range dots spacing
begin
   if A>B then  -- comment spacing
      null ;  -- semicolon spacing
   end if;   
end File2;""",
                
                "file3.adb": """procedure File3 is
begin
   -- This file is already well formatted
   null;
end File3;""",
            }
            
            for filename, content in test_files.items():
                (project_dir / filename).write_text(content)
            
            yield project_dir
    
    def run_adafmt(self, project_dir: Path, extra_args: list) -> tuple[str, str, int]:
        """Run adafmt and return (stdout, stderr, exit_code)."""
        cmd = [
            "python3", "-m", "adafmt", "format",
            "--project-path", str(project_dir / "test.gpr"),
            "--include-path", str(project_dir),
        ] + extra_args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        return result.stdout, result.stderr, result.returncode
    
    def extract_metrics(self, output: str) -> dict:
        """Extract metrics from adafmt output."""
        metrics = {}
        
        # Extract ALS metrics
        als_match = re.search(
            r'ALS METRICS\s+Files\s+(\d+)\s+\d+%\s+'
            r'Changed\s+(\d+)\s+\d+%\s+'
            r'Unchanged\s+(\d+)\s+\d+%\s+'
            r'Failed\s+(\d+)', 
            output
        )
        if als_match:
            metrics['als'] = {
                'files': int(als_match.group(1)),
                'changed': int(als_match.group(2)),
                'unchanged': int(als_match.group(3)),
                'failed': int(als_match.group(4)),
            }
        
        # Extract pattern metrics
        pattern_match = re.search(
            r'PATTERN METRICS\s+Files\s+(\d+)\s+\d+%',
            output
        )
        if pattern_match:
            metrics['patterns'] = {
                'files': int(pattern_match.group(1))
            }
            
            # Count pattern applications
            pattern_lines = re.findall(r'(\w+)\s+(\d+)\s+(\d+)\s+(\d+)', output)
            total_applied = 0
            total_replaced = 0
            for line in pattern_lines:
                if line[0] not in ('Totals', 'Pattern'):
                    total_applied += int(line[1])
                    total_replaced += int(line[2])
            
            metrics['patterns']['applied'] = total_applied
            metrics['patterns']['replaced'] = total_replaced
        
        return metrics
    
    def test_metrics_consistency(self, test_project):
        """Test that metrics sum correctly across different modes."""
        patterns_path = Path(__file__).parent.parent.parent / "tests/patterns/test_patterns.json"
        
        # Run ALS-only mode
        stdout_als, stderr_als, exit_als = self.run_adafmt(test_project, ["--no-patterns"])
        print(f"\nALS-only stdout:\n{stdout_als}")
        print(f"\nALS-only stderr:\n{stderr_als}")
        print(f"\nALS-only exit code: {exit_als}")
        metrics_als = self.extract_metrics(stdout_als)
        
        # Run patterns-only mode  
        stdout_patterns, stderr_patterns, _ = self.run_adafmt(test_project, [
            "--no-als", 
            "--patterns-path", str(patterns_path)
        ])
        print(f"\n\nPatterns-only stdout:\n{stdout_patterns}")
        print(f"\nPatterns-only stderr:\n{stderr_patterns}")
        metrics_patterns = self.extract_metrics(stdout_patterns)
        
        # Run combined mode
        stdout_combined, stderr_combined, _ = self.run_adafmt(test_project, [
            "--patterns-path", str(patterns_path)
        ])
        print(f"\n\nCombined stdout:\n{stdout_combined}")
        print(f"\nCombined stderr:\n{stderr_combined}")
        metrics_combined = self.extract_metrics(stdout_combined)
        
        # Verify files count is consistent
        assert 'als' in metrics_als
        assert 'patterns' in metrics_patterns
        assert 'als' in metrics_combined
        assert 'patterns' in metrics_combined
        
        # All modes should process the same number of files
        files_count = metrics_als['als']['files']
        assert metrics_patterns['patterns']['files'] == files_count
        assert metrics_combined['als']['files'] == files_count
        assert metrics_combined['patterns']['files'] == files_count
        
        # Combined mode ALS metrics should match ALS-only mode
        # (ALS behavior shouldn't change based on whether patterns are enabled)
        assert metrics_combined['als']['changed'] == metrics_als['als']['changed']
        assert metrics_combined['als']['unchanged'] == metrics_als['als']['unchanged']
        assert metrics_combined['als']['failed'] == metrics_als['als']['failed']
        
        # Pattern metrics will differ between modes because:
        # - Patterns-only: patterns fix all issues they can find
        # - Combined mode: ALS fixes many issues first, leaving fewer for patterns
        # This is expected behavior - we just verify both modes found patterns
        assert metrics_patterns['patterns']['applied'] > 0
        assert metrics_combined['patterns']['applied'] > 0
        # Combined mode should have fewer pattern applications since ALS fixed some issues
        assert metrics_combined['patterns']['applied'] < metrics_patterns['patterns']['applied']
        
        # Print results for debugging
        print("\n\n=== METRICS SUMMARY ===")
        print(f"ALS-only: {metrics_als}")
        print(f"Patterns-only: {metrics_patterns}")
        print(f"Combined: {metrics_combined}")
        
        # Show the mismatch
        print(f"\nPattern applications mismatch:")
        print(f"  Patterns-only: {metrics_patterns['patterns']['applied']}")
        print(f"  Combined mode: {metrics_combined['patterns']['applied']}")
        
    def test_no_als_shows_only_pattern_metrics(self, test_project):
        """Test that --no-als shows only PATTERN METRICS section."""
        patterns_path = Path(__file__).parent.parent.parent / "tests/patterns/test_patterns.json"
        stdout, _, _ = self.run_adafmt(test_project, [
            "--no-als",
            "--patterns-path", str(patterns_path)
        ])
        
        assert "ALS METRICS" not in stdout
        assert "PATTERN METRICS" in stdout
        
    def test_no_patterns_shows_only_als_metrics(self, test_project):
        """Test that --no-patterns shows only ALS METRICS section."""
        stdout, _, _ = self.run_adafmt(test_project, ["--no-patterns"])
        
        assert "ALS METRICS" in stdout
        assert "PATTERN METRICS" not in stdout