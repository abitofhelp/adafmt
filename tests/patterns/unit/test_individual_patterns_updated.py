# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Updated tests for the new comment patterns.

These tests replace the old comment pattern tests to match the new
GNAT-compliant patterns that are less aggressive.
"""

from tests.patterns.test_utils import PatternEngine, fake_als, compiles_ada


class TestUpdatedCommentPatterns:
    """Test the new, less aggressive comment patterns."""
    
    def test_comment_eol2_transforms_and_compiles(self):
        """Test new end-of-line comment pattern - only fixes missing space."""
        pattern = {
            "name": "comment_eol2",
            "title": "EOL comment spacing: one before --, one after",
            "category": "comment",
            "find": r"^((?:(?:[^\"\n]*\"){2})*[^\"\n]*?\S)[ \t]*--(?!\s)(.*?)$",
            "replace": r"\g<1> -- \g<2>",
            "flags": ["MULTILINE"]
        }
        
        ada_code = """procedure Test is
   X : Integer := 42;--This needs fixing (no space)
   Y : Integer := 100; -- This is already correct
   Z : Integer := 200;  --  This has two spaces (also correct)
   W : Integer := 300;   --   Three spaces (also correct)
begin
   null;--Another fix needed
   null; -- Already good
end Test;"""
        
        # Verify input compiles
        compiles_before, error = compiles_ada(ada_code)
        assert compiles_before, f"Input should compile: {error}"
        
        # Apply pattern
        rules = PatternEngine.load_list([pattern])
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify only comments with NO space were fixed
        assert "; -- This needs fixing (no space)" in result
        assert "; -- Another fix needed" in result
        
        # Verify comments with 1+ spaces were NOT changed
        assert "; -- This is already correct" in result
        assert ";  --  This has two spaces (also correct)" in result
        assert ";   --   Three spaces (also correct)" in result
        
        # Should only fix 2 comments (the ones with no space)
        assert stats.total_replacements == 2
        
        # Verify output still compiles
        compiles_after, error = compiles_ada(result)
        assert compiles_after, f"Pattern broke compilation: {error}"
    
    def test_cmt_whole_02_transforms_and_compiles(self):
        """Test new whole-line comment pattern - only fixes 0-1 spaces."""
        pattern = {
            "name": "cmt_whole_02",
            "title": "Whole-line comment spacing: `--  text` (GNAT style)",
            "category": "comment",
            "find": r"^([ \t]*)--(?:[ \t])?(?![ \t])(\S.*?)$",
            "replace": r"\g<1>--  \g<2>",
            "flags": ["MULTILINE"]
        }
        
        ada_code = """procedure Test is
   --This needs fixing (no space)
   -- This needs fixing (one space)
   --  This is already correct (two spaces)
   --   This has three spaces (should not change)
   --    This has four spaces (should not change)
   X : Integer;
begin
   if True then
      --Indented no space
      -- Indented one space
      --  Indented two spaces
      --   Indented three spaces
      null;
   end if;
end Test;"""
        
        # Verify input compiles
        compiles_before, error = compiles_ada(ada_code)
        assert compiles_before, f"Input should compile: {error}"
        
        # Apply pattern
        rules = PatternEngine.load_list([pattern])
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify comments with 0-1 spaces were fixed
        assert "   --  This needs fixing (no space)" in result
        assert "   --  This needs fixing (one space)" in result
        assert "      --  Indented no space" in result
        assert "      --  Indented one space" in result
        
        # Verify comments with 2+ spaces were NOT changed
        assert "   --  This is already correct (two spaces)" in result
        assert "   --   This has three spaces (should not change)" in result
        assert "   --    This has four spaces (should not change)" in result
        assert "      --  Indented two spaces" in result
        assert "      --   Indented three spaces" in result
        
        # Should only fix 4 comments (0-1 space ones)
        assert stats.total_replacements == 4
        
        # Verify output still compiles
        compiles_after, error = compiles_ada(result)
        assert compiles_after, f"Pattern broke compilation: {error}"
    
    def test_separator_lines_pattern(self):
        """Test the new separator lines pattern."""
        pattern = {
            "name": "cmt_sep_line",
            "title": "Fix separator line comments to have 2 spaces",
            "category": "comment",
            "find": r"^([ \t]*)--([ \t]?)([-=*#]{3,})$",
            "replace": r"\g<1>--  \g<3>",
            "flags": ["MULTILINE"]
        }
        
        ada_code = """procedure Test is
   -- ========================================
   --========================================
   -- ------------------------------------
   --  ####################################
   -- This is not a separator line
begin
   -- ************************************
   --**************************************
   null;
