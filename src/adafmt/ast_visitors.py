# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
"""
AST visitor implementations for Ada formatting rules using ANTLR best practices.

This module uses token-based offsets instead of line/column positions for
more reliable text manipulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import re

from ada2022_parser.generated import Ada2022ParserVisitor  # type: ignore[import-not-found]
from antlr4 import ParserRuleContext, Token

from .formatting_rules_model import FormattingRules


@dataclass
class TextEdit:
    """Represents a text edit operation using character offsets."""
    start_offset: int
    end_offset: int  # Exclusive (ANTLR stopIndex + 1)
    new_text: str


class AssignmentSpacingVisitor(Ada2022ParserVisitor):
    """
    AST visitor that fixes spacing around := operators using token offsets.
    
    This visitor:
    - Works with token character offsets instead of line/column
    - Protects string literals from modification
    - Applies configurable spacing rules
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        super().__init__()
        self.rules = rules
        self.source_text = source_text
        self.edits: list[TextEdit] = []
        self.protected_regions: list[tuple[int, int]] = []
        self._find_protected_regions()
    
    def _find_protected_regions(self) -> None:
        """Find string literals and comments using regex on source text."""
        # Find string literals (Ada uses double quotes)
        string_pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
        for match in string_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find comments (Ada uses --)
        comment_pattern = re.compile(r'--[^\n]*')
        for match in comment_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
    
    def visitAssignment_statement(self, ctx):
        """Visit assignment statements and fix := spacing."""
        # Check if rule is enabled
        if not self.rules.spacing.assignment.enabled:
            return self.visitChildren(ctx)
        
        # Get the source text for this statement
        if ctx.start and ctx.stop:
            start_idx = ctx.start.start
            stop_idx = ctx.stop.stop + 1  # ANTLR uses inclusive stop
            
            # Find := in the statement text
            statement_text = self.source_text[start_idx:stop_idx]
            
            # Look for := operator
            for match in re.finditer(r':=', statement_text):
                # Calculate absolute position in source
                abs_pos = start_idx + match.start()
                
                # Check if this := is in a protected region
                if self._is_protected(abs_pos):
                    continue
                
                # Check spacing before and after :=
                spaces_before = self.rules.spacing.assignment.parameters.spaces_before
                spaces_after = self.rules.spacing.assignment.parameters.spaces_after
                
                # Find the actual boundaries of the current spacing
                # Go backwards to find start of whitespace or identifier
                edit_start = abs_pos
                while edit_start > 0 and self.source_text[edit_start - 1] in ' \t':
                    edit_start -= 1
                
                # Go forward to find end of whitespace
                edit_end = abs_pos + 2  # Skip past :=
                while edit_end < len(self.source_text) and self.source_text[edit_end] in ' \t':
                    edit_end += 1
                
                # Extract the parts before and after :=
                before_part = self.source_text[edit_start:abs_pos].rstrip()
                after_part = self.source_text[abs_pos + 2:edit_end].lstrip()
                
                # Build the properly spaced version
                new_text = before_part + ' ' * spaces_before + ':=' + ' ' * spaces_after + after_part
                
                # Only add edit if something changed
                if self.source_text[edit_start:edit_end] != new_text:
                    self.edits.append(TextEdit(edit_start, edit_end, new_text))
        
        # Continue visiting children
        return self.visitChildren(ctx)
    
    def _is_protected(self, offset: int) -> bool:
        """Check if an offset is in a protected region (string literal or comment)."""
        for start, end in self.protected_regions:
            if start <= offset < end:
                return True
        return False
    
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


