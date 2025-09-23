# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for type declaration spacing rule.

Tests the AST visitor implementation for fixing spacing around 'is' in
type declarations.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from ada2022_parser.generated import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.ast_visitors import TypeDeclarationSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestTypeDeclarationSpacing:
    """Test type declaration spacing rule with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after 'is'."""
        return FormattingRules()
    
    @pytest.fixture
    def no_space_rules(self) -> FormattingRules:
        """Create formatting rules with no spaces around 'is'."""
        rules = FormattingRules()
        rules.spacing.type_declaration.parameters.spaces_before = 0
        rules.spacing.type_declaration.parameters.spaces_after = 0
        return rules
    
    @pytest.fixture
    def custom_space_rules(self) -> FormattingRules:
        """Create formatting rules with custom spacing (2 before, 3 after)."""
        rules = FormattingRules()
        rules.spacing.type_declaration.parameters.spaces_before = 2
        rules.spacing.type_declaration.parameters.spaces_after = 3
        return rules
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = TypeDeclarationSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_simple_range_type(self, default_rules):
        """Test formatting simple range type declaration."""
        ada_code = """procedure Test is
   type Count  is  range 0 .. 100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 0 .. 100;" in result
        assert "  is  " not in result
    
    def test_multiple_spaces_before_and_after_is(self, default_rules):
        """Test fixing multiple spaces around 'is'."""
        ada_code = """procedure Test is
   type Natural_Count   is   range 0 .. Natural'Last;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Natural_Count is range 0 .. Natural'Last;" in result
        assert "   is   " not in result
    
    def test_record_type_declaration(self, default_rules):
        """Test formatting record type declaration."""
        ada_code = """procedure Test is
   type Point    is    record
      X, Y : Integer;
   end record;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Point is record" in result
        assert "    is    " not in result
    
    def test_access_type_declaration(self, default_rules):
        """Test formatting access type declaration."""
        ada_code = """procedure Test is
   type String_Access  is  access String;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type String_Access is access String;" in result
        assert "  is  " not in result
    
    def test_subtype_declaration(self, default_rules):
        """Test formatting subtype declaration."""
        ada_code = """procedure Test is
   type Count is range 0 .. 100;
   subtype Small_Count    is    Count range 0 .. 10;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "subtype Small_Count is Count range 0 .. 10;" in result
        assert "    is    " not in result
    
    def test_no_spacing_configuration(self, no_space_rules):
        """Test configuration with no spaces around 'is'."""
        ada_code = """procedure Test is
   type Count   is   range 0 .. 100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, no_space_rules)
        
        assert "type Countisrange 0 .. 100;" in result
        assert " is " not in result
    
    def test_custom_spacing_configuration(self, custom_space_rules):
        """Test configuration with custom spacing (2 before, 3 after)."""
        ada_code = """procedure Test is
   type Count is range 0 .. 100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, custom_space_rules)
        
        assert "type Count  is   range 0 .. 100;" in result
    
    def test_array_type_declaration(self, default_rules):
        """Test formatting array type declaration."""
        ada_code = """procedure Test is
   type Int_Array    is    array (1 .. 10) of Integer;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Int_Array is array (1 .. 10) of Integer;" in result
        assert "    is    " not in result
    
    def test_modular_type_declaration(self, default_rules):
        """Test formatting modular type declaration."""
        ada_code = """procedure Test is
   type Byte  is  mod 256;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Byte is mod 256;" in result
        assert "  is  " not in result
    
    def test_new_type_declaration(self, default_rules):
        """Test formatting derived type declaration."""
        ada_code = """procedure Test is
   type My_Integer   is   new Integer;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type My_Integer is new Integer;" in result
        assert "   is   " not in result
    
    def test_disabled_rule(self):
        """Test that formatting is not applied when rule is disabled."""
        rules = FormattingRules()
        rules.spacing.type_declaration.enabled = False
        
        ada_code = """procedure Test is
   type Count    is    range 0 .. 100;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, rules)
        
        # Should remain unchanged
        assert "type Count    is    range 0 .. 100;" in result
    
    def test_multiple_type_declarations(self, default_rules):
        """Test multiple type declarations in a single file."""
        ada_code = """procedure Test is
   type Count  is  range 0 .. 100;
   type Natural_Count   is   range 0 .. Natural'Last;
   type Point    is    record
      X, Y : Integer;
   end record;
   subtype Small   is   Count range 1 .. 10;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "type Count is range 0 .. 100;" in result
        assert "type Natural_Count is range 0 .. Natural'Last;" in result
        assert "type Point is record" in result
        assert "subtype Small is Count range 1 .. 10;" in result
        # Ensure no extra spaces remain
        assert "  is  " not in result
        assert "   is   " not in result
        assert "    is    " not in result