end Test;"""
        
        # Apply pattern
        rules = PatternEngine.load_list([pattern])
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify separator lines were fixed to have 2 spaces
        assert "   --  ========================================" in result
        assert "   --  ========================================" in result  # Both get fixed
        assert "   --  ------------------------------------" in result
        assert "   --  ####################################" in result  # Already has 2
        assert "   --  ************************************" in result
        assert "   --  ************************************" in result  # Both get fixed
        
        # Regular comment should not be changed by this pattern
        assert "-- This is not a separator line" in result
        
        # Should fix 5 separator lines (ones with 0 or 1 space)
        assert stats.total_replacements == 5
    
    def test_patterns_preserve_ascii_art(self):
        """Test that ASCII art is preserved by the new patterns."""
        patterns = [
            {
                "name": "cmt_whole_02",
                "title": "Whole-line comment spacing",
                "category": "comment",
                "find": r"^([ \t]*)--(?:[ \t])?(?![ \t])(\S.*?)$",
                "replace": r"\g<1>--  \g<2>",
                "flags": ["MULTILINE"]
            },
            {
                "name": "cmt_sep_line",
                "title": "Fix separator lines",
                "category": "comment",
                "find": r"^([ \t]*)--([ \t]?)([-=*#]{3,})$",
                "replace": r"\g<1>--  \g<3>",
                "flags": ["MULTILINE"]
            }
        ]
        
        ada_code = """procedure Test is
   --  Tree structure (should not change):
   --  +-- Root
   --  |   +-- Child 1
   --  |   |   +-- Grandchild
   --  |   +-- Child 2
   --  +-- Another Root
   
   --  Box diagram (should not change):
   --  +---------------------------------------+
   --  | This is a box comment                 |
   --  | With multiple lines                   |
   --  +---------------------------------------+
   
   -- =========================================
   --  Section Header
   -- =========================================
begin
   null;
end Test;"""
        
        # Apply patterns
        rules = PatternEngine.load_list(patterns)
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify ASCII art is preserved exactly
        assert "   --  +-- Root" in result
        assert "   --  |   +-- Child 1" in result
        assert "   --  |   |   +-- Grandchild" in result
        assert "   --  +---------------------------------------+" in result
        assert "   --  | This is a box comment                 |" in result
        
        # Separator lines should be fixed
        assert "   --  =========================================" in result
        
        # Only the separator lines should be changed (2 of them)
        assert stats.total_replacements == 2
    
    def test_gnat_compliance_with_new_patterns(self):
        """Test that output complies with GNAT -gnatyy style."""
        patterns = [
            {
                "name": "cmt_whole_02",
                "title": "Whole-line comment spacing",
                "category": "comment",
                "find": r"^([ \t]*)--(?:[ \t])?(?![ \t])(\S.*?)$",
                "replace": r"\g<1>--  \g<2>",
                "flags": ["MULTILINE"]
            },
            {
                "name": "comment_eol2",
                "title": "EOL comment spacing",
                "category": "comment",
                "find": r"^((?:(?:[^\"\n]*\"){2})*[^\"\n]*?\S)[ \t]*--(?!\s)(.*?)$",
                "replace": r"\g<1> -- \g<2>",
                "flags": ["MULTILINE"]
            },
            {
                "name": "cmt_sep_line",
                "title": "Fix separator lines",
                "category": "comment",
                "find": r"^([ \t]*)--([ \t]?)([-=*#]{3,})$",
                "replace": r"\g<1>--  \g<3>",
                "flags": ["MULTILINE"]
            }
        ]
        
        # Code with various GNAT style violations
        ada_code = """procedure Test is
   --This violates GNAT style (no space)
   -- This also violates (one space only)
   X : Integer := 42;--No space inline comment
   -- =====================================
begin
   --Another violation
   null; -- This inline comment is OK
end Test;"""
        
        # Apply all comment patterns
        rules = PatternEngine.load_list(patterns)
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # The result should now be GNAT-compliant:
        # - Whole-line comments have 2 spaces
        # - Inline comments have at least 1 space
        # - Separator lines have 2 spaces
        expected_compliant = """procedure Test is
   --  This violates GNAT style (no space)
   --  This also violates (one space only)
   X : Integer := 42; -- No space inline comment
   --  =====================================
begin
   --  Another violation
   null; -- This inline comment is OK
end Test;"""
        
        # Normalize whitespace for comparison
        assert result.strip() == expected_compliant.strip()
        
        # Verify it compiles
        compiles_after, error = compiles_ada(result)
        assert compiles_after, f"GNAT-compliant output should compile: {error}"