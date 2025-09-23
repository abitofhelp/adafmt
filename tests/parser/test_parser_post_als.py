# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test parser-based patterns on post-ALS formatted code."""

from typing import List
from dataclasses import dataclass

from ada2022_parser import Parser, Success
from ada2022_parser.generated import Ada2022ParserVisitor


@dataclass
class FormatIssue:
    """Represents a formatting issue found by the parser."""
    line: int
    column: int
    issue_type: str
    description: str
    current_text: str


class PostALSFormattingVisitor(Ada2022ParserVisitor):
    """Visitor to detect formatting issues that ALS doesn't fix."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.issues = []
    
    def visitAssignment_statement(self, ctx):
        """Check for assignment spacing issues."""
        line_num = ctx.start.line - 1
        if line_num < len(self.source_lines):
            line_text = self.source_lines[line_num]
            
            # Check for := without proper spacing
            if ':=' in line_text:
                # Find the position of :=
                col = line_text.find(':=')
                if col > 0:
                    # Check spacing before and after
                    before = line_text[col-1] if col > 0 else ' '
                    after = line_text[col+2] if col+2 < len(line_text) else ' '
                    
                    if before != ' ' or after != ' ':
                        self.issues.append(FormatIssue(
                            line=line_num + 1,
                            column=col,
                            issue_type='assignment_spacing',
                            description=f'Missing space {"before" if before != " " else "after"} :=',
                            current_text=line_text.strip()
                        ))
        
        return self.visitChildren(ctx)
    
    def visitObject_declaration(self, ctx):
        """Check for assignment spacing in object declarations."""
        line_num = ctx.start.line - 1
        if line_num < len(self.source_lines):
            line_text = self.source_lines[line_num]
            
            # Check for := without proper spacing
            if ':=' in line_text:
                col = line_text.find(':=')
                if col > 0:
                    # Check spacing before and after
                    before = line_text[col-1] if col > 0 else ' '
                    after = line_text[col+2] if col+2 < len(line_text) else ' '
                    
                    if before != ' ' or after != ' ':
                        self.issues.append(FormatIssue(
                            line=line_num + 1,
                            column=col,
                            issue_type='assignment_spacing',
                            description=f'Missing space {"before" if before != " " else "after"} :=',
                            current_text=line_text.strip()
                        ))
        
        return self.visitChildren(ctx)
    
    def visitDiscrete_range(self, ctx):
        """Check for range operator spacing issues."""
        text = ctx.getText()
        if '..' in text and ' .. ' not in text:
            self.issues.append(FormatIssue(
                line=ctx.start.line,
                column=ctx.start.column,
                issue_type='range_spacing',
                description='Missing spaces around ..',
                current_text=text
            ))
        
        return self.visitChildren(ctx)


class TestParserPostALS:
    """Test parser patterns on code that has already been formatted by ALS."""
    
    def test_assignment_spacing_post_als(self):
        """Test detection of assignment spacing issues after ALS formatting."""
        
        # This simulates code after ALS formatting but with some issues
        # that our patterns need to fix (e.g., ALS might not enforce all spacing)
        als_formatted_code = """with Ada.Text_IO; use Ada.Text_IO;

procedure Test is
   X : Integer := 5;         -- ALS formatted correctly
   Y : Integer:=10;          -- Simulate issue ALS didn't fix
   Z : constant Integer := 15;
