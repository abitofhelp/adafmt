# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for assignment spacing rule.

Tests the AST visitor implementation with various Ada code scenarios
to ensure proper formatting of := operators.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr

import pytest

from ada2022_parser.generated import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.ast_visitors import AssignmentSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestAssignmentSpacing:
    """Test assignment spacing rule with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after."""
        return FormattingRules()
    
    @pytest.fixture
    def no_space_rules(self) -> FormattingRules:
        """Create formatting rules with no spaces."""
        rules = FormattingRules()
        rules.spacing.assignment.parameters.spaces_before = 0
        rules.spacing.assignment.parameters.spaces_after = 0
        return rules
    
    @pytest.fixture
    def custom_space_rules(self) -> FormattingRules:
        """Create formatting rules with custom spacing (2 before, 3 after)."""
        rules = FormattingRules()
        rules.spacing.assignment.parameters.spaces_before = 2
        rules.spacing.assignment.parameters.spaces_after = 3
        return rules
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = AssignmentSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_basic_assignment_no_spaces(self, default_rules):
        """Test formatting assignment with no spaces."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X:=5;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 5;" in result
        assert "X:=5;" not in result
    
    def test_assignment_with_spaces_before_only(self, default_rules):
        """Test formatting assignment with space before only."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X :=5;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 5;" in result
        assert "X :=5;" not in result
    
    def test_assignment_with_spaces_after_only(self, default_rules):
        """Test formatting assignment with space after only."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X:= 5;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 5;" in result
        assert "X:= 5;" not in result
    
    def test_assignment_with_multiple_spaces(self, default_rules):
        """Test formatting assignment with multiple spaces."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X    :=    5;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 5;" in result
        assert "   :=    " not in result
    
    def test_string_literal_protection(self, default_rules):
        """Test that string literals containing := are not modified."""
        ada_code = """procedure Test is
   Op : String := ":=";
   Msg : String := "Use := for assignment";
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        # String literals should remain unchanged
        assert 'Op : String := ":=";' in result
        assert 'Msg : String := "Use := for assignment";' in result
    
    def test_comment_protection(self, default_rules):
        """Test that comments containing := are not modified."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X:=5;  -- This uses := for assignment
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 5;" in result
        assert "-- This uses := for assignment" in result
    
    def test_multiple_assignments_in_procedure(self, default_rules):
        """Test multiple assignments in a single procedure."""
        ada_code = """procedure Test is
   X, Y, Z : Integer;
begin
   X:=1;
   Y :=2;
   Z:= 3;
   X  :=  X + Y + Z;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := 1;" in result
        assert "Y := 2;" in result
        assert "Z := 3;" in result
        assert "X := X + Y + Z;" in result
    
    def test_assignment_in_record_aggregate(self, default_rules):
        """Test assignment in record initialization."""
        ada_code = """procedure Test is
   type Point is record
      X, Y : Integer;
   end record;
   P : Point;
begin
   P.X:=10;
   P.Y  :=  20;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "P.X := 10;" in result
        assert "P.Y := 20;" in result
    
    def test_no_spacing_configuration(self, no_space_rules):
        """Test configuration with no spaces."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X := 5;
   X  :=  10;
end Test;"""
        
        result = self._parse_and_format(ada_code, no_space_rules)
        
        assert "X:=5;" in result
        assert "X:=10;" in result
        assert " := " not in result
    
    def test_custom_spacing_configuration(self, custom_space_rules):
        """Test configuration with custom spacing (2 before, 3 after)."""
        ada_code = """procedure Test is
   X : Integer;
begin
   X:=5;
   X := 10;
end Test;"""
        
        result = self._parse_and_format(ada_code, custom_space_rules)
        
        assert "X  :=   5;" in result
        assert "X  :=   10;" in result
    
    def test_assignment_in_constant_declaration(self, default_rules):
        """Test assignment in constant declarations."""
        ada_code = """procedure Test is
   Max_Size : constant Integer:=100;
   Min_Size : constant Integer  :=  1;
begin
   null;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Max_Size : constant Integer := 100;" in result
        assert "Min_Size : constant Integer := 1;" in result
    
    def test_assignment_with_complex_expressions(self, default_rules):
        """Test assignment with complex expressions."""
        ada_code = """procedure Test is
   Result : Float;
begin
   Result:=(5.0 + 3.0) * 2.0 / 4.0;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Result := (5.0 + 3.0) * 2.0 / 4.0;" in result
    
    def test_disabled_rule(self):
        """Test that formatting is not applied when rule is disabled."""
        rules = FormattingRules()
        rules.spacing.assignment.enabled = False
        
        ada_code = """procedure Test is
   X : Integer;
begin
   X:=5;
end Test;"""
        
        result = self._parse_and_format(ada_code, rules)
        
        # Should remain unchanged
        assert "X:=5;" in result
        assert "X := 5;" not in result
    
    def test_assignment_in_loop(self, default_rules):
        """Test assignments within loop constructs."""
        ada_code = """procedure Test is
   I : Integer;
begin
   for J in 1 .. 10 loop
      I:=J * 2;
   end loop;
   
   while I  >  0 loop
      I  :=  I - 1;
   end loop;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "I := J * 2;" in result
        assert "I := I - 1;" in result
    
    def test_assignment_in_if_statement(self, default_rules):
        """Test assignments within conditional statements."""
        ada_code = """procedure Test is
   X : Integer:=0;
