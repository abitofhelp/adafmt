# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Integration tests for comment spacing rules.

Tests the CommentSpacingVisitor implementation for fixing spacing
in inline comments and end-of-line comments.
"""

from __future__ import annotations

import pytest

from adafmt.comment_visitors import CommentSpacingVisitor
from adafmt.formatting_rules_model import FormattingRules


class TestCommentSpacing:
    """Test comment spacing rules with various scenarios."""
    
    @pytest.fixture
    def default_rules(self) -> FormattingRules:
        """Create default formatting rules."""
        return FormattingRules()
    
    @pytest.fixture
    def custom_rules(self) -> FormattingRules:
        """Create custom formatting rules with different spacing."""
        rules = FormattingRules()
        rules.comments.inline.parameters.min_spaces_after = 2
        rules.comments.end_of_line.parameters.min_spaces_before = 3
        return rules
    
    def _apply_formatting(self, ada_code: str, rules: FormattingRules) -> str:
        """Apply comment formatting rules to Ada code."""
        visitor = CommentSpacingVisitor(rules, ada_code)
        return visitor.apply_edits()
    
    def test_inline_comment_no_space(self, default_rules):
        """Test fixing inline comment with no space after --."""
        ada_code = """--This is a comment
procedure Test is
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert result.startswith("-- This is a comment")
        assert "--This" not in result
    
    def test_inline_comment_already_spaced(self, default_rules):
        """Test that properly spaced inline comments are not changed."""
        ada_code = """-- This is a properly spaced comment
procedure Test is
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Should remain unchanged
        assert result == ada_code
    
    def test_inline_comment_multiple_spaces(self, default_rules):
        """Test that inline comments with multiple spaces are preserved."""
        ada_code = """--   This comment has extra spaces
procedure Test is
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Should preserve the extra spaces but ensure at least min_spaces_after
        assert result.startswith("--   This comment has extra spaces")
    
    def test_end_of_line_comment_no_space_before(self, default_rules):
        """Test fixing end-of-line comment with no space before."""
        ada_code = """procedure Test is
   X : Integer := 1;--No space before
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert "X : Integer := 1;  -- No space before" in result
        assert ";--No" not in result
    
    def test_end_of_line_comment_insufficient_space(self, default_rules):
        """Test fixing end-of-line comment with insufficient space before."""
        ada_code = """procedure Test is
   X : Integer := 1; --Only one space
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Default requires at least 2 spaces before end-of-line comment
        assert "X : Integer := 1;  -- Only one space" in result
    
    def test_end_of_line_comment_extra_spaces(self, default_rules):
        """Test that extra spaces before end-of-line comments are preserved."""
        ada_code = """procedure Test is
   X : Integer := 1;     -- Many spaces
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Should preserve the extra spaces
        assert "X : Integer := 1;     -- Many spaces" in result
    
    def test_end_of_line_comment_also_needs_space_after(self, default_rules):
        """Test fixing end-of-line comment that needs both before and after spacing."""
        ada_code = """procedure Test is
   X : Integer := 1;--Needs both fixes
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert "X : Integer := 1;  -- Needs both fixes" in result
    
    def test_mixed_comments(self, default_rules):
        """Test file with mixed inline and end-of-line comments."""
        ada_code = """--File header comment
procedure Test is
   X : Integer := 1;  -- Already good
   Y : Integer := 2;--Needs fixing
   
   --Inline comment section
   -- Another inline comment
   
begin
   null; --End of line
   --Final comment
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        lines = result.split('\n')
        assert lines[0] == "-- File header comment"
        assert "X : Integer := 1;  -- Already good" in result
        assert "Y : Integer := 2;  -- Needs fixing" in result
        assert "-- Inline comment section" in result
        assert "null;  -- End of line" in result
        assert "-- Final comment" in result
    
    def test_custom_spacing_rules(self, custom_rules):
        """Test comment formatting with custom spacing values."""
        ada_code = """--Comment
procedure Test is
   X : Integer := 1; --EOL comment
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, custom_rules)
        
        # Custom rules: 2 spaces after --, 3 spaces before EOL comment
        assert result.startswith("--  Comment")
        assert "X : Integer := 1;   --  EOL comment" in result
    
    def test_empty_comment(self, default_rules):
        """Test handling of empty comments."""
        ada_code = """--
procedure Test is
   X : Integer := 1; --
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Empty comments should remain unchanged
        lines = result.split('\n')
        assert lines[0] == "--"
        assert "X : Integer := 1;  --" in result
    
    def test_comment_with_special_characters(self, default_rules):
        """Test comments with special characters."""
        ada_code = """--TODO: Fix this!
procedure Test is
   X : Integer := 1;  --NOTE: Important!!!
begin
   null;  --(c) 2025
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        assert "-- TODO: Fix this!" in result
        assert "-- NOTE: Important!!!" in result
        assert "-- (c) 2025" in result
    
    def test_disabled_inline_rule(self):
        """Test that inline comment formatting is not applied when disabled."""
        rules = FormattingRules()
        rules.comments.inline.enabled = False
        
        ada_code = """--No space after
procedure Test is
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, rules)
        
        # Should remain unchanged
        assert result.startswith("--No space after")
    
    def test_disabled_end_of_line_rule(self):
        """Test that end-of-line comment formatting is not applied when disabled."""
        rules = FormattingRules()
        rules.comments.end_of_line.enabled = False
        
        ada_code = """procedure Test is
   X : Integer := 1;--No space
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, rules)
        
        # When end-of-line rule is disabled, end-of-line comments are not processed
        # even for spacing after -- (that's only done when processing end-of-line comments)
        assert "X : Integer := 1;--No space" in result
    
    def test_comment_indentation_preserved(self, default_rules):
        """Test that comment indentation is preserved."""
        ada_code = """procedure Test is
   -- Level 1 comment
      -- Level 2 comment
         -- Level 3 comment
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        # Indentation should be preserved
        lines = result.split('\n')
        assert lines[1] == "   -- Level 1 comment"
        assert lines[2] == "      -- Level 2 comment"
        assert lines[3] == "         -- Level 3 comment"
    
    def test_multiline_comment_block(self, default_rules):
        """Test formatting of multiline comment blocks."""
        ada_code = """--=======================
--Module: Test Module
--Author: Test Author
--Date: 2025-01-01
--=======================
procedure Test is
begin
   null;
end Test;"""
        
        result = self._apply_formatting(ada_code, default_rules)
        
        lines = result.split('\n')
        assert lines[0] == "-- ======================="
        assert lines[1] == "-- Module: Test Module"
        assert lines[2] == "-- Author: Test Author"
        assert lines[3] == "-- Date: 2025-01-01"
        assert lines[4] == "-- ======================="