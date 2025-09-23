# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Operator spacing visitor for Ada formatting.

This visitor implements operator spacing rules for Ada operators such as
assignment (:=), arrows (=>), ranges (..), and comparison operators.
It provides context-aware formatting that respects string literals.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from returns.result import Failure

from .formatting_visitor import FormattingVisitorBase, TextPosition


class OperatorInfo(TypedDict):
    """Type definition for operator spacing configuration."""
    spaces_before: int
    spaces_after: int
    rule: str


class OperatorSpacingVisitor(FormattingVisitorBase):
    """Visitor to fix spacing around Ada operators.
    
    This visitor ensures proper spacing around operators:
    - Assignment operator: :=
    - Arrow operator: =>
    - Range operator: ..
    - Comparison operators: =, /=, <, <=, >, >=
    - Concatenation operator: &
    
    Rules applied:
    1. Ensure single space before and after operators
    2. Handle special cases for certain contexts
    3. Preserve string literals
    4. Track statistics for reporting
    """
    
    # Operator definitions with their required spacing
    OPERATORS: Dict[str, OperatorInfo] = {
        ':=': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'assignment_spacing'},
        '=>': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'arrow_spacing'},
        '..': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'range_spacing'},
        '/=': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'comparison_spacing'},
        '<=': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'comparison_spacing'},
        '>=': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'comparison_spacing'},
        '&': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'concatenation_spacing'},
    }
    
    # Single character operators that need context checking
    SINGLE_CHAR_OPERATORS: Dict[str, OperatorInfo] = {
        '=': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'equality_spacing'},
        '<': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'comparison_spacing'},
        '>': {'spaces_before': 1, 'spaces_after': 1, 'rule': 'comparison_spacing'},
    }
    
    def __init__(self, source_lines: List[str], path: Optional[Path] = None):
        """Initialize the operator spacing visitor.
        
        Args:
            source_lines: Original source lines
            path: Optional file path for error context
        """
        super().__init__(source_lines, path)
        
        # Statistics tracking
        self.fixed_operators: Dict[str, int] = {}
        self.total_fixes = 0
        
        # Build comprehensive operator pattern
        all_operators = list(self.OPERATORS.keys()) + list(self.SINGLE_CHAR_OPERATORS.keys())
        # Sort by length (longest first) to avoid partial matches
        all_operators.sort(key=len, reverse=True)
        
        # Escape special regex characters
        escaped_operators = [re.escape(op) for op in all_operators]
        self.operator_pattern = re.compile('|'.join(escaped_operators))
    
    def get_visitor_name(self) -> str:
        """Get the name of this visitor."""
        return "OperatorSpacingVisitor"
    
    def get_supported_rules(self) -> List[str]:
        """Get list of rule names this visitor supports."""
        rules = set()
        for op_info in self.OPERATORS.values():
            rules.add(op_info['rule'])
        for op_info in self.SINGLE_CHAR_OPERATORS.values():
            rules.add(op_info['rule'])
        return list(rules)
    
    def _apply_formatting_rules(self, tree: Any) -> None:
        """Apply operator spacing rules to the source.
        
        Args:
            tree: ANTLR parse tree root node
        """
        # Process each line for operator spacing
        for line_num, line in enumerate(self.source_lines):
            if self.is_line_in_string_literal(line_num):
                continue  # Skip lines in string literals
            
            modified_line = self._fix_operator_spacing_in_line(line, line_num)
            
            if modified_line != line:
                self.record_line_modification(
                    line_num=line_num,
                    new_line=modified_line,
                    description=f"Fixed operator spacing on line {line_num + 1}"
                )
        
        # Update statistics
        self.add_statistic("total_operator_fixes", self.total_fixes)
        self.add_statistic("fixes_by_operator", self.fixed_operators.copy())
        
        # Add applied rules
        for rule in self.get_supported_rules():
            if any(self.fixed_operators.get(op, 0) > 0 
                   for op in self._get_operators_for_rule(rule)):
                self.applied_rules.add(rule)
    
    def _get_operators_for_rule(self, rule: str) -> List[str]:
        """Get operators that belong to a specific rule.
        
        Args:
            rule: Rule name
            
        Returns:
            List[str]: Operators for the rule
        """
        operators = []
        for op, info in self.OPERATORS.items():
            if info['rule'] == rule:
                operators.append(op)
        for op, info in self.SINGLE_CHAR_OPERATORS.items():
            if info['rule'] == rule:
                operators.append(op)
        return operators
    
    def _fix_operator_spacing_in_line(self, line: str, line_num: int) -> str:
        """Fix operator spacing in a single line.
        
        Args:
            line: Source line to process
            line_num: Line number (0-based) for position tracking
            
        Returns:
            str: Fixed line
        """
        # Find all operator matches
        operator_matches = list(self.operator_pattern.finditer(line))
        
        if not operator_matches:
            return line
        
        # Process each operator from right to left to maintain positions
        modified_line = line
        
        for match in reversed(operator_matches):
            operator = match.group()
            start_pos = match.start()
            
            # Check if this operator is in a string literal
            position = TextPosition(line_num, start_pos)
            
            if self.is_in_string_literal(position):
                continue  # Skip operators in string literals
            
            # Check if this is a valid operator context
            if not self._is_valid_operator_context(modified_line, operator, start_pos):
                continue
            
            # Fix spacing around this operator
            new_line = self._fix_single_operator(modified_line, operator, start_pos)
            
            if new_line != modified_line:
                self.fixed_operators[operator] = self.fixed_operators.get(operator, 0) + 1
                self.total_fixes += 1
                modified_line = new_line
        
        return modified_line
    
    def _is_valid_operator_context(self, line: str, operator: str, pos: int) -> bool:
        """Check if operator is in a valid context for spacing rules.
        
        Args:
            line: Line containing the operator
            operator: The operator string
            pos: Position of the operator
            
        Returns:
            bool: True if operator should be processed
        """
        # Special handling for single character operators that might be part of comments
        if operator in self.SINGLE_CHAR_OPERATORS:
            # Check if it's part of a comment
            comment_pos = line.find('--')
            if comment_pos >= 0 and pos > comment_pos:
                return False  # Skip operators in comments
            
            # Check for specific contexts where single char operators shouldn't be spaced
            if operator == '=':
                # Don't space = in aspects or attributes
                before = line[:pos].rstrip()
                if before.endswith("'") or "aspect" in before.lower():
                    return False
        
        # Check for operators in compiler directives
        stripped_line = line.strip()
        if stripped_line.startswith('#'):
            return False  # Skip preprocessing directives
        
        return True
    
    def _fix_single_operator(self, line: str, operator: str, pos: int) -> str:
        """Fix spacing around a single operator.
        
        Args:
            line: Line containing the operator
            operator: The operator string
            pos: Position of the operator
            
        Returns:
            str: Line with fixed operator spacing
        """
        # Get operator configuration
        if operator in self.OPERATORS:
            config = self.OPERATORS[operator]
        elif operator in self.SINGLE_CHAR_OPERATORS:
            config = self.SINGLE_CHAR_OPERATORS[operator]
        else:
            return line  # Unknown operator
        
        spaces_before = config['spaces_before']
        spaces_after = config['spaces_after']
        
        # Extract parts of the line
        before_op = line[:pos]
        after_op = line[pos + len(operator):]
        
        # Fix spacing before operator
        fixed_before = self._fix_spacing_before(before_op, spaces_before)
        
        # Fix spacing after operator
        fixed_after = self._fix_spacing_after(after_op, spaces_after)
        
        return fixed_before + operator + fixed_after
    
    def _fix_spacing_before(self, before: str, required_spaces: int) -> str:
        """Fix spacing before an operator.
        
        Args:
            before: Text before the operator
            required_spaces: Number of spaces required
            
        Returns:
            str: Fixed text before operator
        """
        if not before:
            return before
        
        # Count trailing spaces
        trailing_spaces = len(before) - len(before.rstrip(' '))
        
        if trailing_spaces == required_spaces:
            return before  # Already correct
        
        # Remove existing trailing spaces and add correct amount
        trimmed = before.rstrip(' ')
        return trimmed + (' ' * required_spaces)
    
    def _fix_spacing_after(self, after: str, required_spaces: int) -> str:
        """Fix spacing after an operator.
        
        Args:
            after: Text after the operator
            required_spaces: Number of spaces required
            
        Returns:
            str: Fixed text after operator
        """
        if not after:
            return after
        
        # Count leading spaces
        leading_spaces = len(after) - len(after.lstrip(' '))
        
        if leading_spaces == required_spaces:
            return after  # Already correct
        
        # Remove existing leading spaces and add correct amount
        trimmed = after.lstrip(' ')
        return (' ' * required_spaces) + trimmed
    
    def get_operator_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about operator fixes.
        
        Returns:
            Dict[str, Any]: Operator statistics
        """
        stats = {
            'total_fixes': self.total_fixes,
            'fixes_by_operator': self.fixed_operators.copy(),
            'rules_applied': list(self.applied_rules),
        }
        
        # Add rule-level statistics
        rule_stats = {}
        for rule in self.get_supported_rules():
            operators = self._get_operators_for_rule(rule)
            rule_fixes = sum(self.fixed_operators.get(op, 0) for op in operators)
            if rule_fixes > 0:
                rule_stats[rule] = rule_fixes
        
        stats['fixes_by_rule'] = rule_stats
        return stats


# Convenience function for standalone usage
def fix_operator_spacing(
    source_lines: List[str],
    path: Optional[Path] = None
) -> Tuple[List[str], Dict[str, Any]]:
    """Fix operator spacing in Ada source lines.
    
    Args:
        source_lines: Original source lines
        path: Optional file path for error context
        
    Returns:
        Tuple[List[str], Dict[str, Any]]: (modified_lines, statistics)
    """
    visitor = OperatorSpacingVisitor(source_lines, path)
    
    # Create a dummy AST node since we're processing line-by-line
    class DummyTree:
        pass
    
    result = visitor.visit_tree(DummyTree())
    
    if isinstance(result, Failure):
        error = result.failure()
        return source_lines, {"error": str(error)}
    
    visitor_result = result.unwrap()
    modified_lines = visitor_result.modified_content.splitlines()
    
    return modified_lines, visitor.get_operator_statistics()