# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for pattern formatter functionality.

These tests verify the pattern formatter behavior with real files,
multiple patterns, and complex pattern interactions.
"""

import json
from pathlib import Path
import pytest

from adafmt.pattern_formatter import PatternFormatter


class TestPatternIntegration:
    """Integration tests for pattern formatter."""
    
    def test_real_world_patterns(self, tmp_path):
        """Test with real-world Ada patterns."""
        patterns = [
            {
                "name": "assign_set01",
                "title": "Spaces around :=",
                "category": "operator",
                "find": r"^(?P<head>(?:(?:[^\"\n]*\"){2})*[^\"\n]*?)(?P<lhs>\w)\s*:=\s*(?P<rhs>\S)",
                "replace": r"\g<head>\g<lhs> := \g<rhs>",
                "flags": ["MULTILINE"]
            },
            {
                "name": "range_dots01",
                "title": "Spaces around ..",
                "category": "operator", 
                "find": r"\s*\.\.\s*",
                "replace": " .. "
            },
            {
                "name": "comma_space1",
                "title": "Space after comma",
                "category": "delimiter",
                "find": r"\s*,\s*(?=[^\s\)])",
                "replace": ", "
            }
        ]
        
        json_file = tmp_path / "ada_patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        content = """procedure Test is
   X,Y,Z:Integer:=42;
   type Range_Type is range 1..100;
   A:array(1..10) of Integer;
begin
   for I in 1..10 loop
      A(I):=I;
   end loop;
end Test;"""
        
        result, stats = formatter.apply(Path("test.adb"), content)
        
        # Check that patterns were applied
        assert " := " in result  # Assignment spacing
        assert " .. " in result  # Range spacing
        assert ", " in result   # Comma spacing
        assert stats.replacements_sum > 0
    
    def test_pattern_sorting(self, tmp_path):
        """Test that patterns are applied in name order."""
        patterns = [
            {
                "name": "zzzz-last-01",
                "title": "Should run last",
                "category": "comment",
                "find": r"FIRST",
                "replace": "SECOND"
            },
            {
                "name": "aaaa-frst-01",
                "title": "Should run first",
                "category": "comment",
                "find": r"test",
                "replace": "FIRST"
            }
        ]
        
        json_file = tmp_path / "ordered.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        content = "test content"
        result, stats = formatter.apply(Path("test.adb"), content)
        
        # First pattern changes "test" to "FIRST"
        # Second pattern changes "FIRST" to "SECOND"
        assert result == "SECOND content"
        assert len(stats.applied_names) == 2
        # Verify order
        assert stats.applied_names[0] == "aaaa-frst-01"
        assert stats.applied_names[1] == "zzzz-last-01"
