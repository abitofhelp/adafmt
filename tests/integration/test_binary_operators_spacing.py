# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for binary operators spacing rule.

Tests the AST visitor implementation for fixing spacing around +, -, *, /
and other configured binary operators.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr

import pytest

from ada2022_parser.generated import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.ast_visitors import BinaryOperatorSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestBinaryOperatorsSpacing:
    """Test binary operators spacing rule with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after operators."""
        return FormattingRules()
    
    @pytest.fixture
    def no_space_rules(self) -> FormattingRules:
        """Create formatting rules with no spaces around operators."""
        rules = FormattingRules()
        rules.spacing.binary_operators.parameters.spaces_before = 0
        rules.spacing.binary_operators.parameters.spaces_after = 0
        return rules
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = BinaryOperatorSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_basic_addition(self, default_rules):
        """Test formatting basic addition."""
        ada_code = """procedure Test is
   X : Integer := 1+2;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 1 + 2;" in result
        assert "1+2" not in result
    
    def test_basic_subtraction(self, default_rules):
        """Test formatting basic subtraction."""
        ada_code = """procedure Test is
   X : Integer := 3-4;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 3 - 4;" in result
        assert "3-4" not in result
    
    def test_basic_multiplication(self, default_rules):
        """Test formatting basic multiplication."""
        ada_code = """procedure Test is
   X : Integer := 5*6;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 5 * 6;" in result
        assert "5*6" not in result
    
    def test_basic_division(self, default_rules):
        """Test formatting basic division."""
        ada_code = """procedure Test is
   X : Integer := 8/2;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 8 / 2;" in result
        assert "8/2" not in result
    
    def test_complex_expression(self, default_rules):
        """Test formatting complex expression with multiple operators."""
        ada_code = """procedure Test is
   X : Integer := (1+2)*3-4/5;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := (1 + 2) * 3 - 4 / 5;" in result
    
    def test_extra_spaces(self, default_rules):
        """Test fixing extra spaces around operators."""
        ada_code = """procedure Test is
   X : Integer := 1   +   2   *   3;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 1 + 2 * 3;" in result
        assert "   +   " not in result
    
    def test_no_spacing_configuration(self, no_space_rules):
        """Test configuration with no spaces around operators."""
        ada_code = """procedure Test is
   X : Integer := 1 + 2 * 3;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, no_space_rules)
        
        assert "X : Integer := 1+2*3;" in result
        assert " + " not in result
        assert " * " not in result
    
    def test_unary_minus_not_affected(self, default_rules):
        """Test that unary minus is not treated as binary operator."""
        ada_code = """procedure Test is
   X : Integer := -5;
   Y : Integer := 10 + -5;
begin
   null;
end Test;"""
        
        # Suppress expected parser warning for "10 + -5" expression
        with redirect_stderr(io.StringIO()):
            result = self._parse_and_format(ada_code, default_rules)
        
        # Unary minus should not have space added
        assert "X : Integer := -5;" in result
        # Binary operators should still be spaced
        assert "Y : Integer := 10 + -5;" in result
    
    def test_protected_string_literal(self, default_rules):
        """Test that operators in string literals are not modified."""
        ada_code = """procedure Test is
   Msg : String := "1+2=3";
   X : Integer := 1+2;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        # String literal should remain unchanged
        assert '"1+2=3"' in result
        # But code should be fixed
        assert "X : Integer := 1 + 2;" in result
    
    def test_disabled_rule(self):
        """Test that formatting is not applied when rule is disabled."""
        rules = FormattingRules()
        rules.spacing.binary_operators.enabled = False
        
        ada_code = """procedure Test is
   X : Integer := 1+2*3;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, rules)
        
        # Should remain unchanged
        assert "X : Integer := 1+2*3;" in result