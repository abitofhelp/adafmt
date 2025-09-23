# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for parameter association spacing rule.

Tests the AST visitor implementation for fixing spacing around '=>' in
parameter associations, aggregates, and case statements.
"""

from __future__ import annotations

import pytest

from ada2022_parser.generated import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.ast_visitors import ParameterAssociationSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestParameterAssociationSpacing:
    """Test parameter association spacing rule with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after '=>'."""
        return FormattingRules()
    
    @pytest.fixture
    def no_space_rules(self) -> FormattingRules:
        """Create formatting rules with no spaces around '=>'."""
        rules = FormattingRules()
        rules.spacing.parameter_association.parameters.spaces_before = 0
        rules.spacing.parameter_association.parameters.spaces_after = 0
        return rules
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = ParameterAssociationSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_array_aggregate(self, default_rules):
        """Test formatting array aggregate with named associations."""
        ada_code = """procedure Test is
   type Int_Array is array (1 .. 5) of Integer;
   Arr : Int_Array := (1=>10, 2=>20, others=>0);
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "(1 => 10, 2 => 20, others => 0)" in result
        assert "=>" not in result.replace(" => ", "")
    
    def test_record_aggregate(self, default_rules):
        """Test formatting record aggregate."""
        ada_code = """procedure Test is
   type Point is record
      X, Y : Integer;
   end record;
   P : Point := (X=>5, Y=>10);
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "P : Point := (X => 5, Y => 10);" in result
        assert "X=>5" not in result
    
    def test_named_parameter_call(self, default_rules):
        """Test formatting named parameter in subprogram call."""
        ada_code = """procedure Test is
   procedure Process(X: Integer; Y: Integer) is null;
begin
   Process(X=>100, Y=>200);
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Process(X => 100, Y => 200);" in result
        assert "X=>100" not in result
    
    def test_case_statement(self, default_rules):
        """Test formatting case statement alternatives."""
        ada_code = """procedure Test is
   X : Integer := 1;
begin
   case X is
      when 1=>
         null;
      when 2  =>
         null;
      when others=>
         null;
   end case;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "when 1 =>" in result
        assert "when 2 =>" in result
        assert "when others =>" in result
        assert "=>" not in result.replace(" => ", "")
    
    def test_extra_spaces(self, default_rules):
        """Test fixing extra spaces around '=>'."""
        ada_code = """procedure Test is
   type Arr is array (1 .. 2) of Integer;
   A : Arr := (1   =>   10, 2  =>  20);
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "(1 => 10, 2 => 20)" in result
        assert "   =>   " not in result
    
    def test_no_spacing_configuration(self, no_space_rules):
        """Test configuration with no spaces around '=>'."""
        ada_code = """procedure Test is
   type Arr is array (1 .. 2) of Integer;
   A : Arr := (1 => 10, 2 => 20);
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, no_space_rules)
        
        assert "(1=>10, 2=>20)" in result
        assert " => " not in result
    
    def test_protected_string_literal(self, default_rules):
        """Test that '=>' in string literals is not modified."""
        ada_code = """procedure Test is
   Msg : String := "Use => for associations";
   X : Integer := 1;
begin
   case X is
      when 1=> null;
      when others => null;
   end case;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        # String literal should remain unchanged
        assert '"Use => for associations"' in result
        # But case statement should be fixed
        assert "when 1 => null;" in result
    
    def test_disabled_rule(self):
        """Test that formatting is not applied when rule is disabled."""
        rules = FormattingRules()
        rules.spacing.parameter_association.enabled = False
        
        ada_code = """procedure Test is
   type Arr is array (1 .. 2) of Integer;
   A : Arr := (1=>10, 2=>20);
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, rules)
        
        # Should remain unchanged
        assert "(1=>10, 2=>20)" in result