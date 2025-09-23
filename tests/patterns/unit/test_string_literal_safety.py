# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test that patterns don't modify content inside string literals."""

from tests.patterns.test_utils import PatternEngine, fake_als, compiles_ada


class TestStringLiteralSafety:
    """Test that comment patterns don't modify -- inside string literals."""
    
    def test_comment_eol2_preserves_string_literals(self):
        """Test that comment_eol2 doesn't change -- inside strings."""
        pattern = {
            "name": "comment_eol2",
            "title": "EOL comment spacing",
            "category": "comment",
            "find": r"^((?:(?:[^\"\n]*\"){2})*[^\"\n]*?[^\"\s])\s*--(?![\s\-])(.*?)$",
            "replace": r"\g<1> -- \g<2>",
            "flags": ["MULTILINE"]
        }
        
        ada_code = """with Ada.Text_IO; use Ada.Text_IO;
with Ada.Strings.Fixed; use Ada.Strings.Fixed;

procedure Test_Strings is
   SQL_Metacharacters : constant String := "';--/**/";
   Shell_Metacharacters : constant String := "&|;<>--";
   Comment_Check : constant String := "--";
   
   X : Integer := 42;--This needs fixing
   Y : String := "test--value";--Another fix needed
   
   Input : String := "test";
   Dangerous : String := "test";
   Result : String := "test";
   
   function Check (S : String) return String is (S);
begin
   if Index (Input, "--") > 0 then
      Put_Line ("Found --");
   end if;
   
   Dangerous := "--" & Input; -- This comment is OK
   Result := Check ("--test");--Fix this comment
end Test_Strings;"""
        
        # Apply pattern
        rules = PatternEngine.load_list([pattern])
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify string literals are preserved
        assert 'SQL_Metacharacters : constant String := "\';--/**/";' in result
        assert 'Shell_Metacharacters : constant String := "&|;<>--";' in result
        assert 'Comment_Check : constant String := "--";' in result
        assert 'if Index (Input, "--") > 0 then' in result
        assert 'Dangerous := "--" & Input;' in result
        assert 'Result := Check ("--test");' in result
        
        # Verify comments were fixed
        assert 'X : Integer := 42; -- This needs fixing' in result
        assert 'Y : String := "test--value"; -- Another fix needed' in result
        assert 'Result := Check ("--test"); -- Fix this comment' in result
        
        # Should fix exactly 3 comments
        assert stats.total_replacements == 3
        
        # Verify the code still compiles
        compiles_after, error = compiles_ada(result)
        assert compiles_after, f"Pattern broke compilation: {error}"
    
    def test_all_patterns_preserve_string_literals(self):
        """Test that no pattern modifies content inside string literals."""
        # Load all patterns
        from tests.patterns.test_utils import DEFAULT_PATTERNS
        rules = PatternEngine.load_list(DEFAULT_PATTERNS)
        
        ada_code = """procedure Test_All_Patterns is
   -- Test various string literals that contain pattern-like content
   Assignment_Op : constant String := ":=";
   Arrow_Op : constant String := "=>";
   Range_Op : constant String := "..";
   Comment_Marker : constant String := "--";
   Semicolon : constant String := ";";
   Parens : constant String := "()";
   Quoted_Quote : constant String := "\\"";
   
   -- These should be formatted normally
   X:Integer:=42;--bad spacing
   Y:=Func(A=>B,C=>D);
   Z:array(1..10)of Integer;
begin
   null;--comment
end Test_All_Patterns;"""
        
        # Apply all patterns
        after_als = fake_als(ada_code)
        result, stats = PatternEngine.apply(after_als, rules)
        
        # Verify all string literals are completely unchanged
        assert 'Assignment_Op : constant String := ":=";' in result
        assert 'Arrow_Op : constant String := "=>";' in result
        assert 'Range_Op : constant String := "..";' in result
        assert 'Comment_Marker : constant String := "--";' in result
        assert 'Semicolon : constant String := ";";' in result
        assert 'Parens : constant String := "()";' in result
        assert 'Quoted_Quote : constant String := "\\"";' in result
        
        # Verify patterns worked on non-string content
        assert 'X : Integer := 42; -- bad spacing' in result
        assert 'Y := Func(A => B, C => D);' in result
        assert 'Z : array (1 .. 10) of Integer;' in result
        assert 'null; -- comment' in result
        
        # Verify compilation
        compiles_after, error = compiles_ada(result)
        assert compiles_after, f"Patterns broke compilation: {error}"
    
    def test_separator_lines_vs_string_literals(self):
        """Test that separator line pattern doesn't match strings."""
        pattern = {
            "name": "cmt_sep_line",
            "title": "Fix separator lines",
            "category": "comment",
            "find": r"^([ \t]*)--([ \t]?)([-=*#]{3,})$",
            "replace": r"\g<1>--  \g<3>",
            "flags": ["MULTILINE"]
        }
        
        ada_code = '''procedure Test_Separators is
   -- Real separator lines
   ----------
   -- ======
   --******
   
   -- String literals that look like separators
   Dashes : constant String := "----------";
   Equals : constant String := "==========";
   Comment_Like : constant String := "-- ======";
   Mixed : constant String := "--******";
begin
   --=======
   null;
   ----------
end Test_Separators;'''
        
        # Apply pattern
        rules = PatternEngine.load_list([pattern])
        result, stats = PatternEngine.apply(ada_code, rules)
        
        # Verify separator lines were fixed
        assert '   --  --------' in result
        assert '   --  ======' in result
        assert '   --  ******' in result
        assert '   --  =======' in result
        assert '   --  --------' in result
        
        # Verify string literals unchanged
        assert 'Dashes : constant String := "----------";' in result
        assert 'Equals : constant String := "==========";' in result
        assert 'Comment_Like : constant String := "-- ======";' in result
        assert 'Mixed : constant String := "--******";' in result
        
        # Should fix 5 separator lines
        assert stats.total_replacements == 5