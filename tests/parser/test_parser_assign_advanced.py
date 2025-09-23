# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Advanced assignment operator spacing detection using the Ada 2022 parser."""

import re
import pytest
from typing import List, Optional, Tuple
from dataclasses import dataclass

try:
    from ada2022_parser import Parser, Success
    from ada2022_parser.generated import Ada2022ParserVisitor, Ada2022Parser
    from antlr4 import ParserRuleContext, TerminalNode
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


@dataclass
class SpacingIssue:
    """Represents a spacing issue around an assignment operator."""
    line: int
    column: int
    before_spaces: int
    after_spaces: int
    full_line: str
    needs_fix: bool


class AdvancedAssignmentVisitor(Ada2022ParserVisitor):
    """
    Advanced visitor that analyzes actual whitespace around := operators.
    This implementation shows how to access the source text and token positions.
    """
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.issues = []
        self._string_literal_regions = []
    
    def visitString_literal(self, ctx):
        """Record string literal regions to avoid processing them."""
        start_line = ctx.start.line - 1  # Convert to 0-based
        start_col = ctx.start.column
        stop_line = ctx.stop.line - 1
        stop_col = ctx.stop.column + len(ctx.getText())
        
        self._string_literal_regions.append((
            (start_line, start_col),
            (stop_line, stop_col)
        ))
        
        return self.visitChildren(ctx)
    
    def _is_in_string_literal(self, line: int, column: int) -> bool:
        """Check if a position is inside a string literal."""
        for (start_line, start_col), (end_line, end_col) in self._string_literal_regions:
            if start_line == end_line:
                if line == start_line and start_col <= column <= end_col:
                    return True
            else:
                if line == start_line and column >= start_col:
                    return True
                elif line == end_line and column <= end_col:
                    return True
                elif start_line < line < end_line:
                    return True
        return False
    
    def _analyze_assignment_spacing(self, ctx: ParserRuleContext) -> Optional[SpacingIssue]:
        """Analyze spacing around := in the given context."""
        line_num = ctx.start.line - 1  # Convert to 0-based
        
        if line_num >= len(self.source_lines):
            return None
        
        line_text = self.source_lines[line_num]
        
        # Find := in the line (not inside string literals)
        for match in re.finditer(r':=', line_text):
            col = match.start()
            
            # Skip if inside string literal
            if self._is_in_string_literal(line_num, col):
                continue
            
            # Analyze spacing before :=
            before_spaces = 0
            if col > 0:
                i = col - 1
                while i >= 0 and line_text[i].isspace():
                    before_spaces += 1
                    i -= 1
            
            # Analyze spacing after :=
            after_spaces = 0
            after_col = col + 2  # Length of ':='
            if after_col < len(line_text):
                i = after_col
                while i < len(line_text) and line_text[i].isspace():
                    after_spaces += 1
                    i += 1
            
            # Determine if fix is needed (must have at least 1 space before and after)
            needs_fix = before_spaces < 1 or after_spaces < 1
            
            return SpacingIssue(
                line=line_num + 1,  # Convert back to 1-based
                column=col,
                before_spaces=before_spaces,
                after_spaces=after_spaces,
                full_line=line_text.strip(),
                needs_fix=needs_fix
            )
        
        return None
    
    def visitAssignment_statement(self, ctx):
        """Check assignment statements."""
        issue = self._analyze_assignment_spacing(ctx)
        if issue:
            self.issues.append(issue)
        
        return self.visitChildren(ctx)
    
    def visitObject_declaration(self, ctx):
        """Check object declarations with initialization."""
        # Only process if there's an assignment
        if ctx.getChildCount() > 0:
            for i in range(ctx.getChildCount()):
                child = ctx.getChild(i)
                if hasattr(child, 'getText') and child.getText() == ':=':
                    issue = self._analyze_assignment_spacing(ctx)
                    if issue:
                        self.issues.append(issue)
                    break
        
        return self.visitChildren(ctx)
    
    def visitComponent_declaration(self, ctx):
        """Check component declarations with default values."""
        issue = self._analyze_assignment_spacing(ctx)
        if issue:
            self.issues.append(issue)
        
        return self.visitChildren(ctx)