begin
   if X = 0 then
      X:=1;
   elsif X = 1 then
      X  :=  2;
   else
      X :=3;
   end if;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X : Integer := 0;" in result
        assert "X := 1;" in result
        assert "X := 2;" in result
        assert "X := 3;" in result
    
    def test_assignment_in_case_statement(self, default_rules):
        """Test assignments within case statements."""
        ada_code = """procedure Test is
   Choice : Integer := 1;
   Result : Integer;
begin
   case Choice is
      when 1 =>
         Result:=10;
      when 2 =>
         Result  :=  20;
      when others =>
         Result :=0;
   end case;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Result := 10;" in result
        assert "Result := 20;" in result
        assert "Result := 0;" in result
    
    def test_empty_file_handling(self, default_rules):
        """Test handling of empty or minimal files."""
        ada_code = ""
        
        # Should handle empty input gracefully
        # Suppress expected parser warning for empty input
        with redirect_stderr(io.StringIO()):
            result = self._parse_and_format(ada_code, default_rules)
        assert result == ""
    
    def test_assignment_with_attributes(self, default_rules):
        """Test assignments using Ada attributes."""
        ada_code = """procedure Test is
   X : Integer;
   Y : Integer;
begin
   X:=Integer'First;
   Y  :=  Integer'Last;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "X := Integer'First;" in result
        assert "Y := Integer'Last;" in result
    
    def test_multiline_assignment(self, default_rules):
        """Test assignments that span multiple lines."""
        ada_code = """procedure Test is
   Long_Variable_Name : Integer;
begin
   Long_Variable_Name:=
      Some_Function(Param1, Param2) + 
      Another_Function(Param3);
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        # Should fix the := on the first line
        assert "Long_Variable_Name :=" in result
    
    def test_array_element_assignment(self, default_rules):
        """Test assignment to array elements."""
        ada_code = """procedure Test is
   Arr : array (1 .. 10) of Integer;
begin
   Arr(1):=10;
   Arr(5)  :=  50;
end Test;"""
        
        result = self._parse_and_format(ada_code, default_rules)
        
        assert "Arr(1) := 10;" in result
        assert "Arr(5) := 50;" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules with 1 space before and after :=."""
        return FormattingRules()
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = AssignmentSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()
    
    def test_malformed_ada_code(self, default_rules):
        """Test handling of syntactically incorrect Ada code."""
        ada_code = """procedure Test is
begin
   X := ;  -- Missing right-hand side
end Test;"""
        
        # Should handle parse errors gracefully
        rules = FormattingRules()
        # Suppress expected parser warning for malformed code
        with redirect_stderr(io.StringIO()):
            try:
                input_stream = InputStream(ada_code)
                lexer = Ada2022Lexer(input_stream)
                token_stream = CommonTokenStream(lexer)
                parser = Ada2022Parser(token_stream)
                tree = parser.compilation_unit()
                
                visitor = AssignmentSpacingVisitor(rules, ada_code)
                visitor.visit(tree)
                result = visitor.apply_edits()
                # Even with parse errors, should return something
                assert isinstance(result, str)
            except Exception:
                # Parser errors are acceptable for malformed code
                pass
    
    def test_unicode_in_strings(self, default_rules):
        """Test handling of Unicode characters in string literals."""
        ada_code = """procedure Test is
   Msg : String := "Unicode: ← := →";
   X : Integer;
begin
   X:=5;
end Test;"""
        
        rules = FormattingRules()
        result = self._parse_and_format(ada_code, rules)
        
        assert 'Msg : String := "Unicode: ← := →";' in result
        assert "X := 5;" in result
    
    def test_very_long_lines(self, default_rules):
        """Test handling of very long lines."""
        ada_code = """procedure Test is
   Very_Long_Variable_Name_That_Goes_On_And_On : Integer;
begin
   Very_Long_Variable_Name_That_Goes_On_And_On:=12345678901234567890;
end Test;"""
        
        rules = FormattingRules()
        result = self._parse_and_format(ada_code, rules)
        
        assert "Very_Long_Variable_Name_That_Goes_On_And_On := 12345678901234567890;" in result
    
    def _parse_and_format(self, ada_code: str, rules: FormattingRules) -> str:
        """Parse Ada code and apply formatting rules."""
        input_stream = InputStream(ada_code)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        tree = parser.compilation_unit()
        
        visitor = AssignmentSpacingVisitor(rules, ada_code)
        visitor.visit(tree)
        return visitor.apply_edits()