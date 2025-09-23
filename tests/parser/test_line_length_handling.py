# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Demonstrate handling of line length limits when applying spacing fixes."""

from ada2022_parser import Parser, Success
from typing import List, Tuple, Optional


def apply_spacing_fix(line: str, max_length: int = 120) -> Tuple[str, bool, Optional[str]]:
    """
    Apply spacing fixes to a line, respecting maximum line length.
    
    Returns:
        Tuple of (fixed_line, was_fixed, warning_message)
    """
    original_length = len(line)
    fixed_line = line
    changes_made = False
    warning = None
    
    # Fix := spacing
    if ':=' in line:
        import re
        # Match := with optional spaces before/after
        fixed_line = re.sub(r'(\S)\s*:=\s*(\S)', r'\1 := \2', fixed_line)
        changes_made = fixed_line != line
    
    # Fix => spacing
    if '=>' in line:
        import re
        fixed_line = re.sub(r'(\S)\s*=>\s*(\S)', r'\1 => \2', fixed_line)
        changes_made = changes_made or (fixed_line != line)
    
    # Fix .. spacing
    if '..' in line and ' .. ' not in line:
        import re
        fixed_line = re.sub(r'(\S)\s*\.\.\s*(\S)', r'\1 .. \2', fixed_line)
        changes_made = changes_made or (fixed_line != line)
    
    # Check if we exceeded the limit
    if changes_made and len(fixed_line) > max_length:
        # Calculate how many chars we added
        chars_added = len(fixed_line) - original_length
        warning = f"Line exceeds {max_length} chars (was {original_length}, now {len(fixed_line)}, added {chars_added} chars)"
        
        # Decide what to do:
        # Option 1: Skip the fix
        # fixed_line = line
        # changes_made = False
        # warning += " - FIX SKIPPED"
        
        # Option 2: Apply fix anyway and warn
        warning += " - FIX APPLIED ANYWAY"
    
    return fixed_line, changes_made, warning


def demonstrate_line_length_issues():
    """Show various scenarios where spacing fixes affect line length."""
    
    print("=== Line Length Handling Demo ===\n")
    print("Maximum line length: 120 characters")
    print("=" * 120 + " (120 char marker)")
    print()
    
    test_cases = [
        # Short lines - no problem
        ("Short:=line", 
         "Short line that will still be under limit after fix"),
        
        # Line near the limit
        ("Very_Long_Variable_Name:=Another_Very_Long_Expression_That_Makes_The_Line_Close_To_The_Maximum_Length+More_Stuff",
         "Line at 115 chars - will exceed limit when spaces added"),
        
        # Line already at limit
        ("This_Line_Is_Exactly_At_The_Maximum_Length_Allowed_With_Assignment:=Value_That_Makes_It_Exactly_120_Characters_Long",
         "Line at exactly 120 chars - any addition will exceed"),
        
        # Multiple fixes needed
        ("Complex_Expression:=Array_Access(1..10)=>Initial_Value",
         "Multiple operators need spacing"),
        
        # Real-world example
        ("Status:=Ada.Directories.Exists(Path)and then not Ada.Directories.Kind(Path)=Ada.Directories.Directory",
         "Realistic code line that might exceed limit"),
    ]
    
    for line, description in test_cases:
        print(f"\n{description}:")
        print(f"Original ({len(line)} chars): {line}")
        
        fixed, was_fixed, warning = apply_spacing_fix(line)
        
        if was_fixed:
            print(f"Fixed    ({len(fixed)} chars): {fixed}")
            if warning:
                print(f"⚠️  WARNING: {warning}")
        else:
            print("No changes needed")
        
        # Visual length indicator
        if len(fixed) > 120:
            print(" " * 119 + "^-- Line exceeds limit here")


