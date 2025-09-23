# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for range operator spacing rule.

Tests the AST visitor implementation for fixing spacing around '..' in
range expressions.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from ada2022_parser.generated import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.ast_visitors import RangeOperatorSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestRangeOperatorSpacing:
    """Test range operator spacing rule with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after '..'."""
        return FormattingRules()
    
    @pytest.fixture
    def no_space_rules(self) -> FormattingRules:
        """Create formatting rules with no spaces around '..'."""
        rules = FormattingRules()
        rules.spacing.range_operator.parameters.spaces_before = 0
        rules.spacing.range_operator.parameters.spaces_after = 0
        return rules
    
    @pytest.fixture
    def custom_space_rules(self) -> FormattingRules:
        """Create formatting rules with custom spacing (2 before, 3 after)."""
        rules = FormattingRules()
        rules.spacing.range_operator.parameters.spaces_before = 2
        rules.spacing.range_operator.parameters.spaces_after = 3
        return rules
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = RangeOperatorSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_simple_range_type(self, default_rules):
        """Test formatting range in type declaration."""
        ada_code = """procedure Test is
   type Count is range 0..100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 0 .. 100;" in result
        assert "0..100" not in result
    
    def test_range_with_spaces_around(self, default_rules):
        """Test range that already has extra spaces."""
        ada_code = """procedure Test is
   type Count is range 0   ..   100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 0 .. 100;" in result
        assert "   ..   " not in result
    
    def test_range_in_array_type(self, default_rules):
        """Test range in array type declaration."""
        ada_code = """procedure Test is
   type Int_Array is array (1..10) of Integer;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Int_Array is array (1 .. 10) of Integer;" in result
        assert "1..10" not in result
    
    def test_range_in_for_loop(self, default_rules):
        """Test range in for loop."""
        ada_code = """procedure Test is
begin
   for I in 1..10 loop
      null;
   end loop;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "for I in 1 .. 10 loop" in result
        assert "1..10" not in result
    
    def test_range_in_slice(self, default_rules):
        """Test range in array slice."""
        ada_code = """procedure Test is
   Arr : array (1 .. 10) of Integer;
begin
   Arr(1..5) := (others => 0);
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Arr(1 .. 5) := (others => 0);" in result
        assert "1..5" not in result
    
    def test_range_with_attributes(self, default_rules):
        """Test range using attributes."""
        ada_code = """procedure Test is
   type Natural_Count is range 0..Natural'Last;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Natural_Count is range 0 .. Natural'Last;" in result
        assert "0..Natural" not in result
    
    def test_no_spacing_configuration(self, no_space_rules):
        """Test configuration with no spaces around '..'."""
        ada_code = """procedure Test is
   type Count is range 0  ..  100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, no_space_rules)
        
        assert "type Count is range 0..100;" in result
        assert " .. " not in result
    
    def test_custom_spacing_configuration(self, custom_space_rules):
        """Test configuration with custom spacing (2 before, 3 after)."""
        ada_code = """procedure Test is
   type Count is range 0..100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, custom_space_rules)
        
        assert "type Count is range 0  ..   100;" in result
    
    def test_protected_string_literal(self, default_rules):
        """Test that '..' in string literals is not modified."""
        ada_code = """procedure Test is
   Msg : String := "Range is 1..10";
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        # String literal should remain unchanged
        assert '"Range is 1..10"' in result
        assert '"Range is 1 .. 10"' not in result
    
    def test_protected_comment(self, default_rules):
        """Test that '..' in comments is not modified."""
        ada_code = """procedure Test is
   type Count is range 1..10;  -- Range from 1..10
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 1 .. 10;" in result
        assert "-- Range from 1..10" in result  # Comment unchanged
    
    def test_disabled_rule(self):
        """Test that formatting is not applied when rule is disabled."""
        rules = FormattingRules()
        rules.spacing.range_operator.enabled = False
        
        ada_code = """procedure Test is
   type Count is range 0..100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, rules)
        
        # Should remain unchanged
        assert "type Count is range 0..100;" in result
    
    def test_multiple_ranges(self, default_rules):
        """Test multiple range operators in a single file."""
        ada_code = """procedure Test is
   type Count is range 1..100;
   type Matrix is array (1..10, 1..10) of Integer;
begin
   for I in 1..5 loop
      null;
   end loop;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 1 .. 100;" in result
        assert "type Matrix is array (1 .. 10, 1 .. 10) of Integer;" in result
        assert "for I in 1 .. 5 loop" in result
        # Ensure no unspaced ranges remain
        assert ".." not in result.replace(" .. ", "")