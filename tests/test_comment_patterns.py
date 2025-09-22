#!/usr/bin/env python3
"""Test suite for the updated comment patterns in adafmt."""

import re
import json

# Test cases for comment patterns
# Format: (input, expected_output, description)
COMMENT_TEST_CASES = [
    # Whole-line comments that SHOULD be fixed (0-1 spaces)
    ("--This has no space", "--  This has no space", "Fix no space after --"),
    ("-- This has one space", "--  This has one space", "Fix one space to two"),
    ("   --No space indented", "   --  No space indented", "Fix indented no space"),
    ("   -- One space indented", "   --  One space indented", "Fix indented one space"),
    
    # Whole-line comments that should NOT change (2+ spaces)
    ("--  This has two spaces", "--  This has two spaces", "Preserve two spaces"),
    ("--   This has three spaces", "--   This has three spaces", "Preserve three spaces"),
    ("--    Four spaces", "--    Four spaces", "Preserve four spaces"),
    
    # End-of-line comments that SHOULD be fixed (no space after --)
    ("X : Integer := 1; --no space", "X : Integer := 1; -- no space", "Fix EOL no space"),
    ("Y : constant := 42;--comment", "Y : constant := 42; -- comment", "Fix EOL no space with no space before"),
    
    # End-of-line comments that should NOT change (already have space)
    ("X : Integer := 1; -- one space", "X : Integer := 1; -- one space", "Preserve EOL one space"),
    ("Y : Integer := 2; --  two spaces", "Y : Integer := 2; --  two spaces", "Preserve EOL two spaces"),
    ("Z : Integer := 3; --   three", "Z : Integer := 3; --   three", "Preserve EOL three spaces"),
    
    # Separator lines that SHOULD be fixed
    ("-- =========", "--  =========", "Fix separator with one space"),
    ("--=========", "--  =========", "Fix separator with no space"),
    ("   -- ------", "   --  ------", "Fix indented separator"),
    
    # ASCII art that should NOT be modified by any pattern
    ("--  +-- Root", "--  +-- Root", "Preserve ASCII tree"),
    ("--  | +-- Child", "--  | +-- Child", "Preserve ASCII tree child"),
    ("--  +-------+", "--  +-------+", "Preserve ASCII box"),
    
    # Empty comment lines
    ("--", "--", "Preserve empty comment"),
    ("-- ", "--  ", "Fix empty comment with one space"),
    
    # Comments in strings (should NOT be modified)
    ('Put_Line ("--This is in a string");', 'Put_Line ("--This is in a string");', "Ignore comments in strings"),
    ('Msg : String := "-- not a comment";', 'Msg : String := "-- not a comment";', "Ignore EOL in strings"),
]

def load_patterns(filename="adafmt_patterns.json"):
    """Load patterns from JSON file."""
    with open(filename, 'r') as f:
        patterns = json.load(f)
    return patterns

def apply_pattern(text, pattern):
    """Apply a single pattern to text."""
    flags = 0
    if 'flags' in pattern and 'MULTILINE' in pattern.get('flags', []):
        flags |= re.MULTILINE
    
    regex = re.compile(pattern['find'], flags)
    return regex.sub(pattern['replace'], text)

def test_comment_patterns():
    """Test the comment patterns against all test cases."""
    patterns = load_patterns()
    
    # Get only comment-related patterns
    comment_patterns = [p for p in patterns if 'comment' in p['category']]
    
    print(f"Testing {len(comment_patterns)} comment patterns:")
    for p in comment_patterns:
        print(f"  - {p['name']}: {p['title']}")
    print()
    
    # Test each case
    failures = 0
    for input_text, expected, description in COMMENT_TEST_CASES:
        result = input_text
        
        # Apply patterns in order (some patterns might need specific order)
        pattern_order = ['separator_lines', 'cmt_whole_01_v2', 'comment_eol1_v2']
        
        for pattern_name in pattern_order:
            pattern = next((p for p in comment_patterns if p['name'] == pattern_name), None)
            if pattern:
                result = apply_pattern(result, pattern)
        
        if result != expected:
            print(f"❌ FAIL: {description}")
            print(f"   Input:    '{input_text}'")
            print(f"   Expected: '{expected}'")
            print(f"   Got:      '{result}'")
            print()
            failures += 1
        else:
            print(f"✓ PASS: {description}")
    
    print(f"\nResults: {len(COMMENT_TEST_CASES) - failures} passed, {failures} failed")
    return failures == 0

def test_gnat_compliance():
    """Create an Ada file to test GNAT compliance."""
    test_content = """with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Patterns is
   --  Correct whole-line comment
   X : Integer := 1; -- Correct inline comment
   
   -- =======================================================
   --  Section header
   -- =======================================================
   
   --  ASCII art example:
   --  +-- Root
   --  |   +-- Child 1
   --  |   +-- Child 2
   
begin
   Put_Line ("Testing patterns");
end Test_Patterns;
"""
    
    with open("test_gnat_compliance.adb", "w") as f:
        f.write(test_content)
    
    print("\nCreated test_gnat_compliance.adb")
    print("Compile with: gcc -c -gnat2022 -gnatyy -gnatyM120 test_gnat_compliance.adb")

if __name__ == "__main__":
    print("Ada Comment Pattern Test Suite")
    print("=" * 50)
    
    # Run pattern tests
    if test_comment_patterns():
        print("\n✓ All pattern tests passed!")
    else:
        print("\n❌ Some pattern tests failed!")
    
    # Create GNAT test file
    test_gnat_compliance()