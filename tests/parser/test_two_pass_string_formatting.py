# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Demonstrate proper two-pass formatting for long string literals.

Pass 1: Pre-ALS - Break long string literals properly
Pass 2: Post-ALS - Fix remaining spacing issues
"""

from ada2022_parser import Parser, Success
from ada2022_parser.generated import Ada2022ParserVisitor
from typing import List
import re


class StringLiteralAnalyzer(Ada2022ParserVisitor):
    """Analyze and collect information about string literals."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.string_literals = []
        
    def visitString_literal(self, ctx):
        """Collect string literal information."""
        line_num = ctx.start.line - 1
        start_col = ctx.start.column
        
        # Get the actual string content
        string_text = ctx.getText()
        
        # Find the full statement containing this string
        line = self.source_lines[line_num]
        
        # Find the beginning of the statement (look for := or :)
        stmt_start = line.rfind(':', 0, start_col)
        if stmt_start == -1:
            stmt_start = 0
            
        self.string_literals.append({
            'line': line_num,
            'column': start_col,
            'text': string_text,
            'full_line': line,
            'statement_start': stmt_start,
            'line_length': len(line.rstrip())
        })
        
        return self.visitChildren(ctx)


def break_long_string(string_lit: str, max_segment_length: int = 60) -> List[str]:
    """Break a string literal into properly formatted segments.
    
    Rules:
    1. Break at natural boundaries (spaces, punctuation)
    2. Preserve escape sequences
    3. Each segment properly quoted
    """
    # Remove surrounding quotes
    content = string_lit[1:-1]
    
    segments = []
    current = ""
    
    i = 0
    while i < len(content):
        # Handle escape sequences
        if content[i] == '\\' and i + 1 < len(content):
            # Keep escape sequences together
            current += content[i:i+2]
            i += 2
        else:
            current += content[i]
            i += 1
        
        # Check if we should break
        if len(current) >= max_segment_length:
            # Look for a good break point (space or punctuation)
            break_point = -1
            
            # Look backwards for a space
            for j in range(len(current) - 1, max(0, len(current) - 20), -1):
                if current[j] == ' ':
                    break_point = j + 1
                    break
                elif current[j] in '.,;:!?':
                    break_point = j + 1
                    break
            
            if break_point > 0:
                segments.append('"' + current[:break_point].rstrip() + '"')
                current = current[break_point:].lstrip()
            else:
                # No good break point, break at limit
                segments.append('"' + current[:max_segment_length] + '"')
                current = current[max_segment_length:]
    
    # Add remaining content
    if current:
        segments.append('"' + current + '"')
    
    return segments


def format_multiline_string(var_name: str, segments: List[str], indent: int) -> str:
    """Format a multi-line string assignment with proper indentation."""
    lines = []
    
    # First line with assignment
    lines.append(f"{' ' * indent}{var_name} :=")
    
    # String segments with continuation
    for i, segment in enumerate(segments):
        if i == 0:
            lines.append(f"{' ' * (indent + 3)}{segment}")
        else:
            lines.append(f"{' ' * (indent + 3)}& {segment}")
    
    # Add semicolon to last line
    lines[-1] += ";"
    
    return '\n'.join(lines)


def pass1_break_long_strings(ada_code: str, max_line_length: int = 120) -> str:
    """Pass 1: Pre-ALS - Break long string literals."""
    print("=== Pass 1: Pre-ALS String Breaking ===\n")
    
    parser = Parser()
    result = parser.parse(ada_code)
    
    if not isinstance(result, Success):
        print(f"Parse error: {result.error}")
        return ada_code
    
    lines = ada_code.split('\n')
    analyzer = StringLiteralAnalyzer(lines)
    analyzer.visit(result.value['tree'])
    
    # Process string literals that cause line length issues
    modifications = []
    
    for lit_info in analyzer.string_literals:
        if lit_info['line_length'] > max_line_length:
            print(f"Line {lit_info['line'] + 1} exceeds {max_line_length} chars ({lit_info['line_length']})")
            
            # Calculate how much we need to reduce
            excess = lit_info['line_length'] - max_line_length
            string_len = len(lit_info['text'])
            
            # If the string is the main cause
            if string_len > 60:  # Arbitrary threshold
                print(f"  String literal is {string_len} chars, breaking it...")
                
                # Extract variable name
                line = lit_info['full_line']
                match = re.search(r'(\w+)\s*:\s*(?:constant\s+)?String\s*:=', line)
                if match:
                    var_name = match.group(1)
                    indent = len(line) - len(line.lstrip())
                    
                    # Break the string
                    segments = break_long_string(lit_info['text'], max_segment_length=50)
                    
                    # Format the new assignment
                    new_assignment = format_multiline_string(var_name, segments, indent)
                    
                    print(f"  Broken into {len(segments)} segments")
                    
                    # Store modification
                    modifications.append({
                        'line': lit_info['line'],
                        'original': line,
                        'replacement': new_assignment
                    })
    
    # Apply modifications
    if modifications:
        # Sort by line number in reverse to avoid offset issues
        modifications.sort(key=lambda x: x['line'], reverse=True)
        
        for mod in modifications:
            lines[mod['line']] = mod['replacement']
        
        return '\n'.join(lines)
    
    return ada_code