begin
   X := X + 1;               -- ALS formatted correctly
   Y:=Y + 1;                 -- Simulate issue ALS didn't fix
   Put_Line (Integer'Image (X));
end Test;
"""
        
        parser = Parser()
        result = parser.parse(als_formatted_code)
        
        assert isinstance(result, Success)
        
        lines = als_formatted_code.split('\n')
        visitor = PostALSFormattingVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Should find the assignment spacing issues
        print(f"Found {len(visitor.issues)} issues:")
        for issue in visitor.issues:
            print(f"  Line {issue.line}: {issue.issue_type} - {issue.description}")
            print(f"    Text: {issue.current_text}")
        
        assert len(visitor.issues) == 2
        
        # Check specific issues
        assignment_issues = [i for i in visitor.issues if i.issue_type == 'assignment_spacing']
        assert len(assignment_issues) == 2
        
        # Line 5: Y : Integer:=10;
        issue1 = next(i for i in assignment_issues if i.line == 5)
        assert ':=10' in issue1.current_text
        
        # Line 9: Y:=Y + 1;
        issue2 = next(i for i in assignment_issues if i.line == 9)
        assert 'Y:=Y' in issue2.current_text
    
    def test_range_operator_post_als(self):
        """Test detection of range operator spacing issues."""
        
        # Simulate post-ALS code with range spacing issues
        als_formatted_code = """package Test_Ranges is
   type Index is range 1 .. 10;      -- Correct
   type Count is range 1..100;       -- Needs fix
   
   subtype Small is Index range 1 .. 5;
   subtype Large is Index range 6..10;  -- Needs fix
end Test_Ranges;
"""
        
        parser = Parser()
        result = parser.parse(als_formatted_code)
        
        assert isinstance(result, Success)
        
        lines = als_formatted_code.split('\n')
        visitor = PostALSFormattingVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Should find range spacing issues
        range_issues = [i for i in visitor.issues if i.issue_type == 'range_spacing']
        print(f"Found {len(range_issues)} range issues:")
        for issue in range_issues:
            print(f"  Line {issue.line}: {issue.description}")
            print(f"    Text: {issue.current_text}")
        
        assert len(range_issues) == 2
        
        # Check the issues found
        for issue in range_issues:
            assert '..' in issue.current_text
            assert ' .. ' not in issue.current_text
    
    def test_comment_spacing_post_als(self):
        """Test comment spacing detection after ALS formatting."""
        
        # ALS might format code but not always fix comment spacing
        als_formatted_code = """--  This is a properly formatted comment
--This needs a space after --
procedure Test is
   X : Integer := 0;  -- This is OK
   Y : Integer := 0;  --This needs space
begin
   null; -- OK comment
   null; --Need space here
end Test;
"""
        
        parser = Parser()
        result = parser.parse(als_formatted_code)
        
        # For comments, we might need to check them differently
        # as they might be in the hidden channel
        lines = als_formatted_code.split('\n')
        comment_issues = []
        
        for i, line in enumerate(lines):
            if '--' in line:
                idx = line.find('--')
                # Check spacing after --
                if idx + 2 < len(line) and line[idx + 2] not in (' ', '\n', '\r', ''):
                    # Skip if it's a separator line (---)
                    if idx + 3 < len(line) and line[idx + 2] == '-':
                        continue
                    
                    comment_issues.append({
                        'line': i + 1,
                        'text': line.strip(),
                        'type': 'whole_line' if idx == 0 else 'eol'
                    })
        
        # Should find comment spacing issues
        assert len(comment_issues) == 4
        assert comment_issues[0]['line'] == 2  # --This needs a space
        assert comment_issues[1]['line'] == 5  # --This needs space
        assert comment_issues[2]['line'] == 8  # --Need space here
    
    def test_no_issues_in_clean_code(self):
        """Test that properly formatted code reports no issues."""
        
        # Fully correct code (as ALS would format it)
        clean_code = """with Ada.Text_IO; use Ada.Text_IO;

procedure Clean is
   X : Integer := 42;
   Y : constant String := "Hello";
   Z : array (1 .. 10) of Integer;
begin
   X := X + 1;
   Put_Line (Y & " World");
   
   for I in Z'Range loop
      Z (I) := I * 2;
   end loop;
end Clean;
"""
        
        parser = Parser()
        result = parser.parse(clean_code)
        
        assert isinstance(result, Success)
        
        lines = clean_code.split('\n')
        visitor = PostALSFormattingVisitor(lines)
        visitor.visit(result.value['tree'])
        
        # Should find no issues in properly formatted code
        assert len(visitor.issues) == 0


if __name__ == "__main__":
    test = TestParserPostALS()
    
    print("=== Testing Post-ALS Formatting Detection ===\n")
    
    print("1. Testing assignment spacing issues:")
    test.test_assignment_spacing_post_als()
    print("✓ Found assignment spacing issues\n")
    
    print("2. Testing range operator spacing:")
    test.test_range_operator_post_als()
    print("✓ Found range spacing issues\n")
    
    print("3. Testing comment spacing:")
    test.test_comment_spacing_post_als()
    print("✓ Found comment spacing issues\n")
    
    print("4. Testing clean code:")
    test.test_no_issues_in_clean_code()
    print("✓ No issues in clean code\n")
    
    print("All tests passed!")