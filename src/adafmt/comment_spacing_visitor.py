# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Comment spacing visitor for Ada formatting.

This visitor implements the comment spacing rules that ensure proper spacing
after comment indicators (--). It replaces the regex-based comment patterns
with context-aware AST-based processing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from returns.result import Failure

from .formatting_visitor import FormattingVisitorBase


class CommentSpacingVisitor(FormattingVisitorBase):
    """Visitor to fix spacing after comment indicators.
    
    This visitor ensures that comments follow the format:
    -- <space> <comment text>
    
    Rules applied:
    1. Ensure single space after --
    2. Remove multiple spaces after --
    3. Handle inline comments properly
    4. Preserve string literals
    """
    
    def __init__(self, source_lines: List[str], path: Optional[Path] = None):
        """Initialize the comment spacing visitor.
        
        Args:
            source_lines: Original source lines
            path: Optional file path for error context
        """
        super().__init__(source_lines, path)
        
        # Pattern to match comment indicators
        self.comment_pattern = re.compile(r'--')
        
        # Statistics tracking
        self.fixed_comments = 0
        self.inline_comments = 0
        self.standalone_comments = 0
    
    def get_visitor_name(self) -> str:
        """Get the name of this visitor."""
        return "CommentSpacingVisitor"
    
    def get_supported_rules(self) -> List[str]:
        """Get list of rule names this visitor supports."""
        return ["comment_spacing", "comment_single_space"]
    
    def _apply_formatting_rules(self, tree: Any) -> None:
        """Apply comment spacing rules to the source.
        
        Args:
            tree: ANTLR parse tree root node
        """
        # Process each line for comment spacing
        for line_num, line in enumerate(self.source_lines):
            if self.is_line_in_string_literal(line_num):
                continue  # Skip lines in string literals
            
            modified_line = self._fix_comment_spacing_in_line(line, line_num)
            
            if modified_line != line:
                self.record_line_modification(
                    line_num=line_num,
                    new_line=modified_line,
                    description=f"Fixed comment spacing on line {line_num + 1}"
                )
                self.applied_rules.add("comment_spacing")
                self.fixed_comments += 1
        
        # Update statistics
        self.add_statistic("fixed_comments", self.fixed_comments)
        self.add_statistic("inline_comments", self.inline_comments)
        self.add_statistic("standalone_comments", self.standalone_comments)
    
    def _fix_comment_spacing_in_line(self, line: str, line_num: int) -> str:
        """Fix comment spacing in a single line.
        
        Args:
            line: Source line to process
            line_num: Line number (0-based) for position tracking
            
        Returns:
            str: Fixed line
        """
        # Find all comment indicators
        comment_matches = list(self.comment_pattern.finditer(line))
        
        if not comment_matches:
            return line
        
        # Process each comment from right to left to maintain positions
        modified_line = line
        
        for match in reversed(comment_matches):
            start_pos = match.start()
            
            # Check if this comment is in a string literal
            from .formatting_visitor import TextPosition
            position = TextPosition(line_num, start_pos)
            
            if self.is_in_string_literal(position):
                continue  # Skip comments in string literals
            
            # Fix spacing after this comment
            modified_line = self._fix_single_comment(modified_line, start_pos, line_num)
        
        return modified_line
    
    def _fix_single_comment(self, line: str, comment_pos: int, line_num: int) -> str:
        """Fix spacing after a single comment indicator.
        
        Args:
            line: Line containing the comment
            comment_pos: Position of the -- in the line
            line_num: Line number for classification
            
        Returns:
            str: Line with fixed comment spacing
        """
        if comment_pos + 2 >= len(line):
            # Comment at end of line, no spacing needed
            return line
        
        # Classify comment type
        is_inline = self._is_inline_comment(line, comment_pos)
        if is_inline:
            self.inline_comments += 1
        else:
            self.standalone_comments += 1
        
        # Get the text after --
        after_comment = line[comment_pos + 2:]
        
        # Determine correct spacing
        if not after_comment:
            # Comment at end of line
            return line
        
        # Check current spacing
        if after_comment[0] == ' ':
            # Has space, check if it's correct
            if len(after_comment) > 1 and after_comment[1] == ' ':
                # Multiple spaces, fix to single space
                fixed_after = ' ' + after_comment.lstrip(' ')
                return line[:comment_pos + 2] + fixed_after
            else:
                # Single space, correct
                return line
        else:
            # No space, add one
            fixed_after = ' ' + after_comment
            return line[:comment_pos + 2] + fixed_after
    
    def _is_inline_comment(self, line: str, comment_pos: int) -> bool:
        """Check if comment is inline (has code before it).
        
        Args:
            line: Line containing the comment
            comment_pos: Position of the comment
            
        Returns:
            bool: True if comment is inline
        """
        before_comment = line[:comment_pos].strip()
        return bool(before_comment)
    
    def _has_correct_spacing(self, after_comment: str) -> bool:
        """Check if text after comment has correct spacing.
        
        Args:
            after_comment: Text after -- indicator
            
        Returns:
            bool: True if spacing is correct
        """
        if not after_comment:
            return True  # Empty comment is fine
        
        if after_comment[0] != ' ':
            return False  # No space
        
        if len(after_comment) > 1 and after_comment[1] == ' ':
            return False  # Multiple spaces
        
        return True  # Single space is correct


# Convenience function for standalone usage
def fix_comment_spacing(
    source_lines: List[str],
    path: Optional[Path] = None
) -> tuple[List[str], dict]:
    """Fix comment spacing in Ada source lines.
    
    Args:
        source_lines: Original source lines
        path: Optional file path for error context
        
    Returns:
        tuple[List[str], dict]: (modified_lines, statistics)
    """
    visitor = CommentSpacingVisitor(source_lines, path)
    
    # Create a dummy AST node since we're processing line-by-line
    class DummyTree:
        pass
    
    result = visitor.visit_tree(DummyTree())
    
    if isinstance(result, Failure):
        error = result.failure()
        return source_lines, {"error": str(error)}
    
    visitor_result = result.unwrap()
    modified_lines = visitor_result.modified_content.splitlines()
    
    return modified_lines, visitor_result.statistics