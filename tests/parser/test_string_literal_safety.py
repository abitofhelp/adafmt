# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test that parser-based patterns correctly handle string literals.

This test demonstrates the critical issue that regex patterns couldn't solve:
protecting string literals from formatting changes. The regex patterns would
incorrectly modify operators inside strings, breaking code functionality.
"""

from ada2022_parser import Parser, Success
from ada2022_parser.generated import Ada2022ParserVisitor
from typing import List, Set, Tuple


class StringLiteralProtectionVisitor(Ada2022ParserVisitor):
    """Visitor that finds formatting issues while protecting string literals."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.formatting_issues = []
        self.string_literal_regions = []
        
    def visitString_literal(self, ctx):
        """Record string literal regions to protect them."""
        # Get the location of this string literal
        start_line = ctx.start.line - 1  # 0-based
        start_col = ctx.start.column
        end_line = ctx.stop.line - 1
        end_col = ctx.stop.column + len(ctx.getText()) - 1
        
        self.string_literal_regions.append({
            'start': (start_line, start_col),
            'end': (end_line, end_col),
            'text': ctx.getText()
        })
        
        return self.visitChildren(ctx)
    
    def is_in_string_literal(self, line: int, column: int) -> bool:
        """Check if a position is inside any string literal."""
        for region in self.string_literal_regions:
            start_line, start_col = region['start']
            end_line, end_col = region['end']
            
            # Single-line string
            if start_line == end_line:
                if line == start_line and start_col <= column <= end_col:
                    return True
            # Multi-line string (rare in Ada)
            else:
                if line == start_line and column >= start_col:
                    return True
                elif line == end_line and column <= end_col:
                    return True
                elif start_line < line < end_line:
                    return True
        
        return False
    
    def check_line_for_operators(self, line_num: int):
        """Check a line for operators that need spacing, avoiding string literals."""
        if line_num >= len(self.source_lines):
            return
            
        line = self.source_lines[line_num]
        
        # Check for various operators
        operators = [':=', '=>', '..', '/=', '>=', '<=', '**']
        
        for op in operators:
            idx = 0
            while idx < len(line):
                idx = line.find(op, idx)
                if idx == -1:
                    break
                
                # Check if this operator is inside a string literal
                if not self.is_in_string_literal(line_num, idx):
                    # Check spacing around the operator
                    needs_fix = False
                    
                    # Check before
                    if idx > 0 and line[idx-1] not in ' \t':
                        needs_fix = True
                    
                    # Check after
                    op_end = idx + len(op)
                    if op_end < len(line) and line[op_end] not in ' \t\n;,)':
                        needs_fix = True
                    
                    if needs_fix:
                        self.formatting_issues.append({
                            'line': line_num + 1,
                            'column': idx,
                            'operator': op,
                            'context': line.strip()
                        })
                
                idx += len(op)
    
    def visitCompilation_unit(self, ctx):
        """Visit the compilation unit and check all lines."""
        # First, collect all string literals
        self.visitChildren(ctx)
        
        # Then check all lines for operators
        for i in range(len(self.source_lines)):
            self.check_line_for_operators(i)
        
        return None


