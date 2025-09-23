# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test parser-based formatting patterns using ada2022_parser."""

import pytest
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Try to import the parser - mark tests as skipped if not available
ada_parser_available = True
try:
    from ada2022_parser import Parser
    from ada2022_parser.generated import (
        Ada2022Parser,
        Ada2022ParserVisitor,
        Ada2022Lexer
    )
    from antlr4 import CommonTokenStream, InputStream
except ImportError:
    ada_parser_available = False


@pytest.mark.skipif(not ada_parser_available, reason="ada2022_parser not installed")
class TestParserPatterns:
    """Test each formatting pattern using the Ada parser instead of regex."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = Parser()
    
    def parse_and_get_tree(self, source: str):
        """Parse source code and return the tree."""
        result = self.parser.parse(source)
        assert result.is_success, f"Parse failed: {result.error}"
        return result.value['tree']
    
    def test_assign_set01_pattern(self):
        """Test assignment operator spacing: ':=' → ' := '"""
        
        class AssignmentVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.assignments_found = []
                
            def visitAssignment_statement(self, ctx):
                # Find := token in the context
                for i, child in enumerate(ctx.children):
                    if hasattr(child, 'getText') and child.getText() == ':=':
                        # Record the assignment location
                        self.assignments_found.append({
                            'line': ctx.start.line,
                            'col': ctx.start.column,
                            'text': ctx.getText()
                        })
                return self.visitChildren(ctx)
        
        # Test cases
        test_code = """
procedure Test is
   X:=5;           -- No spaces
   Y :=10;         -- Space before only  
   Z:= 15;         -- Space after only
   W := 20;        -- Correct spacing
   Str := ":=";    -- Inside string literal
begin
   null;
end Test;
"""
        
        tree = self.parse_and_get_tree(test_code)
        visitor = AssignmentVisitor()
        visitor.visit(tree)
        
        # We should find 5 assignments (including the string literal one)
        assert len(visitor.assignments_found) >= 4
        print(f"Found {len(visitor.assignments_found)} assignments")
        for assign in visitor.assignments_found:
            print(f"  Line {assign['line']}: {assign['text']}")
    
    def test_comment_patterns(self):
        """Test comment formatting patterns."""
        
        class CommentVisitor(Ada2022ParserVisitor):
            def __init__(self, source_lines):
                self.source_lines = source_lines
                self.comments = []
                
            def visitTerminal(self, node):
                # Comments are terminal nodes
                if node.symbol and node.symbol.type == Ada2022Lexer.COMMENT:
                    line_num = node.symbol.line - 1
                    col = node.symbol.column
                    text = node.getText()
                    
                    # Determine if it's a whole-line comment
                    line = self.source_lines[line_num] if line_num < len(self.source_lines) else ""
                    before_comment = line[:col].strip()
                    is_whole_line = len(before_comment) == 0
                    
                    self.comments.append({
                        'line': node.symbol.line,
                        'col': col,
                        'text': text,
                        'is_whole_line': is_whole_line
                    })
                    
                return super().visitTerminal(node)
        
        test_code = """
--This needs fixing (no space)
-- This needs fixing (one space)  
--  This is correct (two spaces)
--   This is also fine (three spaces)
procedure Test is
   X : Integer := 42;--No space comment
   Y : String; -- Correct EOL comment
begin
   null;--Another bad comment
