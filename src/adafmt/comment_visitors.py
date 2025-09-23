# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
AST visitor implementations for Ada comment formatting rules.

This module provides visitors for handling comment-related formatting,
including inline comments and end-of-line comments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .formatting_rules_model import FormattingRules


@dataclass
class CommentEdit:
    """Represents a comment formatting edit."""
    start_offset: int
    end_offset: int
    new_text: str
    comment_type: str  # 'inline' or 'end_of_line'


class CommentSpacingVisitor:
    """
    Visitor that fixes spacing in comments.
    
    Handles:
    - Inline comments: ensuring proper spacing after --
    - End-of-line comments: ensuring proper spacing before comments at end of lines
    
    Note: This doesn't inherit from Ada2022ParserVisitor because comments
    are typically not part of the AST. We process the source text directly.
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        self.rules = rules
        self.source_text = source_text
        self.edits: list[CommentEdit] = []
        self._process_comments()
    
    def _process_comments(self) -> None:
        """Process all comments in the source text."""
        lines = self.source_text.split('\n')
        offset = 0
        
        for line_num, line in enumerate(lines):
            # Find comments in the line
            comment_match = re.search(r'--', line)
            
            if comment_match:
                # Determine if it's inline or end-of-line
                before_comment = line[:comment_match.start()]
                
                if before_comment.strip():
                    # End-of-line comment (has code before it)
                    self._process_end_of_line_comment(line, offset, comment_match)
                else:
                    # Inline comment (standalone comment line)
                    self._process_inline_comment(line, offset, comment_match)
            
            # Update offset for next line (add 1 for newline character)
            offset += len(line) + 1
    
    def _process_inline_comment(self, line: str, line_offset: int, comment_match) -> None:
        """Process standalone inline comments."""
        if not self.rules.comments.inline.enabled:
            return
        
        comment_pos = comment_match.start()
        comment_text = line[comment_pos:]
        
        # Check spacing after --
        if len(comment_text) > 2 and comment_text[2] not in ' \t\n':
            # Need to add space after --
            min_spaces = self.rules.comments.inline.parameters.min_spaces_after
            
            # Extract the comment content after --
            content_start = 2
            existing_spaces = 0
            
            # Count existing spaces
            while content_start < len(comment_text) and comment_text[content_start] in ' \t':
                existing_spaces += 1
                content_start += 1
            
            # Only add edit if we need more spaces
            if existing_spaces < min_spaces and content_start < len(comment_text):
                # Build new comment with proper spacing
                new_comment = '--' + ' ' * min_spaces + comment_text[content_start:]
                
                edit = CommentEdit(
                    start_offset=line_offset + comment_pos,
                    end_offset=line_offset + len(line),
                    new_text=line[:comment_pos] + new_comment,
                    comment_type='inline'
                )
                self.edits.append(edit)
    
    def _process_end_of_line_comment(self, line: str, line_offset: int, comment_match) -> None:
        """Process end-of-line comments."""
        if not self.rules.comments.end_of_line.enabled:
            return
        
        comment_pos = comment_match.start()
        before_comment = line[:comment_pos]
        
        # Check spacing before comment
        min_spaces_before = self.rules.comments.end_of_line.parameters.min_spaces_before
        
        # Count trailing spaces before comment
        spaces_before = 0
        check_pos = comment_pos - 1
        while check_pos >= 0 and line[check_pos] in ' \t':
            spaces_before += 1
            check_pos -= 1
        
        # Also process spacing after -- for end-of-line comments
        comment_text = line[comment_pos:]
        needs_space_after = (self.rules.comments.inline.enabled and 
                            len(comment_text) > 2 and 
                            comment_text[2] not in ' \t\n')
        
        # Determine if we need to make changes
        needs_change = spaces_before < min_spaces_before or needs_space_after
        
        if needs_change:
            # Build the properly formatted line
            code_part = before_comment.rstrip()
            
            # Build comment part with proper spacing after --
            if needs_space_after:
                content_start = 2
                while content_start < len(comment_text) and comment_text[content_start] in ' \t':
                    content_start += 1
                min_spaces_after = self.rules.comments.inline.parameters.min_spaces_after
                comment_part = '--' + ' ' * min_spaces_after + comment_text[content_start:]
            else:
                comment_part = comment_text
            
            # Combine with proper spacing before comment
            new_line = code_part + ' ' * max(spaces_before, min_spaces_before) + comment_part
            
            edit = CommentEdit(
                start_offset=line_offset,
                end_offset=line_offset + len(line),
                new_text=new_line,
                comment_type='end_of_line'
            )
            self.edits.append(edit)
    
    def apply_edits(self) -> str:
        """Apply all collected edits to produce the formatted text."""
        if not self.edits:
            return self.source_text
        
        # Sort edits by start position (reverse order for safe application)
        sorted_edits = sorted(self.edits, key=lambda e: e.start_offset, reverse=True)
        
        # Apply edits from end to start to preserve offsets
        result = self.source_text
        for edit in sorted_edits:
            result = result[:edit.start_offset] + edit.new_text + result[edit.end_offset:]
        
        return result