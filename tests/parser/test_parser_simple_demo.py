# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Simple demonstration of parser-based pattern detection."""

from ada2022_parser import Parser, Success


def demo_assignment_detection():
    """Demonstrate assignment operator detection."""
    print("=== Assignment Operator Detection Demo ===\n")
    
    # Code that might come from ALS with some remaining issues
    ada_code = """procedure Demo is
   X : Integer := 5;      -- Correct
   Y : Integer:=10;       -- Missing space before :=
begin
   X := X + 1;            -- Correct
   Y:=Y+1;                -- Missing spaces
end Demo;
"""
    
    print("Ada Code:")
    print(ada_code)
    
    parser = Parser()
    result = parser.parse(ada_code)
    
    if isinstance(result, Success):
        print("\n✓ Parsing successful!")
        
        # Simple line-by-line analysis
        lines = ada_code.split('\n')
        print("\nChecking for assignment spacing issues:")
        
        for i, line in enumerate(lines, 1):
            if ':=' in line:
                # Find := position
                idx = line.find(':=')
                
                # Check character before and after
                before_ok = idx == 0 or line[idx-1] == ' '
                after_ok = idx+2 >= len(line) or line[idx+2] == ' ' or line[idx+2] in ';,'
                
                if not before_ok or not after_ok:
                    print(f"  Line {i}: NEEDS FIX - {line.strip()}")
                    if not before_ok:
                        print("    → Missing space before :=")
                    if not after_ok:
                        print("    → Missing space after :=")
                else:
                    print(f"  Line {i}: OK - {line.strip()}")
    else:
        print(f"\n✗ Parsing failed: {result.error}")


def demo_comment_detection():
    """Demonstrate comment spacing detection."""
    print("\n\n=== Comment Spacing Detection Demo ===\n")
    
    ada_code = """-- This comment is OK
--This comment needs space
procedure Test is
   X : Integer;  -- This is OK  
   Y : String;   --Needs space
begin
   null; -- OK
   null; --Bad
end Test;
"""
    
    print("Ada Code:")
    print(ada_code)
    
    lines = ada_code.split('\n')
    print("\nChecking for comment spacing issues:")
    
    for i, line in enumerate(lines, 1):
        if '--' in line:
            idx = line.find('--')
            
            # Skip separator lines (---)
            if idx + 2 < len(line) and line[idx+2] == '-':
                continue
            
            # Check spacing after --
            if idx + 2 < len(line) and line[idx+2] not in (' ', '\n', '\r', ''):
                print(f"  Line {i}: NEEDS FIX - {line.strip()}")
                print("    → Missing space after --")
            else:
                print(f"  Line {i}: OK - {line.strip()}")


def demo_range_detection():
    """Demonstrate range operator detection."""
    print("\n\n=== Range Operator Detection Demo ===\n")
    
    ada_code = """package Ranges is
   type T1 is range 1 .. 10;    -- OK
   type T2 is range 1..10;      -- Needs spaces
   
   A : array (1 .. 5) of Integer;
   B : array (1..5) of Integer;  -- Needs spaces
end Ranges;
"""
    
    print("Ada Code:")
    print(ada_code)
    
    lines = ada_code.split('\n')
    print("\nChecking for range operator spacing issues:")
    
    for i, line in enumerate(lines, 1):
        if '..' in line:
            # Simple check: should have spaces around ..
            if ' .. ' in line:
                print(f"  Line {i}: OK - {line.strip()}")
            else:
                print(f"  Line {i}: NEEDS FIX - {line.strip()}")
                print("    → Missing spaces around ..")


def demo_arrow_detection():
    """Demonstrate arrow operator detection."""
    print("\n\n=== Arrow Operator Detection Demo ===\n")
    
    ada_code = """procedure Test is
begin
   case X is
      when 1 => null;       -- OK
      when 2=> null;        -- Missing space before =>
      when 3 =>null;        -- Missing space after =>
      when 4=>null;         -- Missing both spaces
   end case;
end Test;
"""
    
    print("Ada Code:")
    print(ada_code)
    
    lines = ada_code.split('\n')
    print("\nChecking for arrow operator spacing issues:")
    
    for i, line in enumerate(lines, 1):
        if '=>' in line:
            idx = line.find('=>')
            
            # Check spacing
            before_ok = idx == 0 or line[idx-1] == ' '
            after_ok = idx+2 >= len(line) or line[idx+2] == ' '
            
            if not before_ok or not after_ok:
                print(f"  Line {i}: NEEDS FIX - {line.strip()}")
                if not before_ok:
                    print("    → Missing space before =>")
                if not after_ok:
                    print("    → Missing space after =>")
            else:
                print(f"  Line {i}: OK - {line.strip()}")


if __name__ == "__main__":
    demo_assignment_detection()
    demo_comment_detection()
    demo_range_detection()
    demo_arrow_detection()
    
    print("\n\nThis demonstrates how parser-based patterns would detect")
    print("formatting issues in post-ALS code that still need fixing.")