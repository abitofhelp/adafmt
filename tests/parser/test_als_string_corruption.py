# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Demonstrate how ALS corrupts long string literals by breaking them incorrectly.

This is a CRITICAL BUG: ALS attempts to break long strings but doesn't properly
continue them with Ada's concatenation syntax, resulting in corrupted code.
"""

def demonstrate_als_string_corruption():
    """Show how ALS corrupts long string literals."""
    
    print("=== ALS String Literal Corruption Bug ===\n")
    
    # Example of what happens
    print("BEFORE ALS formatting (valid Ada code):")
    print("-" * 80)
    
    before = '''procedure Test is
   -- This is a very long string that exceeds the line length limit
   Error_Message : constant String := "This is a very long error message that exceeds the maximum line length and ALS will try to break it but will do so incorrectly";
begin
   null;
end Test;'''
    
    print(before)
    
    print("\n\nAFTER ALS formatting (CORRUPTED - not valid Ada!):")
    print("-" * 80)
    
    # This is what ALS might produce (based on your description)
    after_corrupted = '''procedure Test is
   -- This is a very long string that exceeds the line length limit
   Error_Message : constant String := "This is a very long error message that exceeds the maximum line 
length and ALS will try to break it but will do so incorrectly";
begin
   null;
end Test;'''
    
    print(after_corrupted)
    
    print("\n❌ CRITICAL PROBLEMS:")
    print("1. String literal broken across lines WITHOUT concatenation operator (&)")
    print("2. No closing quote on first line")
    print("3. No opening quote on continuation line")
    print("4. Continuation line not properly indented")
    print("5. Result is INVALID Ada code that won't compile!")
    
    print("\n\nWHAT ALS SHOULD HAVE DONE (Option 1 - Don't break):")
    print("-" * 80)
    
    correct1 = '''procedure Test is
   -- This is a very long string that exceeds the line length limit
   Error_Message : constant String := "This is a very long error message that exceeds the maximum line length and ALS will try to break it but will do so incorrectly";
begin
   null;
end Test;'''
    
    print(correct1)
    
    print("\n\nWHAT ALS SHOULD HAVE DONE (Option 2 - Proper concatenation):")
    print("-" * 80)
    
    correct2 = '''procedure Test is
   -- This is a very long string that exceeds the line length limit
   Error_Message : constant String := 
      "This is a very long error message that exceeds the maximum line " &
      "length and ALS will try to break it but will do so incorrectly";
begin
   null;
end Test;'''
    
    print(correct2)


def demonstrate_corruption_scenarios():
    """Show various scenarios where ALS string breaking causes corruption."""
    
    print("\n\n=== Various String Corruption Scenarios ===\n")
    
    scenarios = [
        {
            'name': 'SQL Query',
            'before': '''   Query : String := "SELECT * FROM users WHERE status = 'active' AND created_date > '2024-01-01' AND (role = 'admin' OR role = 'superuser')";''',
            'after_bad': '''   Query : String := "SELECT * FROM users WHERE status = 'active' AND created_date > '2024-01-01' 
AND (role = 'admin' OR role = 'superuser')";''',
            'problem': 'SQL query is broken, missing quotes and concatenation'
        },
        
        {
            'name': 'Path with Spaces',
            'before': '''   Path : String := "C:\\Program Files\\Very Long Application Name\\Even Longer Subdirectory Name\\Configuration Files\\app.config";''',
            'after_bad': '''   Path : String := "C:\\Program Files\\Very Long Application Name\\Even Longer Subdirectory 
Name\\Configuration Files\\app.config";''',
            'problem': 'File path is corrupted, backslashes and spaces cause issues'
        },
        
        {
            'name': 'JSON String',
            'before': '''   Json : String := "{\\"name\\": \\"Very Long Name\\", \\"description\\": \\"This is a very long description that will be broken incorrectly\\"}";''',
            'after_bad': '''   Json : String := "{\\"name\\": \\"Very Long Name\\", \\"description\\": \\"This is a very long 
description that will be broken incorrectly\\"}";''',
            'problem': 'JSON is corrupted, escape sequences might be broken'
        }
    ]
    
    for scenario in scenarios:
        print(f"{scenario['name']}:")
        print("BEFORE (valid):")
        print(scenario['before'])
        print("\nAFTER ALS (corrupted):")
        print(scenario['after_bad'])
        print(f"\nPROBLEM: {scenario['problem']}")
        print("-" * 80)
        print()


def demonstrate_parser_detection():
    """Show how parser-based detection can identify this issue."""
    
    print("\n=== Parser-Based Detection of String Corruption ===\n")
    
    # Corrupted code from ALS
    corrupted_code = '''procedure Test is
   Message : String := "This is a broken
string literal";
   Path : String := "C:\\Users\\Name\\Documents\\Very Long Path
\\That Got Broken";
begin
   null;
end Test;'''
    
    print("Parser-based analysis can detect:")
    print("1. Unterminated string literal on line 2")
    print("2. Unexpected string literal on line 3 (no assignment)")
    print("3. Unterminated string literal on line 4")
    print("4. Unexpected string continuation on line 5")
    print()
    print("The parser would fail, immediately revealing the corruption!")
    
    
def propose_adafmt_solution():
    """Propose how adafmt should handle this."""
    
    print("\n\n=== Proposed adafmt Solution ===\n")
    
    print("1. DETECTION:")
    print("   - Use parser to verify code is valid AFTER any formatting")
    print("   - Specifically check for unterminated string literals")
    print("   - Detect string literals that span multiple lines incorrectly")
    print()
    
    print("2. PREVENTION:")
    print("   - If ALS produces invalid code, REJECT the changes")
    print("   - Log the issue for debugging")
    print("   - Keep the original (valid) code")
    print()
    
    print("3. WARNING:")
    print("   - Warn user about long string literals")
    print("   - Suggest manual refactoring")
    print("   - Provide line numbers and context")
    print()
    
    print("Example adafmt output:")
    print("  ⚠️  WARNING: Line 15 contains a string literal that exceeds line length")
    print("  ⚠️  ALS formatting was skipped for this file to prevent corruption")
    print("  💡  Consider manually splitting long strings using concatenation (&)")


if __name__ == "__main__":
    demonstrate_als_string_corruption()
    demonstrate_corruption_scenarios()
    demonstrate_parser_detection()
    propose_adafmt_solution()
    
    print("\n" + "="*80)
    print("CONCLUSION: This is a critical bug in ALS that can corrupt valid Ada code.")
    print("Parser-based validation is ESSENTIAL to detect and prevent such corruption.")
    print("="*80)