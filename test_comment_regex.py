#!/usr/bin/env python3
"""Test the improved comment regex patterns."""

import re

# Define the patterns
WHOLE_LINE_FIX = re.compile(r'^(\s*)--(?:\s|(?=\S))(?!\s\S)(.*?)$', re.MULTILINE)
EOL_FIX = re.compile(r'^(.*\S)\s*--(?!\s)(.*?)$', re.MULTILINE)
PRESERVE_ART = re.compile(r'^\s*--\s*([+|\-=*#]{3,}|[+|]\s*[+\-|])', re.MULTILINE)

def test_patterns():
    """Test comment patterns with various inputs."""
    
    test_cases = [
        # (input, should_match_whole_line_fix, should_match_eol_fix, should_preserve)
        ("   --This has no space", True, False, False),
        ("   -- This has one space", True, False, False),  
        ("   --  This has two spaces", False, False, False),
        ("   --   This has three spaces", False, False, False),
        ("X := 1; --no space", False, True, False),
        ("X := 1; -- one space", False, False, False),
        ("X := 1; --  two spaces", False, False, False),
        ("   -- =========", False, False, True),
        ("   --  +-- Tree", False, False, True),
        ("   --  | +-- Child", False, False, True),
    ]
    
    print("Testing comment patterns:\n")
    
    for test_input, expect_whole, expect_eol, expect_preserve in test_cases:
        whole_match = bool(WHOLE_LINE_FIX.search(test_input))
        eol_match = bool(EOL_FIX.search(test_input))
        preserve_match = bool(PRESERVE_ART.search(test_input))
        
        print(f"Input: '{test_input}'")
        print(f"  Whole-line fix needed: {whole_match} (expected: {expect_whole})")
        print(f"  EOL fix needed: {eol_match} (expected: {expect_eol})")
        print(f"  Should preserve: {preserve_match} (expected: {expect_preserve})")
        
        # Show what the fix would be
        if whole_match:
            fixed = WHOLE_LINE_FIX.sub(r'\1--  \2', test_input)
            print(f"  Fixed to: '{fixed}'")
        elif eol_match:
            fixed = EOL_FIX.sub(r'\1 -- \2', test_input)
            print(f"  Fixed to: '{fixed}'")
            
        print()

if __name__ == "__main__":
    test_patterns()