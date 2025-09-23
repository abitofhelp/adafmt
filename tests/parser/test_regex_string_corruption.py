# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Demonstrate the exact regex issue that led to string literal corruption.

This test shows the actual bug we encountered where the comment_eol2 pattern
was modifying -- inside string literals, breaking valid Ada code.
"""

import re


def demonstrate_regex_corruption():
    """Show the exact corruption that happened with regex patterns."""
    
    print("=== Regex String Literal Corruption Demo ===\n")
    
    # The exact line that was corrupted in abohlib
    test_cases = [
        {
            'description': 'SQL metacharacters with embedded --',
            'original': '''   SQL_Metacharacters : constant String := "';\\--/**/";  -- SQL injection protection''',
            'pattern_name': 'comment_eol2',
            'pattern': r'^((?:(?:[^"\n]*"){2})*[^"\n]*?[^\s])(\s*)(--)(.*?)$',
            'replacement': r'\1 -- \4',
            'expected_corruption': '''   SQL_Metacharacters : constant String := "';\\ -- /**/";  -- SQL injection protection'''
        },
        {
            'description': 'Simple assignment with := in string',
            'original': '''   Msg : String := "Use := for assignment";  --This needs space''',
            'pattern_name': 'comment_eol2',  
            'pattern': r'^((?:(?:[^"\n]*"){2})*[^"\n]*?[^\s])(\s*)(--)(.*?)$',
            'replacement': r'\1 -- \4',
            'expected_fix': '''   Msg : String := "Use := for assignment";  -- This needs space'''
        },
        {
            'description': 'Multiple operators in string',
            'original': '''   Ops : String := ":= => .. --";--Need space''',
            'pattern_name': 'comment_eol2',
            'pattern': r'^((?:(?:[^"\n]*"){2})*[^"\n]*?[^\s])(\s*)(--)(.*?)$',
            'replacement': r'\1 -- \4',
            'expected_fix': '''   Ops : String := ":= => .. --"; -- Need space'''
        }
    ]
    
    for test in test_cases:
        print(f"{test['description']}:")
        print(f"Original:  {test['original']}")
        
        # Apply the regex pattern
        result = re.sub(test['pattern'], test['replacement'], test['original'], flags=re.MULTILINE)
        
        print(f"After fix: {result}")
        
        # Check if corruption occurred
        if 'expected_corruption' in test:
            if result == test['expected_corruption']:
                print("❌ CORRUPTION: The -- inside the string literal was modified!")
                print("   This breaks the string content!")
            else:
                print("✓ Pattern worked correctly (but this wasn't the case in practice)")
        elif 'expected_fix' in test:
            if result == test['expected_fix']:
                print("✓ Correctly fixed only the comment spacing")
            else:
                print("❌ Unexpected result")
        
        print("-" * 80)
        print()


def show_attempted_regex_fixes():
    """Show the various regex patterns we tried that all had issues."""
    
    print("\n=== Attempted Regex Solutions (All Had Problems) ===\n")
    
    original = '''   SQL : String := "SELECT --comment";  --Fix this'''
    
    attempts = [
        {
            'name': 'Simple pattern',
            'pattern': r'(\S)\s*--\s*(\S)',
            'replacement': r'\1 -- \2',
            'problem': 'Modifies -- inside strings'
        },
        {
            'name': 'Negative lookbehind',
            'pattern': r'(?<!")(\S)\s*--\s*(\S)',
            'replacement': r'\1 -- \2',
            'problem': 'Only checks immediate predecessor'
        },
        {
            'name': 'Complex quote matching',
            'pattern': r'^((?:(?:[^"\n]*"){2})*[^"\n]*?)(\S)\s*--\s*(\S)',
            'replacement': r'\1\2 -- \3',
            'problem': 'Fragile, hard to maintain, edge cases'
        }
    ]
    
    print(f"Original: {original}\n")
    
    for attempt in attempts:
        print(f"{attempt['name']}:")
        print(f"  Pattern: {attempt['pattern']}")
        
        try:
            result = re.sub(attempt['pattern'], attempt['replacement'], original)
            print(f"  Result:  {result}")
            print(f"  Problem: {attempt['problem']}")
        except Exception as e:
            print(f"  Error: {e}")
        print()


def show_parser_solution():
    """Show how the parser solves this cleanly."""
    
    print("\n=== Parser-Based Solution ===\n")
    
    print("With a parser, we can:")
    print("1. First pass: Identify all string literal regions")
    print("   - Line 1, columns 25-40: \"SELECT --comment\"")
    print()
    print("2. Second pass: Find -- operators")
    print("   - Line 1, column 33: -- (inside string, SKIP)")
    print("   - Line 1, column 45: -- (in comment, FIX)")
    print()
    print("3. Apply fixes only outside strings")
    print("   - Original: SQL : String := \"SELECT --comment\";  --Fix this")
    print("   - Fixed:    SQL : String := \"SELECT --comment\";  -- Fix this")
    print("              (only the comment -- was fixed)")
    print()
    print("Result: ✓ String literals are protected")
    print("        ✓ Comments are properly formatted")
    print("        ✓ No risk of corruption")


def show_real_world_impact():
    """Show the real-world impact of this bug."""
    
    print("\n\n=== Real-World Impact ===\n")
    
    print("In the abohlib repository, this bug caused:")
    print()
    print("1. BROKEN SQL STRINGS:")
    print('   Before: "\';\\--/**/"')
    print('   After:  "\';\\ -- /**/"')
    print("   Result: SQL injection protection string was corrupted")
    print()
    print("2. BROKEN REGULAR EXPRESSIONS:")
    print('   Before: "[a-z]--[A-Z]"')  
    print('   After:  "[a-z] -- [A-Z]"')
    print("   Result: Regex pattern changed, would match different strings")
    print()
    print("3. BROKEN COMMENT MARKERS IN DATA:")
    print('   Before: "data--more"')
    print('   After:  "data -- more"')
    print("   Result: Data format changed, parsers would fail")
    print()
    print("This demonstrates why regex-based formatting is fundamentally")
    print("unsafe for languages with string literals.")


if __name__ == "__main__":
    demonstrate_regex_corruption()
    show_attempted_regex_fixes()
    show_parser_solution()
    show_real_world_impact()
    
    print("\n" + "="*80)
    print("CONCLUSION: Regex patterns cannot safely format code with string literals.")
    print("A proper parser is required to understand context and avoid corruption.")
    print("="*80)