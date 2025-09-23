# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test handling of long string literals that exceed line length limits.

This demonstrates a fundamental limitation of ALS/GNATformat: they cannot
automatically break long string literals into multiple lines with concatenation.
"""

from ada2022_parser import Parser, Success
from ada2022_parser.generated import Ada2022ParserVisitor
from typing import List


class LongStringAnalyzer(Ada2022ParserVisitor):
    """Analyzes string literals that might exceed line length limits."""
    
    def __init__(self, source_lines: List[str], max_line_length: int = 120):
        self.source_lines = source_lines
        self.max_line_length = max_line_length
        self.long_strings = []
        
    def visitString_literal(self, ctx):
        """Check each string literal for length issues."""
        line_num = ctx.start.line - 1
        start_col = ctx.start.column
        
        # Get the full line containing this string
        if line_num < len(self.source_lines):
            line = self.source_lines[line_num]
            line_length = len(line.rstrip())
            
            # Get the string literal text
            string_text = ctx.getText()
            string_length = len(string_text)
            
            if line_length > self.max_line_length:
                self.long_strings.append({
                    'line': line_num + 1,
                    'column': start_col,
                    'string_text': string_text,
                    'string_length': string_length,
                    'line_length': line_length,
                    'excess': line_length - self.max_line_length,
                    'full_line': line.rstrip()
                })
        
        return self.visitChildren(ctx)


def demonstrate_long_string_problem():
    """Show the problem with long string literals."""
    
    print("=== Long String Literal Problem ===\n")
    print("Maximum line length: 120 characters")
    print("=" * 120 + " (marker)")
    print()
    
    ada_code = '''package Long_Strings is
   -- Example 1: Error message that's too long
   Error_Msg : constant String := "Invalid configuration: The specified file path exceeds the maximum allowed length of 255 characters. Please use a shorter path.";
   
   -- Example 2: SQL query that's too long  
   Query : constant String := "SELECT u.id, u.name, u.email, u.created_at, p.phone, a.street, a.city FROM users u LEFT JOIN profiles p ON u.id = p.user_id LEFT JOIN addresses a ON u.id = a.user_id WHERE u.active = true";
   
   -- Example 3: Long file path
   Config_Path : constant String := "/usr/local/share/application/config/deeply/nested/directories/with/very/long/names/that/exceed/reasonable/limits/config.xml";
   
   -- Example 4: Documentation string
   Help_Text : constant String := "Usage: command [options] arguments. This command performs various operations on the specified files. Use --help for more information about available options and their parameters.";
   
   -- Example 5: String that would need complex splitting
   Complex : constant String := "This string has embedded ""quotes"" and special\ncharacters\tthat make it hard to split automatically without breaking the content's meaning.";
end Long_Strings;
'''
    
    parser = Parser()
    result = parser.parse(ada_code)
    
    if isinstance(result, Success):
        lines = ada_code.split('\n')
        analyzer = LongStringAnalyzer(lines, max_line_length=120)
        analyzer.visit(result.value['tree'])
        
        print(f"Found {len(analyzer.long_strings)} string literals in lines exceeding {analyzer.max_line_length} chars:\n")
        
        for info in analyzer.long_strings:
            print(f"Line {info['line']} ({info['line_length']} chars, {info['excess']} over limit):")
            print(f"  {info['full_line'][:60]}...")
            print(f"  String literal: {info['string_text'][:50]}...")
            print(f"  String length: {info['string_length']} chars")
            print()


def demonstrate_manual_string_splitting():
    """Show how a developer would manually handle long strings."""
    
    print("\n=== Manual String Splitting Solutions ===\n")
    
    print("1. Using concatenation:")
    print('''   Error_Msg : constant String := 
      "Invalid configuration: The specified file path " &
      "exceeds the maximum allowed length of 255 " &
      "characters. Please use a shorter path.";
''')
    
    print("2. Using multi-line strings (if supported):")
    print('''   Query : constant String := 
      "SELECT u.id, u.name, u.email, u.created_at, " &
      "p.phone, a.street, a.city " &
      "FROM users u " &
      "LEFT JOIN profiles p ON u.id = p.user_id " &
      "LEFT JOIN addresses a ON u.id = a.user_id " &
      "WHERE u.active = true";
''')
    
    print("3. Breaking at natural boundaries:")
    print('''   Config_Path : constant String := 
      "/usr/local/share/application/config/" &
      "deeply/nested/directories/with/very/" &
      "long/names/that/exceed/reasonable/" &
      "limits/config.xml";
''')


def demonstrate_why_tools_cant_split():
    """Explain why automatic string splitting is problematic."""
    
    print("\n=== Why Tools Can't Automatically Split Strings ===\n")
    
    print("1. SEMANTIC ISSUES:")
    print("   - Where to split? Natural word boundaries? Fixed length?")
    print("   - Escape sequences must not be broken (\\n, \\t, \"\", etc.)")
    print("   - Whitespace at split points affects the string content")
    print()
    
    print("2. CONTEXT AWARENESS:")
    print("   - Some contexts don't allow concatenation (e.g., aspect clauses)")
    print("   - Performance implications of runtime concatenation")
    print("   - Constant vs variable string expressions")
    print()
    
    print("3. EXAMPLES OF PROBLEMATIC CASES:")
    
    # Case 1: Escape sequences
    print("   Original: \"Line1\\nLine2\\nLine3\"")
    print("   Wrong:    \"Line1\\\" & \"nLine2\\nLine3\"  -- Breaks \\n!")
    print("   Right:    \"Line1\" & ASCII.LF & \"Line2\" & ASCII.LF & \"Line3\"")
    print()
    
    # Case 2: Trailing spaces
    print("   Original: \"Hello World\"")
    print("   Wrong:    \"Hello \" & \"World\"  -- Extra space!")
    print("   Right:    \"Hello\" & \" World\"")
    print()
    
    # Case 3: Quotes
    print("   Original: \"She said \"\"Hello\"\" to me\"")
    print("   Complex splitting required to handle embedded quotes")


def propose_solution():
    """Propose how adafmt could handle this."""
    
    print("\n=== Proposed Solution for adafmt ===\n")
    
    print("Since ALS/GNATformat can't split strings, adafmt could:")
    print()
    print("1. DETECT long string literals that cause line length violations")
    print("2. WARN the user about them (don't try to fix automatically)")
    print("3. OPTIONALLY provide suggestions for manual splitting")
    print("4. SKIP formatting rules that would push strings over the limit")
    print()
    
    print("Example warning:")
    print("  WARNING: Line 42 exceeds maximum length (142 chars)")
    print("  Cause: String literal is 98 characters")
    print("  Suggestion: Consider splitting this string using concatenation (&)")
    print()
    
    print("This maintains correctness while informing developers about issues.")


if __name__ == "__main__":
    demonstrate_long_string_problem()
    demonstrate_manual_string_splitting()
    demonstrate_why_tools_cant_split()
    propose_solution()