def demonstrate_handling_strategies():
    """Show different strategies for handling lines that would exceed the limit."""
    
    print("\n\n=== Strategies for Handling Length Violations ===\n")
    
    long_line = "Very_Long_Package_Name.Very_Long_Function_Call(Parameter1:=Value1,Parameter2:=Value2,Parameter3:=Value3)"
    print(f"Original line ({len(long_line)} chars):")
    print(long_line)
    print()
    
    # Strategy 1: Skip the fix
    print("Strategy 1: Skip spacing fixes if they would exceed limit")
    print("→ Pro: Never exceeds limit")
    print("→ Con: Inconsistent formatting")
    
    # Strategy 2: Apply fix and warn
    print("\nStrategy 2: Apply fix anyway and warn user")
    print("→ Pro: Consistent formatting")
    print("→ Con: May exceed limit")
    
    # Strategy 3: Selective fixing
    print("\nStrategy 3: Apply only fixes that don't exceed limit")
    print("→ Pro: Best effort formatting")
    print("→ Con: May be partially formatted")
    
    # Strategy 4: Line splitting (complex)
    print("\nStrategy 4: Split long lines (requires semantic understanding)")
    print("Example:")
    print("  -- Before:")
    print("  Result:=Long_Function(A:=1,B:=2,C:=3);")
    print("  -- After:")
    print("  Result := Long_Function(")
    print("     A => 1,")
    print("     B => 2,") 
    print("     C => 3);")
    print("→ Pro: Clean, readable result")
    print("→ Con: Complex to implement correctly")


def demonstrate_pattern_priority():
    """Show how patterns might be prioritized when line length is a concern."""
    
    print("\n\n=== Pattern Priority Demo ===\n")
    
    line = "if X:=Calculate(Range:=1..10,Filter:=Lambda)then Result:=X*2;end if;  --Complex line"
    print(f"Original line ({len(line)} chars):")
    print(line)
    print("\nThis line needs multiple fixes:")
    print("  1. Assignment operators (:=)")
    print("  2. Range operator (..)")
    print("  3. Arrow operator (=>)")  
    print("  4. Comment spacing (--)")
    print("  5. Missing spaces around 'then'")
    
    print("\nWith limited space budget (max 120 chars), we might:")
    print("  - Prioritize safety-critical spacing (operators)")
    print("  - Skip cosmetic spacing (comments)")
    print("  - Or require user to refactor long lines first")


def demonstrate_real_world_scenario():
    """Show a realistic example from actual Ada code."""
    
    print("\n\n=== Real-World Scenario ===\n")
    
    ada_code = """package body Very_Long_Package_Name is
   procedure Process_Complex_Data_Structure is
      Status:Boolean:=Ada.Directories.Exists(Full_Path_Name)and then not Ada.Directories.Kind(Full_Path_Name)=Ada.Directories.Directory;
      Result:Data_Array:=(1..100=>Default_Value,101..200=>Special_Value,others=>Zero);
   begin
      if Status then
         Logger.Log(Message=>"Processing started",Level=>Info,Timestamp=>Ada.Calendar.Clock);
      end if;
   end Process_Complex_Data_Structure;
end Very_Long_Package_Name;
"""
    
    print("Real Ada code with long lines:")
    print(ada_code)
    
    lines = ada_code.split('\n')
    max_length = 120
    
    print(f"\nAnalyzing lines (max length: {max_length}):")
    for i, line in enumerate(lines, 1):
        if line.strip():
            original_len = len(line)
            # Count potential spacing fixes
            fixes_needed = 0
            if ':=' in line and not ' := ' in line:
                fixes_needed += line.count(':=') * 2
            if '=>' in line and not ' => ' in line:
                fixes_needed += line.count('=>') * 2
            if '..' in line and not ' .. ' in line:
                fixes_needed += line.count('..') * 2
            
            if fixes_needed > 0:
                projected_len = original_len + fixes_needed
                if projected_len > max_length:
                    print(f"  Line {i}: {original_len} chars → ~{projected_len} chars (WOULD EXCEED by {projected_len - max_length})")
                    print(f"    Preview: {line[:60]}...")
                else:
                    print(f"  Line {i}: {original_len} chars → ~{projected_len} chars (OK)")


if __name__ == "__main__":
    demonstrate_line_length_issues()
    demonstrate_handling_strategies()
    demonstrate_pattern_priority()
    demonstrate_real_world_scenario()
    
    print("\n\n=== Summary ===")
    print("When spacing fixes would exceed line length limits, we have several options:")
    print("1. Skip the fix and warn the user")
    print("2. Apply the fix anyway and warn about the violation")
    print("3. Selectively apply only fixes that fit")
    print("4. Intelligently split long lines (complex, requires semantic understanding)")
    print("\nThe best approach depends on the project's style requirements and user preferences.")