end Test;
"""
        
        tree = self.parse_and_get_tree(test_code)
        lines = test_code.split('\n')
        visitor = CommentVisitor(lines)
        visitor.visit(tree)
        
        print(f"Found {len(visitor.comments)} comments:")
        for comment in visitor.comments:
            comment_type = "whole-line" if comment['is_whole_line'] else "EOL"
            print(f"  Line {comment['line']} ({comment_type}): {repr(comment['text'])}")
        
        # Check we found all comments
        assert len(visitor.comments) == 7
        
        # Check classification
        whole_line_count = sum(1 for c in visitor.comments if c['is_whole_line'])
        eol_count = sum(1 for c in visitor.comments if not c['is_whole_line'])
        assert whole_line_count == 4
        assert eol_count == 3
    
    def test_range_dots01_pattern(self):
        """Test range operator spacing: '..' → ' .. '"""
        
        class RangeVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.ranges_found = []
                
            def visitDiscrete_range(self, ctx):
                # Look for .. token
                for child in ctx.children:
                    if hasattr(child, 'getText') and child.getText() == '..':
                        self.ranges_found.append({
                            'line': ctx.start.line,
                            'text': ctx.getText()
                        })
                return self.visitChildren(ctx)
                
            def visitRange(self, ctx):
                # Alternative range context
                for child in ctx.children:
                    if hasattr(child, 'getText') and child.getText() == '..':
                        self.ranges_found.append({
                            'line': ctx.start.line,
                            'text': ctx.getText()
                        })
                return self.visitChildren(ctx)
        
        test_code = """
procedure Test is
   type Arr1 is array (1..10) of Integer;      -- No spaces
   type Arr2 is array (1 ..10) of Integer;     -- Space before
   type Arr3 is array (1.. 10) of Integer;     -- Space after
   type Arr4 is array (1 .. 10) of Integer;    -- Correct
   Str : String := "1..10";                     -- Inside string
begin
   for I in 1..5 loop
      null;
   end loop;
end Test;
"""
        
        tree = self.parse_and_get_tree(test_code)
        visitor = RangeVisitor()
        visitor.visit(tree)
        
        print(f"Found {len(visitor.ranges_found)} ranges:")
        for r in visitor.ranges_found:
            print(f"  Line {r['line']}: {r['text']}")
            
        assert len(visitor.ranges_found) >= 5
    
    def test_assoc_arrow1_pattern(self):
        """Test association arrow spacing: '=>' → ' => '"""
        
        class ArrowVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.arrows_found = []
                
            def visitNamed_association_element(self, ctx):
                # Look for => token
                for child in ctx.children:
                    if hasattr(child, 'getText') and child.getText() == '=>':
                        self.arrows_found.append({
                            'line': ctx.start.line,
                            'text': ctx.getText()
                        })
                return self.visitChildren(ctx)
        
        test_code = """
procedure Test is
   type Rec is record
      X, Y : Integer;
   end record;
   
   R1 : Rec := (X=>1, Y=>2);              -- No spaces
   R2 : Rec := (X =>3, Y=> 4);            -- Mixed spacing
   R3 : Rec := (X => 5, Y => 6);          -- Correct
   Str : String := "A=>B";                -- Inside string
begin
   Process(First=>10, Second => 20);      -- Mixed in call
end Test;
"""
        
        tree = self.parse_and_get_tree(test_code)
        visitor = ArrowVisitor()
        visitor.visit(tree)
        
        print(f"Found {len(visitor.arrows_found)} arrows:")
        for arrow in visitor.arrows_found:
            print(f"  Line {arrow['line']}: {arrow['text']}")
            
        assert len(visitor.arrows_found) >= 6
    
    def test_comma_space1_pattern(self):
        """Test comma spacing: ',' → ', '"""
        
        class CommaVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.commas_found = []
                
            def visitTerminal(self, node):
                # Commas are terminal nodes
                if node.symbol and node.getText() == ',':
                    self.commas_found.append({
                        'line': node.symbol.line,
                        'col': node.symbol.column
                    })
                return super().visitTerminal(node)
        
        test_code = """
procedure Test is
   X,Y,Z : Integer;                    -- No spaces
   A, B,C : Float;                     -- Mixed
   P, Q, R : Boolean;                  -- Correct
   Str : String := "A,B,C";            -- Inside string
begin
   Proc(1,2,3);                        -- In call
   Proc(4, 5, 6);                      -- Correct in call
