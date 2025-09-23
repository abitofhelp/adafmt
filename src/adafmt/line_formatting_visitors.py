# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
Line formatting visitor implementations for Ada code.

This module provides visitors for handling line-level formatting rules
like trailing whitespace removal and final newline normalization.
"""

from __future__ import annotations

from dataclasses import dataclass

from .formatting_rules_model import FormattingRules


@dataclass
class LineFormatEdit:
    """Represents a line formatting edit."""
    start_offset: int
    end_offset: int
    new_text: str
    edit_type: str  # 'trailing_whitespace' or 'final_newline'


class LineFormattingVisitor:
    """
    Visitor that applies line formatting rules.
    
    Handles:
    - Trailing whitespace removal from all lines
    - Final newline normalization at end of file
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        self.rules = rules
        self.source_text = source_text
        self.edits: list[LineFormatEdit] = []
        self._process_line_formatting()
    
    def _process_line_formatting(self) -> None:
        """Process all line formatting rules."""
        # Process trailing whitespace first
        if self.rules.line_formatting.trailing_whitespace.enabled:
            self._process_trailing_whitespace()
        
        # Then process final newline
        if self.rules.line_formatting.final_newline.enabled:
            self._process_final_newline()
    
    def _process_trailing_whitespace(self) -> None:
        """Remove trailing whitespace from all lines."""
        lines = self.source_text.split('\n')
        offset = 0
        
        for line_num, line in enumerate(lines):
            line_length = len(line)
            trimmed_line = line.rstrip()
            
            if len(trimmed_line) < line_length:
                # Line has trailing whitespace
                edit = LineFormatEdit(
                    start_offset=offset + len(trimmed_line),
                    end_offset=offset + line_length,
                    new_text='',
                    edit_type='trailing_whitespace'
                )
                self.edits.append(edit)
            
            # Update offset for next line (add 1 for newline character)
            offset += line_length + 1
    
    def _process_final_newline(self) -> None:
        """Ensure file ends with the configured number of newlines."""
        if not self.source_text:
            return
        
        desired_count = self.rules.line_formatting.final_newline.parameters.newline_count
        
        # Count trailing newlines
        trailing_newlines = 0
        pos = len(self.source_text) - 1
        
        while pos >= 0 and self.source_text[pos] == '\n':
            trailing_newlines += 1
            pos -= 1
        
        # Determine what changes are needed
        if trailing_newlines != desired_count:
            # Calculate the position after all content (excluding trailing newlines)
            content_end = pos + 1
            
            # Create edit to set exact number of newlines
            new_ending = '\n' * desired_count
            
            edit = LineFormatEdit(
                start_offset=content_end,
                end_offset=len(self.source_text),
                new_text=new_ending,
                edit_type='final_newline'
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