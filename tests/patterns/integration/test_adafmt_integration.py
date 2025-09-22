# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

from tests.patterns.test_utils import PatternEngine, DEFAULT_PATTERNS, fake_als, compiles_ada

def test_als_then_patterns_end_to_end(tmp_path):
    rules = PatternEngine.load_list(DEFAULT_PATTERNS)
    before = """with Ada.Text_IO; use Ada.Text_IO;
procedure Demo is
   X:Integer:=42; --bad  spacing
   Y :  String:=  "Hello" ;   --comment
   --foo
   Z : array (  1..10)  of Integer := (1,2,3, others => 0);
begin
   Put_Line("value -- inside string");  --   EOL comment
end Demo;"""
    
    # COMPILATION CHECK: Verify input is valid Ada
    compiles_before, error_before = compiles_ada(before)
    assert compiles_before, f"Test input must be valid Ada code: {error_before}"
    
    # Note: decl_colon01 only fixes lines WITHOUT comments (due to (?!.*--) lookahead)
    # So X:Integer and Y : String lines with comments are not fixed by decl_colon01
    # The comment patterns will fix the comment spacing
    # Also: fake_als doesn't normalize general spacing, only := operators
    want = """with Ada.Text_IO; use Ada.Text_IO;
procedure Demo is
   X:Integer := 42; -- bad  spacing
   Y :  String := "Hello"; -- comment
   --  foo
   Z : array (1 .. 10)  of Integer := (1, 2, 3, others => 0);
begin
   Put_Line("value -- inside string");  --   EOL comment
end Demo;
"""
    after_als = fake_als(before)
    out, stats = PatternEngine.apply(after_als, rules, timeout_ms=50)
    assert out == want
    
    # COMPILATION CHECK: Verify output still compiles
    compiles_after, error_after = compiles_ada(out)
    assert compiles_after, f"Pattern formatting broke compilation: {error_after}"
    
    # sanity: a few key rules fired
    for k in ("range_dots01","assign_set01","comment_eol2","cmt_whole_02"):
        assert k in stats.replacements_by_rule


def test_compilation_validation_catches_broken_patterns(tmp_path):
    """Test that compilation validation catches patterns that break code."""
    # Create a pattern that would break Ada syntax
    bad_pattern = {
        "name": "bad_semi_del",  # Exactly 12 characters
        "title": "Remove semicolons (BAD!)",
        "category": "hygiene",
        "find": r";(\s*--[^\n]*)?$",  # Semicolon at end of line (with optional comment)
        "replace": r"\1"  # Remove the semicolon, keep comment
    }
    
    rules = PatternEngine.load_list([bad_pattern])
    
    ada_code = """with Ada.Text_IO; use Ada.Text_IO;
procedure Test_Bad is
   X : Integer := 42;  -- This semicolon will be removed
begin
   Put_Line("Hello");  -- This one too
end Test_Bad;"""
    
    # Verify input compiles
    compiles_before, _ = compiles_ada(ada_code)
    assert compiles_before, "Test setup: input should be valid Ada"
    
    # Apply the bad pattern
    after_als = fake_als(ada_code)
    out, stats = PatternEngine.apply(after_als, rules, timeout_ms=50)
    
    # Verify the pattern did make changes
    assert stats.total_replacements > 0, "Pattern should have made replacements"
    
    # COMPILATION CHECK: This should fail!
    compiles_after, error_after = compiles_ada(out)
    assert not compiles_after, "Bad pattern should break compilation"
    assert "error:" in error_after.lower(), f"Should have compilation errors: {error_after}"