class TypeDeclarationSpacingVisitor(Ada2022ParserVisitor):
    """
    AST visitor that fixes spacing around type declarations.
    
    Handles:
    - type Name is ...
    - subtype Name is ...
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        super().__init__()
        self.rules = rules
        self.source_text = source_text
        self.edits: list[TextEdit] = []
    
    def visitType_declaration(self, ctx):
        """Visit type declarations and fix 'is' spacing."""
        # Check if rule is enabled  
        if not self.rules.spacing.type_declaration.enabled:
            return self.visitChildren(ctx)
            
        if ctx.start and ctx.stop:
            # Get the full text of the declaration
            start_idx = ctx.start.start
            stop_idx = ctx.stop.stop + 1
            
            # Find ' is ' in the declaration
            decl_text = self.source_text[start_idx:stop_idx]
            
            # Look for the 'is' keyword
            for match in re.finditer(r'\bis\b', decl_text):
                abs_pos = start_idx + match.start()
                
                # Check current spacing
                spaces_before = self.rules.spacing.type_declaration.parameters.spaces_before
                spaces_after = self.rules.spacing.type_declaration.parameters.spaces_after
                
                # Find boundaries
                edit_start = abs_pos
                while edit_start > 0 and self.source_text[edit_start - 1] in ' \t':
                    edit_start -= 1
                
                edit_end = abs_pos + 2  # 'is' is 2 chars
                while edit_end < len(self.source_text) and self.source_text[edit_end] in ' \t':
                    edit_end += 1
                
                # Build properly spaced version
                before = self.source_text[edit_start:abs_pos].rstrip()
                after = self.source_text[abs_pos + 2:edit_end].lstrip()
                new_text = before + ' ' * spaces_before + 'is' + ' ' * spaces_after + after
                
                if self.source_text[edit_start:edit_end] != new_text:
                    self.edits.append(TextEdit(edit_start, edit_end, new_text))
        
        return self.visitChildren(ctx)
    
    def visitSubtype_declaration(self, ctx):
        """Visit subtype declarations and fix 'is' spacing."""
        # Same logic as type declarations
        return self.visitType_declaration(ctx)
    
    def apply_edits(self) -> str:
        """Apply all collected edits to produce the formatted text."""
        if not self.edits:
            return self.source_text
        
        sorted_edits = sorted(self.edits, key=lambda e: e.start_offset, reverse=True)
        result = self.source_text
        for edit in sorted_edits:
            result = result[:edit.start_offset] + edit.new_text + result[edit.end_offset:]
        
        return result


class RangeOperatorSpacingVisitor(Ada2022ParserVisitor):
    """
    AST visitor that fixes spacing around '..' range operators.
    
    Handles:
    - type Count is range 0..100;  -> type Count is range 0 .. 100;
    - for I in 1..10 loop          -> for I in 1 .. 10 loop
    - array (1..N) of Integer      -> array (1 .. N) of Integer
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        super().__init__()
        self.rules = rules
        self.source_text = source_text
        self.edits: list[TextEdit] = []
        self.protected_regions: list[tuple[int, int]] = []
        self.processed_ranges: set[int] = set()  # Track processed range positions
        self._find_protected_regions()
    
    def _find_protected_regions(self) -> None:
        """Find string literals and comments using regex on source text."""
        # Find string literals (Ada uses double quotes)
        string_pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
        for match in string_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find comments (Ada uses --)
        comment_pattern = re.compile(r'--[^\n]*')
        for match in comment_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
    
    def visitChildren(self, node):
        """Override visitChildren to check all nodes for range operators."""
        if self.rules.spacing.range_operator.enabled and hasattr(node, 'start') and hasattr(node, 'stop'):
            self._process_range_operator(node)
        return super().visitChildren(node)
    
    def _process_range_operator(self, ctx):
        """Process a context that might contain a '..' operator."""
        if ctx.start and ctx.stop:
            start_idx = ctx.start.start
            stop_idx = ctx.stop.stop + 1
            
            # Find '..' in the range text
            range_text = self.source_text[start_idx:stop_idx]
            
            # Look for .. operator (but not ...)
            for match in re.finditer(r'\.\.(?!\.)', range_text):
                # Calculate absolute position in source
                abs_pos = start_idx + match.start()
                
                # Check if this .. is in a protected region or already processed
                if self._is_protected(abs_pos) or abs_pos in self.processed_ranges:
                    continue
                
                # Mark this position as processed
                self.processed_ranges.add(abs_pos)
                
                # Get configured spacing
                spaces_before = self.rules.spacing.range_operator.parameters.spaces_before
                spaces_after = self.rules.spacing.range_operator.parameters.spaces_after
                
                # Find the actual boundaries of whitespace around ..
                edit_start = abs_pos
                while edit_start > 0 and self.source_text[edit_start - 1] in ' \t':
                    edit_start -= 1
                
                edit_end = abs_pos + 2  # Skip past ..
                while edit_end < len(self.source_text) and self.source_text[edit_end] in ' \t':
                    edit_end += 1
                
                # Extract what's before and after the whitespace
                before_content = self.source_text[edit_start:abs_pos]
                after_content = self.source_text[abs_pos + 2:edit_end]
                
                # Build the properly spaced version
                new_text = before_content.rstrip() + ' ' * spaces_before + '..' + ' ' * spaces_after + after_content.lstrip()
                
                # Only add edit if something changed
                current_text = self.source_text[edit_start:edit_end]
                if current_text != new_text:
                    self.edits.append(TextEdit(edit_start, edit_end, new_text))
    
    def _is_protected(self, offset: int) -> bool:
        """Check if an offset is in a protected region (string literal or comment)."""
        for start, end in self.protected_regions:
            if start <= offset < end:
                return True
        return False
    
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


