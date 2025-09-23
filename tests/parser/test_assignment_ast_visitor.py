#!/usr/bin/env python3
"""Test the AST visitor-based assignment spacing rule."""

import pytest
from pathlib import Path
import sys
import os

# Add src to path so we can import adafmt modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ada2022_parser import Ada2022Lexer, Ada2022Parser
from antlr4 import CommonTokenStream, InputStream

from adafmt.formatting_rules_model import FormattingRules
from adafmt.ast_visitors import AssignmentSpacingVisitor


class TestAssignmentASTVisitor:
    """Test assignment spacing with AST visitor approach."""
    
    def parse_ada_code(self, source: str):
        """Parse Ada source code and return the parse tree."""
        input_stream = InputStream(source)
        lexer = Ada2022Lexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = Ada2022Parser(token_stream)
        return parser.compilation_unit()  # Top-level rule
    
    def apply_assignment_spacing(self, source: str, rules: FormattingRules) -> str:
        """Apply assignment spacing rule using AST visitor."""
        # Parse the source
        tree = self.parse_ada_code(source)
        
        # Create and run visitor
        source_lines = source.split('\n')
        visitor = AssignmentSpacingVisitor(rules, source_lines)
        visitor.visit(tree)
        
        # Apply edits and return result
        result_lines = visitor.apply_edits()
        return '\n'.join(result_lines)
    
    def test_basic_assignment_spacing(self):
        """Test basic assignment operator spacing with default rules."""
        # Load default rules (spaces_before=1, spaces_after=1)
        rules = FormattingRules()
        
        test_cases = [
            # Input -> Expected output
            ("X:=5;", "X := 5;"),
            ("Y:=10;", "Y := 10;"),
            ("Result:=Func();", "Result := Func();"),
            
            # Already correct - no change
            ("X := 5;", "X := 5;"),
            ("Y := 10;", "Y := 10;"),
            
            # Multiple assignments on different lines
            ("X:=5;\nY:=10;", "X := 5;\nY := 10;"),
        ]
        
        for input_code, expected in test_cases:
            # Need a minimal compilable Ada unit
            ada_source = f"""procedure Test is
begin
   {input_code}
end Test;"""
            
            expected_ada = f"""procedure Test is
begin
   {expected}
end Test;"""
            
            result = self.apply_assignment_spacing(ada_source, rules)
            assert result == expected_ada, f"Input: {input_code!r}, Expected: {expected!r}, Got: {result!r}"
            print(f"✓ {input_code!r} -> {expected!r}")
    
    def test_string_literal_protection(self):
        """Test that := inside string literals is NOT modified."""
        rules = FormattingRules()
        
        # := inside string should be protected
        ada_source = """procedure Test is
   Op : String := ":=";
   X:=5;
begin
   null;
end Test;"""
        
        expected = """procedure Test is
   Op : String := ":=";
   X := 5;
begin
   null;
end Test;"""
        
        result = self.apply_assignment_spacing(ada_source, rules)
        assert result == expected
        print("✓ String literal protection works!")
    
    def test_custom_spacing_configuration(self):
        """Test custom spacing parameters from JSON config."""
        # Create custom rules with 2 spaces before, 3 spaces after
        rules = FormattingRules()
        rules.spacing.assignment.parameters.spaces_before = 2
        rules.spacing.assignment.parameters.spaces_after = 3
        
        ada_source = """procedure Test is
begin
   X:=5;
end Test;"""
        
        expected = """procedure Test is
begin
   X  :=   5;
end Test;"""
        
        result = self.apply_assignment_spacing(ada_source, rules)
        assert result == expected
        print("✓ Custom spacing configuration works!")
    
    def test_disabled_rule(self):
        """Test that disabled rules don't apply."""
        rules = FormattingRules()
        rules.spacing.assignment.enabled = False
        
        ada_source = """procedure Test is
begin
   X:=5;
end Test;"""
        
        # Should not change when rule is disabled
        result = self.apply_assignment_spacing(ada_source, ada_source)
        assert result == ada_source
        print("✓ Disabled rule check works!")


if __name__ == "__main__":
    test = TestAssignmentASTVisitor()
    test.test_basic_assignment_spacing()
    test.test_string_literal_protection()
    test.test_custom_spacing_configuration()
    test.test_disabled_rule()
    print("\n✅ All AST visitor tests passed!")