# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
AST visitor implementations for grammar-based formatting rules.

This module provides AST visitors that traverse the Ada 2022 parse tree
and apply formatting rules based on the grammar structure.
"""

from typing import Optional
import re

from ada2022_parser.generated import Ada2022ParserVisitor  # type: ignore[import-not-found]

from .formatting_rules_model import FormattingRules


class Edit:
    """Represents a text edit to apply."""
    
    def __init__(self, line: int, start_col: int, end_col: int, new_text: str):
        self.line = line
        self.start_col = start_col
        self.end_col = end_col
        self.new_text = new_text
    
    def __repr__(self) -> str:
        return f"Edit(line={self.line}, cols={self.start_col}-{self.end_col}, text={self.new_text!r})"


class AssignmentSpacingVisitor(Ada2022ParserVisitor):
    """Fix spacing around := in assignment statements only."""
    
    def __init__(self, rules: FormattingRules, source_lines: list[str]):
        self.rules = rules
        self.source_lines = source_lines
        self.edits: list[Edit] = []
        self.protected_regions: list[tuple[int, int, int]] = []  # line, start_col, end_col
    
    def visitString_literal(self, ctx):
        """Record string literal regions to protect them from edits."""
        line = ctx.start.line - 1  # Convert to 0-based
        start_col = ctx.start.column
        end_col = ctx.stop.column + 1 if ctx.stop else start_col + len(ctx.getText())
        self.protected_regions.append((line, start_col, end_col))
        return self.visitChildren(ctx)
    
    def visitAssignment_statement(self, ctx):
        """Fix := spacing in assignment statements."""
        # Check if rule is enabled
        if not self.rules.spacing.assignment.enabled:
            return self.visitChildren(ctx)
        
        # Get the line containing the assignment
        line_num = ctx.start.line - 1  # Convert to 0-based
        if line_num >= len(self.source_lines):
            return self.visitChildren(ctx)
            
        line_text = self.source_lines[line_num]
        
        # Find := in the line (should be exactly one in an assignment_statement)
        match = re.search(r':=', line_text)
        if match:
            col = match.start()
            
            # Check if this position is in a protected region
            if self._is_protected(line_num, col):
                return self.visitChildren(ctx)
            
            # Check current spacing
            spaces_before = self.rules.spacing.assignment.parameters.spaces_before
            spaces_after = self.rules.spacing.assignment.parameters.spaces_after
            
            # Look at characters before and after :=
            before_ok = (col == 0 or 
                        line_text[col-1] == ' ' and 
                        (col < 2 or line_text[col-2:col] == ' ' * spaces_before))
            
            after_ok = (col + 2 >= len(line_text) or
                       line_text[col+2] == ' ' and
                       line_text[col+2:col+2+spaces_after] == ' ' * spaces_after)
            
            if not before_ok or not after_ok:
                # Need to fix spacing
                # Find the extent of the current token (no spaces)
                start = col
                while start > 0 and line_text[start-1] not in ' \t':
                    start -= 1
                
                end = col + 2
                while end < len(line_text) and line_text[end] not in ' \t;':
                    end += 1
                
                # Create the properly spaced version
                before_part = line_text[start:col].rstrip()
                after_part = line_text[col+2:end].lstrip()
                
                new_text = (before_part + 
                           ' ' * spaces_before + ':=' + ' ' * spaces_after + 
                           after_part)
                
                # Record the edit
                self.edits.append(Edit(line_num, start, end, new_text))
        
        return self.visitChildren(ctx)
    
    def _is_protected(self, line: int, col: int) -> bool:
        """Check if a position is in a protected region (string literal)."""
        for prot_line, start_col, end_col in self.protected_regions:
            if line == prot_line and start_col <= col < end_col:
                return True
        return False
    
    def apply_edits(self) -> list[str]:
        """Apply all collected edits to produce modified source lines."""
        # Sort edits by line, then by column (reverse order for same line)
        self.edits.sort(key=lambda e: (e.line, -e.start_col))
        
        result_lines = self.source_lines.copy()
        
        for edit in self.edits:
            line = result_lines[edit.line]
            result_lines[edit.line] = (
                line[:edit.start_col] + 
                edit.new_text + 
                line[edit.end_col:]
            )
        
        return result_lines