class ParameterAssociationSpacingVisitor(Ada2022ParserVisitor):
    """
    AST visitor that fixes spacing around '=>' parameter association operator.
    
    Handles:
    - Create(Name => "Test", Value => 42)  
    - (1 => 10, 2 => 20, others => 0)
    - when 1 => Process_One;
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        super().__init__()
        self.rules = rules
        self.source_text = source_text
        self.edits: list[TextEdit] = []
        self.protected_regions: list[tuple[int, int]] = []
        self.processed_operators: set[int] = set()  # Track processed operator positions
        self._find_protected_regions()
    
    def _find_protected_regions(self) -> None:
        """Find string literals and comments using regex on source text."""
        # Find string literals (Ada uses double quotes)
        string_pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
        for match in string_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find character literals (Ada uses single quotes)
        # Be careful not to match attributes like 'First, 'Last
        char_pattern = re.compile(r"'[^']'")
        for match in char_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find comments (Ada uses --)
        comment_pattern = re.compile(r'--[^\n]*')
        for match in comment_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
    
    def visitChildren(self, node):
        """Override visitChildren to check all nodes for => operators."""
        if self.rules.spacing.parameter_association.enabled and hasattr(node, 'start') and hasattr(node, 'stop'):
            self._process_association_operator(node)
        return super().visitChildren(node)
    
    def _process_association_operator(self, ctx):
        """Process a context that might contain a '=>' operator."""
        if ctx.start and ctx.stop:
            start_idx = ctx.start.start
            stop_idx = ctx.stop.stop + 1
            
            # Find '=>' in the node text
            node_text = self.source_text[start_idx:stop_idx]
            
            # Look for => operator
            for match in re.finditer(r'=>', node_text):
                # Calculate absolute position in source
                abs_pos = start_idx + match.start()
                
                # Check if this => is in a protected region or already processed
                if self._is_protected(abs_pos) or abs_pos in self.processed_operators:
                    continue
                
                # Mark this position as processed
                self.processed_operators.add(abs_pos)
                
                # Get configured spacing
                spaces_before = self.rules.spacing.parameter_association.parameters.spaces_before
                spaces_after = self.rules.spacing.parameter_association.parameters.spaces_after
                
                # Find the actual boundaries of whitespace around =>
                edit_start = abs_pos
                while edit_start > 0 and self.source_text[edit_start - 1] in ' \t':
                    edit_start -= 1
                
                edit_end = abs_pos + 2  # Skip past =>
                while edit_end < len(self.source_text) and self.source_text[edit_end] in ' \t':
                    edit_end += 1
                
                # Extract what's before and after the whitespace
                before_content = self.source_text[edit_start:abs_pos]
                after_content = self.source_text[abs_pos + 2:edit_end]
                
                # Build the properly spaced version
                new_text = before_content.rstrip() + ' ' * spaces_before + '=>' + ' ' * spaces_after + after_content.lstrip()
                
                # Only add edit if something changed
                current_text = self.source_text[edit_start:edit_end]
                if current_text != new_text:
                    self.edits.append(TextEdit(edit_start, edit_end, new_text))
    
    def _is_protected(self, offset: int) -> bool:
        """Check if an offset is in a protected region (string literal or comment)."""
        for start, end in self.protected_regions:
            if start <= offset < end:
                return True
        return False
    
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


class BinaryOperatorSpacingVisitor(Ada2022ParserVisitor):
    """
    AST visitor that fixes spacing around binary operators.
    
    Handles operators specified in the configuration:
    - Default: +, -, *, /
    - Configurable list via operators parameter
    """
    
    def __init__(self, rules: FormattingRules, source_text: str):
        """Initialize the visitor with formatting rules and source text."""
        super().__init__()
        self.rules = rules
        self.source_text = source_text
        self.edits: list[TextEdit] = []
        self.protected_regions: list[tuple[int, int]] = []
        self.processed_operators: set[int] = set()  # Track processed operator positions
        self._find_protected_regions()
        
        # Build regex pattern for configured operators
        self.operators = self.rules.spacing.binary_operators.parameters.operators
        # Escape special regex characters in operators
        escaped_ops = [re.escape(op) for op in self.operators]
        # Create pattern that matches operators preceded by word character, digit, or closing paren/bracket
        # This avoids matching unary operators
        self.operator_pattern = re.compile(
            r'(?<=[\w\d\)\]])(\s*)(' + '|'.join(escaped_ops) + r')(\s*)(?=[\w\d\(\[])'
        )
    
    def _find_protected_regions(self) -> None:
        """Find string literals and comments using regex on source text."""
        # Find string literals (Ada uses double quotes)
        string_pattern = re.compile(r'"(?:[^"\\]|\\.)*"')
        for match in string_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find character literals (Ada uses single quotes)
        char_pattern = re.compile(r"'[^']'")
        for match in char_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
        
        # Find comments (Ada uses --)
        comment_pattern = re.compile(r'--[^\n]*')
        for match in comment_pattern.finditer(self.source_text):
            self.protected_regions.append((match.start(), match.end()))
    
    def visitChildren(self, node):
        """Override visitChildren to check all nodes for binary operators."""
        if self.rules.spacing.binary_operators.enabled and hasattr(node, 'start') and hasattr(node, 'stop'):
            self._process_binary_operators(node)
        return super().visitChildren(node)
    
    def _process_binary_operators(self, ctx):
        """Process a context that might contain binary operators."""
        if ctx.start and ctx.stop:
            start_idx = ctx.start.start
            stop_idx = ctx.stop.stop + 1
            
            # Find operators in the node text
            node_text = self.source_text[start_idx:stop_idx]
            
            # Look for configured operators
            for match in self.operator_pattern.finditer(node_text):
                # Calculate absolute position in source
                # Group 2 is the operator (group 1 is preceding space, group 3 is following space)
                abs_pos = start_idx + match.start(2)
                operator = match.group(2)
                
                # Check if this operator is in a protected region or already processed
                if self._is_protected(abs_pos) or abs_pos in self.processed_operators:
                    continue
                
                # Mark this position as processed
                self.processed_operators.add(abs_pos)
                
                # Get configured spacing
                spaces_before = self.rules.spacing.binary_operators.parameters.spaces_before
                spaces_after = self.rules.spacing.binary_operators.parameters.spaces_after
                
                # Find the actual boundaries of whitespace around operator
                edit_start = abs_pos
                while edit_start > 0 and self.source_text[edit_start - 1] in ' \t':
                    edit_start -= 1
                
                edit_end = abs_pos + len(operator)  # Skip past operator
                while edit_end < len(self.source_text) and self.source_text[edit_end] in ' \t':
                    edit_end += 1
                
                # Extract what's before and after the whitespace
                before_content = self.source_text[edit_start:abs_pos]
                after_content = self.source_text[abs_pos + len(operator):edit_end]
                
                # Build the properly spaced version
                new_text = before_content.rstrip() + ' ' * spaces_before + operator + ' ' * spaces_after + after_content.lstrip()
                
                # Only add edit if something changed
                current_text = self.source_text[edit_start:edit_end]
                if current_text != new_text:
                    self.edits.append(TextEdit(edit_start, edit_end, new_text))
    
    def _is_protected(self, offset: int) -> bool:
        """Check if an offset is in a protected region (string literal or comment)."""
        for start, end in self.protected_regions:
            if start <= offset < end:
                return True
        return False
    
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