def pass2_fix_operators(ada_code: str) -> str:
    """Pass 2: Post-ALS - Fix operator spacing."""
    print("\n=== Pass 2: Post-ALS Operator Spacing ===\n")
    
    parser = Parser()
    result = parser.parse(ada_code)
    
    if not isinstance(result, Success):
        print(f"Parse error: {result.error}")
        return ada_code
    
    lines = ada_code.split('\n')
    
    # Simple line-by-line fixes (parser ensures we're not in strings)
    analyzer = StringLiteralAnalyzer(lines)
    analyzer.visit(result.value['tree'])
    
    # Build a map of protected regions
    protected_regions = []
    for lit in analyzer.string_literals:
        line_num = lit['line']
        start_col = lit['column']
        end_col = start_col + len(lit['text'])
        protected_regions.append((line_num, start_col, end_col))
    
    # Fix operators
    fixed_lines = []
    fixes_made = 0
    
    for i, line in enumerate(lines):
        fixed_line = line
        
        # Check for operators that need spacing
        for op in [':=', '=>', '..', '>=', '<=', '/=']:
            idx = 0
            while True:
                idx = fixed_line.find(op, idx)
                if idx == -1:
                    break
                
                # Check if this position is protected
                protected = False
                for (prot_line, start_col, end_col) in protected_regions:
                    if prot_line == i and start_col <= idx < end_col:
                        protected = True
                        break
                
                if not protected:
                    # Check spacing
                    before_ok = idx == 0 or fixed_line[idx-1] == ' '
                    after_ok = idx + len(op) >= len(fixed_line) or fixed_line[idx + len(op)] == ' '
                    
                    if not before_ok or not after_ok:
                        # Fix spacing
                        before = fixed_line[:idx].rstrip() + ' '
                        after = ' ' + fixed_line[idx + len(op):].lstrip()
                        fixed_line = before + op + after
                        fixes_made += 1
                        print(f"  Fixed {op} on line {i + 1}")
                        # Adjust idx to continue search
                        idx = len(before) + len(op) + 1
                    else:
                        idx += len(op)
                else:
                    idx += len(op)
        
        fixed_lines.append(fixed_line)
    
    print(f"\nTotal fixes: {fixes_made}")
    return '\n'.join(fixed_lines)


def demonstrate_two_pass_formatting():
    """Demonstrate the complete two-pass formatting process."""
    
    print("=== Two-Pass String Literal Formatting Demo ===\n")
    print("Max line length: 120 characters")
    print("=" * 120)
    print()
    
    # Original code with issues
    original_code = '''package Example is
   -- This long string will be broken properly
   Error_Message : constant String := "This is a very long error message that exceeds the maximum line length limit and needs to be broken into multiple lines properly";
   
   -- This has operator spacing issues but fits on one line
   Short : String:="Short message";
   
   -- This has both issues
   Long_SQL : constant String:="SELECT user_id, user_name, email, registration_date FROM users WHERE status='active' AND created_date>=SYSDATE-30";
   
   -- Multiple operators need fixing
   Result : Integer:=Calculate(A=>1,B=>2,Range_Val=>1..100);
end Example;'''
    
    print("ORIGINAL CODE:")
    print(original_code)
    print("\n" + "=" * 120 + "\n")
    
    # Pass 1: Break long strings
    pass1_result = pass1_break_long_strings(original_code, max_line_length=120)
    
    print("\nAFTER PASS 1 (Long strings broken):")
    print(pass1_result)
    print("\n" + "=" * 120 + "\n")
    
    # Simulate ALS formatting (it would format structure but not fix our operators)
    # For demo purposes, we'll just pass through
    als_result = pass1_result
    
    # Pass 2: Fix operators
    final_result = pass2_fix_operators(als_result)
    
    print("\nFINAL RESULT (After Pass 2):")
    print(final_result)
    
    # Verify no lines exceed limit
    print("\n" + "=" * 120)
    print("VERIFICATION:")
    for i, line in enumerate(final_result.split('\n')):
        length = len(line.rstrip())
        if length > 120:
            print(f"  Line {i + 1}: {length} chars (EXCEEDS LIMIT)")
        else:
            print(f"  Line {i + 1}: {length} chars (OK)")


if __name__ == "__main__":
    demonstrate_two_pass_formatting()
    
    print("\n\nSUMMARY:")
    print("1. Pass 1 (Pre-ALS): Break long string literals using Ada concatenation")
    print("2. ALS: Format code structure (indentation, etc.)")
    print("3. Pass 2 (Post-ALS): Fix operator spacing outside string literals")
    print("\nResult: Properly formatted code that respects line length limits!")