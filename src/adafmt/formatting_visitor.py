# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Base visitor classes for Ada formatting operations.

This module provides the foundation for implementing formatting rules using
the visitor pattern with the Ada 2022 ANTLR parser. All formatting visitors
inherit from these base classes to ensure consistent behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Set

from returns.io import IOFailure, IOResult, IOSuccess, impure_safe
from returns.result import Failure, Result, Success

from .errors import VisitorError


@dataclass(frozen=True)
class TextPosition:
    """Represents a position in source text.
    
    Attributes:
        line: Line number (0-based)
        column: Column number (0-based)
    """
    line: int
    column: int
    
    def __post_init__(self):
        """Validate position values."""
        if self.line < 0 or self.column < 0:
            raise ValueError("Line and column must be non-negative")


@dataclass(frozen=True)
class TextRange:
    """Represents a range in source text.
    
    Attributes:
        start: Starting position
        end: Ending position (exclusive)
    """
    start: TextPosition
    end: TextPosition
    
    def __post_init__(self):
        """Validate range ordering."""
        if (self.start.line > self.end.line or 
            (self.start.line == self.end.line and self.start.column >= self.end.column)):
            raise ValueError("Invalid range: start must be before end")
    
    def contains(self, position: TextPosition) -> bool:
        """Check if position is within this range."""
        if position.line < self.start.line or position.line > self.end.line:
            return False
        if position.line == self.start.line and position.column < self.start.column:
            return False
        if position.line == self.end.line and position.column >= self.end.column:
            return False
        return True


@dataclass
class TextModification:
    """Represents a text modification to be applied.
    
    Attributes:
        range: Range of text to replace
        new_text: Replacement text
        description: Human-readable description of the change
    """
    range: TextRange
    new_text: str
    description: str
    
    def affects_line(self, line_num: int) -> bool:
        """Check if this modification affects the given line."""
        return self.range.start.line <= line_num <= self.range.end.line


@dataclass
class VisitorResult:
    """Result of applying a formatting visitor.
    
    Attributes:
        modifications: List of text modifications to apply
        modified_content: The modified source content
        applied_rules: Set of rule names that were applied
        statistics: Dictionary of statistics (e.g., replacement counts)
    """
    modifications: List[TextModification] = field(default_factory=list)
    modified_content: str = ""
    applied_rules: Set[str] = field(default_factory=set)
    statistics: dict = field(default_factory=dict)
    
    @property
    def has_changes(self) -> bool:
        """Check if any modifications were made."""
        return len(self.modifications) > 0
    
    @property
    def modification_count(self) -> int:
        """Get total number of modifications."""
        return len(self.modifications)