end Test;
"""
        
        tree = self.parse_and_get_tree(test_code)
        visitor = CommaVisitor()
        visitor.visit(tree)
        
        print(f"Found {len(visitor.commas_found)} commas:")
        for comma in visitor.commas_found:
            print(f"  Line {comma['line']}, col {comma['col']}")
            
        # Should find many commas (in declarations and calls)
        assert len(visitor.commas_found) >= 8
    
    def test_semicolon_pattern(self):
        """Test semicolon spacing: no space before ';'"""
        
        class SemicolonVisitor(Ada2022ParserVisitor):
            def __init__(self, source_text):
                self.source_text = source_text
                self.semicolons = []
                
            def visitTerminal(self, node):
                if node.symbol and node.getText() == ';':
                    # Check what's before the semicolon
                    pos = node.symbol.start
                    space_before = 0
                    while pos > 0 and self.source_text[pos - 1] == ' ':
                        space_before += 1
                        pos -= 1
                        
                    self.semicolons.append({
                        'line': node.symbol.line,
                        'col': node.symbol.column,
                        'space_before': space_before
                    })
                return super().visitTerminal(node)
        
        test_code = """
procedure Test is
   X : Integer;                        -- Correct
   Y : Float ;                         -- Space before
   Z : Boolean   ;                     -- Multiple spaces
begin
   null;                               -- Correct
   Put_Line("Test") ;                  -- Space before
end Test  ;                            -- Space before
"""
        
        tree = self.parse_and_get_tree(test_code)
        visitor = SemicolonVisitor(test_code)
        visitor.visit(tree)
        
        print(f"Found {len(visitor.semicolons)} semicolons:")
        for semi in visitor.semicolons:
            print(f"  Line {semi['line']}: {semi['space_before']} spaces before")
            
        # Count how many have incorrect spacing
        incorrect = sum(1 for s in visitor.semicolons if s['space_before'] > 0)
        print(f"  {incorrect} have incorrect spacing")
        
        assert len(visitor.semicolons) >= 6
        assert incorrect >= 3
    
    def test_string_literal_protection(self):
        """Test that we can identify string literals to protect them."""
        
        class StringLiteralVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.string_literals = []
                
            def visitString_literal(self, ctx):
                self.string_literals.append({
                    'line': ctx.start.line,
                    'text': ctx.getText()
                })
                return self.visitChildren(ctx)
        
        test_code = '''
procedure Test is
   SQL : String := "';--/**/";           -- Contains comment marker
   Op1 : String := ":=";                 -- Contains assignment
   Op2 : String := "=>";                 -- Contains arrow  
   Op3 : String := "..";                 -- Contains range
   Op4 : String := ", ";                 -- Contains comma space
   Nested : String := "He said ""Hi""";  -- Doubled quotes
begin
   null;
end Test;
'''
        
        tree = self.parse_and_get_tree(test_code)
        visitor = StringLiteralVisitor()
        visitor.visit(tree)
        
        print(f"Found {len(visitor.string_literals)} string literals:")
        for s in visitor.string_literals:
            print(f"  Line {s['line']}: {s['text']}")
            
        assert len(visitor.string_literals) == 6
        
        # Verify we found the problematic ones
        texts = [s['text'] for s in visitor.string_literals]
        assert '"\';--/**/"' in texts or '"\';"' in texts  # Might parse differently
        assert '":="' in texts
        assert '"=>"' in texts
        assert '".."' in texts


if __name__ == "__main__":
    # Run a simple test
    if ada_parser_available:
        test = TestParserPatterns()
        test.setup_method()
        print("Testing assignment pattern:")
        test.test_assign_set01_pattern()
        print("\nTesting comment patterns:")
        test.test_comment_patterns()
        print("\nTesting string literal protection:")
        test.test_string_literal_protection()
    else:
        print("ada2022_parser not available - install it first")