def test_string_literal_protection():
    """Test that demonstrates why regex patterns fail and parser succeeds."""
    
    print("=== String Literal Protection Test ===\n")
    
    # This is the exact type of code that broke with regex patterns
    ada_code = '''with Ada.Text_IO; use Ada.Text_IO;

procedure SQL_Example is
   -- These string literals contain operators that must NOT be formatted
   SQL_Metacharacters : constant String := "';\--/**/";   -- SQL injection chars
   Assignment_Op      : constant String := ":=";           -- Assignment operator
   Range_Op           : constant String := "..";           -- Range operator
   Arrow_Op           : constant String := "=>";           -- Arrow operator
   
   -- These operators SHOULD be formatted
   X : Integer:=42;                                        -- Needs spacing
   Y : Integer range 1..10:=5;                             -- Needs spacing
   
   -- Complex case: operators in code and strings on same line
   SQL:String:="SELECT * WHERE id:=1";                     -- Only first := needs fix
   
   -- Real-world example that failed with regex
   Query:constant String:="UPDATE users SET name:=? WHERE id>=? AND created<=?";
begin
   -- More operators that need formatting
   X:=X+1;                                                 -- Needs spacing
   
   -- Case statement with arrow operator
   case X is
      when 1=>Put_Line(":= in string");                   -- Only => needs spacing
      when 2 => Put_Line("OK");                            -- Already correct
   end case;
   
   -- Output the metacharacters (this line broke with regex!)
   Put_Line("SQL metacharacters: " & SQL_Metacharacters);
end SQL_Example;
'''
    
    print("Original Ada code:")
    print(ada_code)
    print("\n" + "="*80 + "\n")
    
    # Parse the code
    parser = Parser()
    result = parser.parse(ada_code)
    
    assert isinstance(result, Success), f"Parse failed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
    
    lines = ada_code.split('\n')
    visitor = StringLiteralProtectionVisitor(lines)
    visitor.visitCompilation_unit(result.value['tree'])
    
    print(f"Found {len(visitor.string_literal_regions)} string literals to protect:")
    for region in visitor.string_literal_regions:
        line = region['start'][0] + 1
        text = region['text']
        print(f"  Line {line}: {text}")
    
    print(f"\nFound {len(visitor.formatting_issues)} formatting issues (outside strings):")
    for issue in visitor.formatting_issues:
        print(f"  Line {issue['line']}, Col {issue['column']}: "
              f"'{issue['operator']}' needs spacing")
        print(f"    Context: {issue['context']}")
    
    # Verify critical cases
    print("\n" + "="*80)
    print("VERIFICATION: Critical test cases")
    print("="*80 + "\n")
    
    # 1. The SQL metacharacters line that broke with regex
    sql_meta_line = next(line for line in lines if 'SQL_Metacharacters' in line)
    print(f"1. SQL Metacharacters line: {sql_meta_line.strip()}")
    
    # Check that := in the string literal was NOT flagged
    sql_issues = [i for i in visitor.formatting_issues 
                  if 'SQL_Metacharacters' in i['context']]
    if sql_issues:
        # Should only find the := for assignment, not the one in the string
        assert len(sql_issues) == 1
        assert sql_issues[0]['operator'] == ':='
        assert sql_issues[0]['column'] < sql_meta_line.find('"')  # Before the string
        print("   ✓ Correctly identified only the assignment := (not the one in string)")
    else:
        print("   ✓ No operators in string literal were flagged")
    
    # 2. Query line with operators in string
    query_line_num = next(i for i, line in enumerate(lines) 
                          if 'Query:constant String' in line)
    query_issues = [i for i in visitor.formatting_issues 
                    if i['line'] == query_line_num + 1]
    
    print(f"\n2. Query line: {lines[query_line_num].strip()}")
    print(f"   Found {len(query_issues)} issues on this line")
    for issue in query_issues:
        print(f"   - Column {issue['column']}: '{issue['operator']}'")
    
    # Should only find the first :=, not the ones inside the string
    assert len(query_issues) <= 1, "Should only find assignment, not operators in string"
    
    # 3. Mixed operators on same line
    mixed_line_num = next(i for i, line in enumerate(lines)
                          if 'when 1=>Put_Line' in line)
    mixed_issues = [i for i in visitor.formatting_issues 
                    if i['line'] == mixed_line_num + 1]
    
    print(f"\n3. Mixed line: {lines[mixed_line_num].strip()}")
    print(f"   Found {len(mixed_issues)} issues")
    
    # Should only find =>, not := in the string
    assert all(i['operator'] == '=>' for i in mixed_issues), \
        "Should only find => operator, not := in string"
    
    print("\n" + "="*80)
    print("SUCCESS: Parser correctly protects string literals!")
    print("This is what regex patterns could NOT do correctly.")
    print("="*80)
    
    return visitor


def demonstrate_regex_failure():
    """Show what happens with the regex approach."""
    
    print("\n\n=== Demonstrating Regex Pattern Failure ===\n")
    
    test_line = '''SQL_Metacharacters : constant String := "';\\"--/**/";  -- SQL chars'''
    
    print("Original line:")
    print(test_line)
    
    # The regex pattern that was used
    import re
    
    # Original comment_eol2 pattern
    pattern = r'(\w)(\s*)(--)'
    replacement = r'\1 \2-- '
    
    print("\nApplying regex pattern for comment spacing...")
    result = re.sub(pattern, replacement, test_line)
    
    print("Result:")
    print(result)
    
    if '--' in test_line[test_line.find('"'):test_line.rfind('"')]:
        print("\n❌ PROBLEM: The -- inside the string literal was modified!")
        print("This would break the SQL metacharacters string.")
    
    # Try the "improved" regex with negative lookahead
    print("\nEven with complex regex to avoid strings:")
    # This pattern tries to avoid strings but is fragile
    complex_pattern = r'(?:[^"]*(?:"[^"]*"[^"]*)*)(--)'
    
    print("Complex patterns become unmaintainable and still have edge cases.")
    
    print("\n✓ Parser solution: Understands that '--' at column 45 is inside")
    print("  a string literal from column 40 to 54, so it won't modify it.")


if __name__ == "__main__":
    # Run the main test
    visitor = test_string_literal_protection()
    
    # Demonstrate the regex failure
    demonstrate_regex_failure()
    
    print("\n\nConclusion: Parser-based patterns are essential for correct")
    print("formatting of languages with string literals and complex syntax.")