class FormattingVisitorBase(ABC):
    """Abstract base class for all formatting visitors.
    
    This class provides common functionality for visiting AST nodes and
    tracking string literal regions to prevent accidental modifications
    within string literals.
    """
    
    def __init__(self, source_lines: List[str], path: Optional[Path] = None):
        """Initialize the visitor.
        
        Args:
            source_lines: Original source lines
            path: Optional file path for error context
        """
        self.source_lines = source_lines
        self.path = path or Path("")
        self.original_content = "\n".join(source_lines)
        self.modifications: List[TextModification] = []
        self.string_ranges: List[TextRange] = []
        self.applied_rules: Set[str] = set()
        self.statistics: dict = {}
        
        # Track visitor state
        self._current_line = 0
        self._current_column = 0
    
    @abstractmethod
    def get_visitor_name(self) -> str:
        """Get the name of this visitor for reporting."""
        pass
    
    @abstractmethod
    def get_supported_rules(self) -> List[str]:
        """Get list of rule names this visitor supports."""
        pass
    
    def visit_tree(self, tree: Any) -> Result[VisitorResult, VisitorError]:
        """Visit the AST tree and apply formatting rules.
        
        Args:
            tree: ANTLR parse tree root node
            
        Returns:
            Result[VisitorResult, VisitorError]: Visitor result or error
        """
        try:
            # First pass: identify string literal regions
            self._collect_string_regions(tree)
            
            # Second pass: apply formatting rules
            self._apply_formatting_rules(tree)
            
            # Apply modifications to get final content
            final_content = self._apply_modifications()
            
            return Success(VisitorResult(
                modifications=self.modifications.copy(),
                modified_content=final_content,
                applied_rules=self.applied_rules.copy(),
                statistics=self.statistics.copy()
            ))
            
        except Exception as e:
            return Failure(VisitorError(
                path=self.path,
                visitor_name=self.get_visitor_name(),
                node_type=tree.__class__.__name__ if tree else "unknown",
                message=str(e)
            ))
    
    def _collect_string_regions(self, node: Any) -> None:
        """Collect all string literal regions for protection.
        
        Args:
            node: ANTLR parse tree node
        """
        if not node:
            return
        
        # Check if this is a string literal node
        # Note: Adjust based on actual ada2022_parser grammar
        if hasattr(node, 'getText') and self._is_string_literal(node):
            self._record_string_region(node)
        
        # Recursively process children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self._collect_string_regions(child)
    
    def _is_string_literal(self, node: Any) -> bool:
        """Check if node represents a string literal.
        
        Args:
            node: ANTLR parse tree node
            
        Returns:
            bool: True if node is a string literal
        """
        # This needs to be implemented based on the actual ada2022_parser grammar
        # Common patterns to check:
        node_text = getattr(node, 'getText', lambda: '')()
        return (node_text.startswith('"') and node_text.endswith('"')) or \
               (node_text.startswith("'") and node_text.endswith("'"))
    
    def _record_string_region(self, node: Any) -> None:
        """Record a string literal region for protection.
        
        Args:
            node: String literal node
        """
        if not hasattr(node, 'start') or not hasattr(node, 'stop'):
            return
        
        start_line = node.start.line - 1  # Convert to 0-based
        start_col = node.start.column
        stop_line = node.stop.line - 1
        stop_col = node.stop.column + 1  # Make exclusive
        
        string_range = TextRange(
            start=TextPosition(start_line, start_col),
            end=TextPosition(stop_line, stop_col)
        )
        
        self.string_ranges.append(string_range)
    
    @abstractmethod
    def _apply_formatting_rules(self, tree: Any) -> None:
        """Apply formatting rules to the AST.
        
        Args:
            tree: ANTLR parse tree root node
        """
        pass
    
    def is_in_string_literal(self, position: TextPosition) -> bool:
        """Check if position is inside a string literal.
        
        Args:
            position: Position to check
            
        Returns:
            bool: True if position is in a string literal
        """
        return any(range_.contains(position) for range_ in self.string_ranges)
    
    def is_line_in_string_literal(self, line_num: int) -> bool:
        """Check if any part of line is in a string literal.
        
        Args:
            line_num: Line number to check (0-based)
            
        Returns:
            bool: True if any part of line is in a string literal
        """
        return any(
            range_.start.line <= line_num <= range_.end.line
            for range_ in self.string_ranges
        )
    
    def record_modification(
        self,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
        new_text: str,
        description: str
    ) -> None:
        """Record a text modification.
        
        Args:
            start_line: Starting line (0-based)
            start_col: Starting column (0-based)
            end_line: Ending line (0-based)
            end_col: Ending column (0-based, exclusive)
            new_text: Replacement text
            description: Description of the change
        """
        # Validate that modification is not in string literal
        start_pos = TextPosition(start_line, start_col)
        end_pos = TextPosition(end_line, end_col)
        
        if self.is_in_string_literal(start_pos) or self.is_in_string_literal(end_pos):
            # Skip modifications inside string literals
            return
        
        modification = TextModification(
            range=TextRange(start=start_pos, end=end_pos),
            new_text=new_text,
            description=description
        )
        
        self.modifications.append(modification)
    
    def record_line_modification(
        self,
        line_num: int,
        new_line: str,
        description: str
    ) -> None:
        """Record a full line modification.
        
        Args:
            line_num: Line number to replace (0-based)
            new_line: New line content
            description: Description of the change
        """
        if line_num < 0 or line_num >= len(self.source_lines):
            return
        
        # Don't modify lines that contain string literals
        if self.is_line_in_string_literal(line_num):
            return
        
        old_line = self.source_lines[line_num]
        line_length = len(old_line)
        
        self.record_modification(
            start_line=line_num,
            start_col=0,
            end_line=line_num,
            end_col=line_length,
            new_text=new_line,
            description=description
        )
    
    @impure_safe
    def _apply_modifications_internal(self) -> str:
        """Internal modification application with automatic exception handling.
        
        Returns:
            str: Modified content
            
        Note:
            @impure_safe automatically converts exceptions to IOResult[str, Exception]
        """
        if not self.modifications:
            return self.original_content
        
        # Sort modifications by position (reverse order for correct application)
        sorted_mods = sorted(
            self.modifications,
            key=lambda m: (m.range.start.line, m.range.start.column),
            reverse=True
        )
        
        lines = self.source_lines.copy()
        
        for mod in sorted_mods:
            lines = self._apply_single_modification(lines, mod)
        
        return "\n".join(lines)
    
    def _apply_modifications(self) -> str:
        """Apply all recorded modifications to get final content.
        
        Returns:
            str: Modified content
        """
        result: IOResult[str, Exception] = self._apply_modifications_internal()
        
        if isinstance(result, IOFailure):
            # If modification application fails, return original content
            return self.original_content
        
        return result.unwrap()
    
    def _apply_single_modification(
        self,
        lines: List[str],
        modification: TextModification
    ) -> List[str]:
        """Apply a single modification to the lines.
        
        Args:
            lines: Current lines
            modification: Modification to apply
            
        Returns:
            List[str]: Modified lines
        """
        start = modification.range.start
        end = modification.range.end
        
        if start.line >= len(lines) or end.line >= len(lines):
            return lines  # Invalid range, skip
        
        # Handle single-line modification
        if start.line == end.line:
            line = lines[start.line]
            new_line = (
                line[:start.column] +
                modification.new_text +
                line[end.column:]
            )
            lines[start.line] = new_line
            return lines
        
        # Handle multi-line modification
        start_line = lines[start.line]
        end_line = lines[end.line]
        
        new_line = (
            start_line[:start.column] +
            modification.new_text +
            end_line[end.column:]
        )
        
        # Replace the range with the new line
        new_lines = lines[:start.line] + [new_line] + lines[end.line + 1:]
        
        return new_lines
    
    def add_statistic(self, key: str, value: Any) -> None:
        """Add a statistic for reporting.
        
        Args:
            key: Statistic name
            value: Statistic value
        """
        self.statistics[key] = value
    
    def increment_statistic(self, key: str, increment: int = 1) -> None:
        """Increment a numeric statistic.
        
        Args:
            key: Statistic name
            increment: Amount to increment
        """
        self.statistics[key] = self.statistics.get(key, 0) + increment