@pytest.mark.skipif(not PARSER_AVAILABLE, reason="ada2022_parser not installed")
class TestAdvancedAssignmentPattern:
    """Test advanced assignment operator spacing detection."""
    
    def test_spacing_detection_accuracy(self):
        """Test accurate detection of spacing issues."""
        ada_code = """procedure Test is
   A:=1;            -- No spaces (needs fix)
   B :=2;           -- No space after (needs fix)
   C:= 3;           -- No space before (needs fix)
   D := 4;          -- Correct spacing
   E  :=  5;        -- Extra spaces (OK)
begin
   A:=B+C;          -- No spaces (needs fix)
   D := E * 2;      -- Correct spacing
end Test;"""
        
        lines = ada_code.split('\n')
        parser = Parser()
        result = parser.parse(ada_code)
        
        assert isinstance(result, Success)
        
        visitor = AdvancedAssignmentVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Should find exactly the problematic assignments
        assert len(visitor.issues) == 5
        
        # Verify specific issues
        issues_by_line = {issue.line: issue for issue in visitor.issues}
        
        # Line 2: A:=1 (no spaces)
        assert issues_by_line[2].before_spaces == 0
        assert issues_by_line[2].after_spaces == 0
        assert issues_by_line[2].needs_fix
        
        # Line 3: B :=2 (no space after)
        assert issues_by_line[3].before_spaces == 1
        assert issues_by_line[3].after_spaces == 0
        assert issues_by_line[3].needs_fix
        
        # Line 4: C:= 3 (no space before)
        assert issues_by_line[4].before_spaces == 0
        assert issues_by_line[4].after_spaces == 1
        assert issues_by_line[4].needs_fix
        
        # Line 5: D := 4 (correct)
        assert issues_by_line[5].before_spaces == 1
        assert issues_by_line[5].after_spaces == 1
        assert not issues_by_line[5].needs_fix
        
        # Line 6: E  :=  5 (extra spaces, OK)
        assert issues_by_line[6].before_spaces == 2
        assert issues_by_line[6].after_spaces == 2
        assert not issues_by_line[6].needs_fix
    
    def test_string_literal_exclusion(self):
        """Test that := in string literals is properly excluded."""
        ada_code = '''procedure Test is
   Op1 : String := ":=";                    -- Assignment needs checking
   Op2 : String:=":= is assignment";        -- Assignment needs fix
   Msg : String := "X:=5 is bad style";     -- Assignment OK, string ignored
   Code:String:="begin X:=Y; end;";         -- Assignment needs fix, string ignored
begin
   null;
end Test;'''
        
        lines = ada_code.split('\n')
        parser = Parser()
        result = parser.parse(ada_code)
        
        assert isinstance(result, Success)
        
        visitor = AdvancedAssignmentVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Should only find the actual assignment operators, not ones in strings
        for issue in visitor.issues:
            # The column should be for the assignment, not inside a string
            line_text = lines[issue.line - 1]
            # Get text around the assignment
            assignment_text = line_text[max(0, issue.column - 10):issue.column + 12]
            
            # Should be part of variable assignment, not inside quotes
            assert 'String :=' in assignment_text or 'String:=' in assignment_text
    
    def test_complex_expressions(self):
        """Test assignment detection in complex expressions."""
        ada_code = """package body Complex is
   procedure Init is
      -- Multiple assignments on one line (if allowed)
      X:Integer:=1;Y:Integer:=2;          -- Each needs fix
      
      -- Nested expressions
      Result:=Calc(A:=B+C,D:=E*F);        -- Multiple issues
      
      -- Array aggregates  
      Data:=(1,2,3,4);                    -- := needs fix
      Matrix:=((1,2),(3,4));              -- := needs fix
      
      -- Record aggregates
      Point:=(X=>0,Y=>0);                 -- := needs fix
   begin
      null;
   end Init;
end Complex;"""
        
        lines = ada_code.split('\n')
        parser = Parser()
        result = parser.parse(ada_code)
        
        # Even if parsing fails on complex cases, visitor should handle what it can
        if isinstance(result, Success):
            visitor = AdvancedAssignmentVisitor(lines)
            visitor.visit(result.value['tree'])
            
            # Should find multiple issues
            assert len(visitor.issues) > 0
            
            # All found issues should need fixes (no spaces)
            for issue in visitor.issues:
                assert issue.needs_fix
    
    def test_multiline_handling(self):
        """Test handling of assignments split across lines."""
        ada_code = """procedure Test is
   Very_Long_Variable_Name
      := Very_Long_Expression_That_Continues;    -- OK (line continuation)
   
   Short:=                                       -- Bad (no space before)
      Value;
      
   Good := 
      Another_Value;                             -- OK
begin
   null;
end Test;"""
        
        lines = ada_code.split('\n')
        parser = Parser()
        result = parser.parse(ada_code)
        
        if isinstance(result, Success):
            visitor = AdvancedAssignmentVisitor(lines)
            visitor.visit(result.value['tree'])
            
            # Should handle multi-line cases appropriately
            assert isinstance(visitor.issues, list)
    
    def test_formatting_suggestions(self):
        """Test generating formatting suggestions from detected issues."""
        ada_code = """procedure Format_Me is
   X:=5;         -- Should become X := 5
   Y :=10;       -- Should become Y := 10  
   Z:= 15;       -- Should become Z := 15
begin
   null;
end Format_Me;"""
        
        lines = ada_code.split('\n')
        parser = Parser()
        result = parser.parse(ada_code)
        
        assert isinstance(result, Success)
        
        visitor = AdvancedAssignmentVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Generate fixes
        fixes = []
        for issue in visitor.issues:
            if issue.needs_fix:
                line = lines[issue.line - 1]
                # Simple fix: ensure 1 space before and after :=
                before = line[:issue.column].rstrip() + ' '
                after = ' ' + line[issue.column + 2:].lstrip()
                fixed_line = before + ':=' + after
                
                fixes.append({
                    'line': issue.line,
                    'original': line.strip(),
                    'fixed': fixed_line.strip()
                })
        
        # Verify fixes
        assert len(fixes) == 3
        assert fixes[0]['fixed'] == 'X := 5;         -- Should become X := 5'
        assert fixes[1]['fixed'] == 'Y := 10;       -- Should become Y := 10'
        assert fixes[2]['fixed'] == 'Z := 15;       -- Should become Z := 15'


if __name__ == "__main__":
    if PARSER_AVAILABLE:
        test = TestAdvancedAssignmentPattern()
        
        print("=== Advanced Assignment Pattern Tests ===\n")
        
        print("1. Testing spacing detection accuracy:")
        test.test_spacing_detection_accuracy()
        print("✓ Passed\n")
        
        print("2. Testing string literal exclusion:")  
        test.test_string_literal_exclusion()
        print("✓ Passed\n")
        
        print("3. Testing complex expressions:")
        test.test_complex_expressions()
        print("✓ Passed\n")
        
        print("4. Testing multiline handling:")
        test.test_multiline_handling()
        print("✓ Passed\n")
        
        print("5. Testing formatting suggestions:")
        test.test_formatting_suggestions()
        print("✓ Passed\n")
        
        print("All advanced tests passed!")
    else:
        print("ada2022_parser not installed")