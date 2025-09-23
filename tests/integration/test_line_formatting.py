# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for line formatting rules.

Tests the LineFormattingVisitor implementation for handling
trailing whitespace and final newline normalization.
"""

from __future__ import annotations

import pytest

from adafmt.line_formatting_visitors import LineFormattingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestLineFormatting:
    """Test line formatting rules with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules."""
        return FormattingRules()
    
    @pytest.fixture
    def custom_rules(self) -> FormattingRules:
        """Create custom formatting rules with different newline count."""
        rules = FormattingRules()
        rules.line_formatting.final_newline.parameters.newline_count = 2
        return rules
    
    @pytest.fixture
    def no_newline_rules(self) -> FormattingRules:
        """Create rules with no final newline."""
        rules = FormattingRules()
        rules.line_formatting.final_newline.parameters.newline_count = 0
        return rules
    
    def _apply_formatting(self, ada_code: str, rules: FormattingRules) -> str:
        """Apply line formatting rules to Ada code."""
        visitor = LineFormattingVisitor(rules, ada_code)
        return visitor.apply_edits()
    
    def test_trailing_whitespace_removal(self, default_rules):
        """Test removal of trailing whitespace from lines."""
        ada_code = """procedure Test is   
   X : Integer := 1;     
   Y : Integer := 2;  
begin
   null;  
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        lines = result.split('\n')
        assert lines[0] == "procedure Test is"
        assert lines[1] == "   X : Integer := 1;"
        assert lines[2] == "   Y : Integer := 2;"
        assert lines[4] == "   null;"
    
    def test_no_trailing_whitespace(self, default_rules):
        """Test that lines without trailing whitespace are unchanged."""
        ada_code = """procedure Test is
   X : Integer := 1;
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Should remain unchanged except for final newline
        assert result == ada_code + '\n'
    
    def test_mixed_trailing_whitespace(self, default_rules):
        """Test mixed lines with and without trailing whitespace."""
        ada_code = """procedure Test is
   X : Integer := 1;   
   Y : Integer := 2;
   Z : Integer := 3;     
begin
   null;
end Test;   """
        
        result = self._apply_formatting(ada_code, default_rules)
        
        lines = result.split('\n')
        assert lines[1] == "   X : Integer := 1;"
        assert lines[2] == "   Y : Integer := 2;"
        assert lines[3] == "   Z : Integer := 3;"
        assert lines[6] == "end Test;"
    
    def test_final_newline_missing(self, default_rules):
        """Test adding final newline when missing."""
        ada_code = "procedure Test is\nbegin\n   null;\nend Test;"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert result.endswith('\n')
        assert not result.endswith('\n\n')
    
    def test_final_newline_already_present(self, default_rules):
        """Test that single final newline is preserved."""
        ada_code = "procedure Test is\nbegin\n   null;\nend Test;\n"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert result == ada_code
    
    def test_multiple_final_newlines(self, default_rules):
        """Test normalizing multiple final newlines to one."""
        ada_code = "procedure Test is\nbegin\n   null;\nend Test;\n\n\n"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert result.endswith('\n')
        assert not result.endswith('\n\n')
        assert result == "procedure Test is\nbegin\n   null;\nend Test;\n"
    
    def test_custom_final_newline_count(self, custom_rules):
        """Test custom final newline count (2 newlines)."""
        ada_code = "procedure Test is\nbegin\n   null;\nend Test;"
        
        result = self._apply_formatting(ada_code, custom_rules)
        
        assert result.endswith('\n\n')
        assert not result.endswith('\n\n\n')
    
    def test_no_final_newline_configuration(self, no_newline_rules):
        """Test configuration with no final newline."""
        ada_code = "procedure Test is\nbegin\n   null;\nend Test;\n\n"
        
        result = self._apply_formatting(ada_code, no_newline_rules)
        
        assert not result.endswith('\n')
        assert result == "procedure Test is\nbegin\n   null;\nend Test;"
    
    def test_empty_file(self, default_rules):
        """Test handling of empty file."""
        ada_code = ""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert result == ""
    
    def test_whitespace_only_file(self, default_rules):
        """Test file with only whitespace."""
        ada_code = "   \n  \n \n"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # All trailing whitespace removed, single final newline added
        assert result == "\n\n\n"
    
    def test_disabled_trailing_whitespace_rule(self):
        """Test that trailing whitespace is preserved when rule is disabled."""
        rules = FormattingRules()
        rules.line_formatting.trailing_whitespace.enabled = False
        
        ada_code = """procedure Test is   
   X : Integer := 1;     
end Test;"""
        
        result = self._apply_formatting(ada_code, rules)
        
        # Trailing whitespace should be preserved, only final newline added
        lines = result.split('\n')
        assert lines[0] == "procedure Test is   "
        assert lines[1] == "   X : Integer := 1;     "
    
    def test_disabled_final_newline_rule(self):
        """Test that final newline is not modified when rule is disabled."""
        rules = FormattingRules()
        rules.line_formatting.final_newline.enabled = False
        
        ada_code = """procedure Test is
   X : Integer := 1;  
end Test;\n\n\n"""
        
        result = self._apply_formatting(ada_code, rules)
        
        # Only trailing whitespace should be removed
        assert result == """procedure Test is
   X : Integer := 1;
end Test;\n\n\n"""
    
    def test_both_rules_disabled(self):
        """Test that nothing changes when both rules are disabled."""
        rules = FormattingRules()
        rules.line_formatting.trailing_whitespace.enabled = False
        rules.line_formatting.final_newline.enabled = False
        
        ada_code = """procedure Test is   
   X : Integer := 1;     
end Test;  \n\n"""
        
        result = self._apply_formatting(ada_code, rules)
        
        # Should remain completely unchanged
        assert result == ada_code
    
    def test_tabs_and_spaces(self, default_rules):
        """Test removal of mixed tabs and spaces as trailing whitespace."""
        ada_code = "procedure Test is\t  \n   X : Integer := 1;\t\nend Test;"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        lines = result.split('\n')
        assert lines[0] == "procedure Test is"
        assert lines[1] == "   X : Integer := 1;"
        assert result.endswith('\n')
    
    def test_large_file_performance(self, default_rules):
        """Test performance with a larger file."""
        # Create a file with 1000 lines, some with trailing whitespace
        lines = []
        for i in range(1000):
            if i % 3 == 0:
                lines.append(f"   Line_{i} : Integer := {i};   ")
            else:
                lines.append(f"   Line_{i} : Integer := {i};")
        
        ada_code = "procedure Large_Test is\n" + "\n".join(lines) + "\nbegin\n   null;\nend Large_Test;"
        
        result = self._apply_formatting(ada_code, default_rules)
        
        result_lines = result.split('\n')
        # Check some samples
        assert result_lines[1] == "   Line_0 : Integer := 0;"
        assert result_lines[4] == "   Line_3 : Integer := 3;"
        assert result.endswith('\n')
        assert not result.endswith('\n\n')