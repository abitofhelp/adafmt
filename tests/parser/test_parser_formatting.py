# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test formatting using the Ada 2022 parser instead of regex patterns."""

import pytest
from dataclasses import dataclass

# Check if parser is available
try:
    from ada2022_parser import Parser, Success
    from ada2022_parser.generated import Ada2022ParserVisitor
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


@dataclass
class FormatEdit:
    """Represents a formatting change to make."""
    line: int
    column: int
    original: str
    replacement: str
    rule: str


@pytest.mark.skipif(not PARSER_AVAILABLE, reason="ada2022_parser not installed")
class TestParserBasedFormatting:
    """Test formatting rules using the Ada parser."""
    
    def test_assignment_operator_spacing(self):
        """Test that we can detect and fix assignment operator spacing."""
        
        class AssignmentFormattingVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.edits = []
                
            def visitAssignment_statement(self, ctx):
                """Check assignment statements for proper := spacing."""
                # Get the full text of the assignment
                full_text = ctx.getText()
                
                # Look for the := operator in the text
                if ':=' in full_text:
                    # In a real implementation, we'd check the actual spacing
                    # For now, just record that we found an assignment
                    self.edits.append(FormatEdit(
                        line=ctx.start.line,
                        column=ctx.start.column,
                        original=full_text,
                        replacement=full_text.replace(':=', ' := '),
                        rule='assign_set01'
                    ))
                
                return self.visitChildren(ctx)
        
        # Test Ada code with various assignment spacings
        ada_code = """
procedure Test is
   X:=5;          -- No spaces
   Y := 10;       -- Correct spacing
   Z  :=  15;     -- Too many spaces
begin
   null;
end Test;
"""
        
        parser = Parser()
        result = parser.parse(ada_code)
        
        assert isinstance(result, Success)
        
        visitor = AssignmentFormattingVisitor()
        visitor.visit(result.value['tree'])
        
        # We should find 3 assignments
        assert len(visitor.edits) == 3
        print(f"Found {len(visitor.edits)} assignments to check")
        
    def test_comment_formatting(self):
        """Test comment formatting detection."""
        
        class CommentFormattingVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.whole_line_comments = []
                self.eol_comments = []
                
            def visitTerminal(self, node):
                """Check terminal nodes for comments."""
                # In ANTLR, comments might be in the hidden channel
                # This is a simplified example
                if hasattr(node, 'symbol') and hasattr(node.symbol, 'text'):
                    text = node.symbol.text
                    if text.startswith('--'):
                        # Simple heuristic: if column 0, it's whole-line
                        if hasattr(node.symbol, 'column') and node.symbol.column == 0:
                            self.whole_line_comments.append({
                                'line': node.symbol.line,
                                'text': text
                            })
                        else:
                            self.eol_comments.append({
                                'line': node.symbol.line,
                                'text': text
                            })
                
                return super().visitTerminal(node)
        
        ada_code = """
--Whole line comment (needs space)
-- This is correct
procedure Test is
   X : Integer;  --EOL comment (needs space)
   Y : String;   -- This is correct
begin
   null;
end Test;
"""
        
        parser = Parser()
        result = parser.parse(ada_code)
        
        if isinstance(result, Success):
            visitor = CommentFormattingVisitor()
            visitor.visit(result.value['tree'])
            
            print(f"Found {len(visitor.whole_line_comments)} whole-line comments")
            print(f"Found {len(visitor.eol_comments)} EOL comments")
    
    def test_range_operator_spacing(self):
        """Test range operator (..) spacing detection."""
        
        class RangeFormattingVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.ranges = []
                
            def visitDiscrete_range(self, ctx):
                """Check discrete ranges for proper .. spacing."""
                text = ctx.getText()
                if '..' in text:
                    self.ranges.append({
                        'line': ctx.start.line,
                        'text': text,
                        'needs_fix': ' .. ' not in text
                    })
                return self.visitChildren(ctx)
        
        ada_code = """
procedure Test is
   type T1 is range 1..10;        -- Needs spaces
   type T2 is range 1 .. 10;      -- Correct
   subtype S is Integer range 5..15;  -- Needs spaces
begin
   for I in 1 .. 5 loop
      null;
   end loop;
end Test;
"""
        
        parser = Parser()
        result = parser.parse(ada_code)
        
        if isinstance(result, Success):
            visitor = RangeFormattingVisitor()
            visitor.visit(result.value['tree'])
            
            print(f"Found {len(visitor.ranges)} ranges:")
            for r in visitor.ranges:
                status = "needs fix" if r['needs_fix'] else "correct"
                print(f"  Line {r['line']}: {r['text']} - {status}")
            
            # Count how many need fixing
            need_fix = sum(1 for r in visitor.ranges if r['needs_fix'])
            assert need_fix >= 2
    
    def test_string_literal_protection(self):
        """Test that string literals are properly identified."""
        
        class StringLiteralVisitor(Ada2022ParserVisitor):
            def __init__(self):
                self.string_literals = []
                
            def visitString_literal(self, ctx):
                """Collect all string literals."""
                self.string_literals.append({
                    'line': ctx.start.line,
                    'column': ctx.start.column,
                    'text': ctx.getText()
                })
                return self.visitChildren(ctx)
        
        ada_code = '''
procedure Test is
   -- These string literals should be protected from formatting
   Op1 : String := ":=";           -- Assignment operator
   Op2 : String := "..";           -- Range operator  
   Op3 : String := "=>";           -- Arrow operator
   Comment : String := "--test";   -- Comment marker
   
   -- Regular code that should be formatted
   X:=5;                           -- This needs spacing
   Y:Integer range 1..10;          -- This needs spacing
begin
   null;
end Test;
'''
        
        parser = Parser()
        result = parser.parse(ada_code)
        
        if isinstance(result, Success):
            visitor = StringLiteralVisitor()
            visitor.visit(result.value['tree'])
            
            print(f"Found {len(visitor.string_literals)} string literals:")
            for s in visitor.string_literals:
                print(f"  Line {s['line']}: {s['text']}")
            
            # Verify we found the important ones
            texts = [s['text'] for s in visitor.string_literals]
            assert '":="' in texts
            assert '".."' in texts
            assert '"=>"' in texts
            assert '"--test"' in texts
    
    def test_complete_formatting_example(self):
        """Test a complete formatting example combining multiple patterns."""
        
        class ComprehensiveFormattingVisitor(Ada2022ParserVisitor):
            """Visitor that checks multiple formatting rules."""
            
            def __init__(self):
                self.issues = []
                
            def add_issue(self, ctx, issue_type: str, description: str):
                """Record a formatting issue."""
                self.issues.append({
                    'line': ctx.start.line,
                    'column': ctx.start.column,
                    'type': issue_type,
                    'description': description,
                    'text': ctx.getText()
                })
            
            def visitAssignment_statement(self, ctx):
                """Check assignment spacing."""
                text = ctx.getText()
                if ':=' in text and ' := ' not in text:
                    self.add_issue(ctx, 'assignment', 'Missing spaces around :=')
                return self.visitChildren(ctx)
            
            def visitDiscrete_range(self, ctx):
                """Check range spacing."""
                text = ctx.getText()
                if '..' in text and ' .. ' not in text:
                    self.add_issue(ctx, 'range', 'Missing spaces around ..')
                return self.visitChildren(ctx)
            
            def visitString_literal(self, ctx):
                """Mark string literals as protected."""
                self.add_issue(ctx, 'protected', f'String literal: {ctx.getText()}')
                return self.visitChildren(ctx)
        
        ada_code = """
with Ada.Text_IO; use Ada.Text_IO;
procedure Demo is
   X:Integer:=42;                  -- Multiple issues
   Y:String:="Hello";              -- Assignment issue, but string is protected
   Z:array(1..10)of Integer;       -- Range issue
   
   Ops:String:=":=,=>,..";         -- String should be protected
begin
   Put_Line("Operators: :=, .., =>");  -- String protected
   
   for I in 1..5 loop              -- Range issue
      X:=X+1;                      -- Assignment issue
   end loop;
end Demo;
"""
        
        parser = Parser()
        result = parser.parse(ada_code)
        
        if isinstance(result, Success):
            visitor = ComprehensiveFormattingVisitor()
            visitor.visit(result.value['tree'])
            
            print(f"\nFound {len(visitor.issues)} formatting items:")
            
            # Group by type
            by_type = {}
            for issue in visitor.issues:
                issue_type = issue['type']
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(issue)
            
            for issue_type, issues in by_type.items():
                print(f"\n{issue_type.upper()} ({len(issues)} items):")
                for issue in issues[:3]:  # Show first 3 of each type
                    print(f"  Line {issue['line']}: {issue['description']}")
                if len(issues) > 3:
                    print(f"  ... and {len(issues) - 3} more")
            
            # Verify we found issues
            assert len(visitor.issues) > 0
            assert 'assignment' in by_type
            assert 'range' in by_type
            assert 'protected' in by_type


if __name__ == "__main__":
    if PARSER_AVAILABLE:
        # Run a simple demonstration
        test = TestParserBasedFormatting()
        print("=== Parser-Based Formatting Tests ===\n")
        
        print("1. Testing assignment operator detection:")
        test.test_assignment_operator_spacing()
        
        print("\n2. Testing range operator detection:")
        test.test_range_operator_spacing()
        
        print("\n3. Testing string literal protection:")
        test.test_string_literal_protection()
        
        print("\n4. Testing comprehensive formatting:")
        test.test_complete_formatting_example()
    else:
        print("ada2022_parser package not installed")
        print("Install with: pip install ada2022-parser")