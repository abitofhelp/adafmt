# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Parser-based pattern processor for Ada formatting.

This module orchestrates the parser-based visitors to provide the same
interface as the regex-based pattern system while using AST-aware processing.
It serves as a bridge between the old pattern system and the new parser-based
architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from returns.result import Failure, Result, Success

from .comment_spacing_visitor import CommentSpacingVisitor
from .errors import ParseError, PatternError
from .formatting_visitor import VisitorResult
from .operator_spacing_visitor import OperatorSpacingVisitor
from .parser_wrapper import AdaParserWrapper, ParseResult


@dataclass
class ProcessorResult:
    """Result of applying parser-based patterns.
    
    Attributes:
        success: Whether processing succeeded
        modified_content: The modified source content
        original_content: The original source content
        applied_patterns: Set of pattern names that were applied
        visitor_results: Results from individual visitors
        statistics: Combined statistics from all visitors
        error: Error message if processing failed
    """
    success: bool
    modified_content: str = ""
    original_content: str = ""
    applied_patterns: Set[str] = field(default_factory=set)
    visitor_results: List[VisitorResult] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def has_changes(self) -> bool:
        """Check if any modifications were made."""
        return self.modified_content != self.original_content
    
    @property
    def total_modifications(self) -> int:
        """Get total number of modifications across all visitors."""
        return sum(result.modification_count for result in self.visitor_results)


class ParserPatternProcessor:
    """Parser-based pattern processor for Ada source code.
    
    This processor uses AST visitors instead of regex patterns to provide
    context-aware formatting. It maintains compatibility with the existing
    pattern system interface while providing superior correctness.
    """
    
    def __init__(self, enabled_patterns: Optional[Set[str]] = None):
        """Initialize the parser-based pattern processor.
        
        Args:
            enabled_patterns: Set of pattern names to enable. If None, all patterns are enabled.
        """
        self.enabled_patterns = enabled_patterns
        self.parser = AdaParserWrapper()
        
        # Register available visitors
        self.visitor_classes = {
            'comment_spacing': CommentSpacingVisitor,
            'operator_spacing': OperatorSpacingVisitor,
        }
        
        # Map pattern names to visitor names for compatibility
        self.pattern_to_visitor = {
            # Comment patterns
            'comment_spacing': 'comment_spacing',
            'comment_single_space': 'comment_spacing',
            
            # Operator patterns
            'assignment_spacing': 'operator_spacing',
            'arrow_spacing': 'operator_spacing', 
            'range_spacing': 'operator_spacing',
            'comparison_spacing': 'operator_spacing',
            'equality_spacing': 'operator_spacing',
            'concatenation_spacing': 'operator_spacing',
            
            # Legacy pattern names for backward compatibility
            'assign_set01': 'operator_spacing',  # Maps to assignment spacing
        }
    
    def is_enabled(self) -> bool:
        """Check if parser-based processing is enabled."""
        return True  # Always enabled when using this processor
    
    def get_available_patterns(self) -> Set[str]:
        """Get set of available pattern names."""
        return set(self.pattern_to_visitor.keys())
    
    def get_enabled_patterns(self) -> Set[str]:
        """Get set of enabled pattern names."""
        if self.enabled_patterns is None:
            return self.get_available_patterns()
        return self.enabled_patterns & self.get_available_patterns()
    
    def process_content(
        self,
        content: str,
        path: Optional[Path] = None
    ) -> Result[ProcessorResult, PatternError | ParseError]:
        """Process Ada content with parser-based patterns.
        
        Args:
            content: Ada source code to process
            path: Optional file path for error context
            
        Returns:
            Result[ProcessorResult, PatternError | ParseError]: Processing result or error
        """
        if not content.strip():
            return Success(ProcessorResult(
                success=True,
                modified_content=content,
                original_content=content
            ))
        
        # Parse the content
        parse_result = self.parser.parse_content(content, path)
        
        if isinstance(parse_result, Failure):
            # Parse failed - return original content with error
            parse_error = parse_result.failure()
            return Failure(PatternError(
                path=path or Path(""),
                pattern_name="parser",
                message=f"Parse failed: {parse_error.message}",
                line=parse_error.line,
                original_error=str(parse_error)
            ))
        
        parsed = parse_result.unwrap()
        
        # Apply visitors
        return self._apply_visitors(parsed)
    
    def process_file(
        self,
        file_path: Union[str, Path]
    ) -> Result[ProcessorResult, PatternError | ParseError]:
        """Process Ada file with parser-based patterns.
        
        Args:
            file_path: Path to Ada source file
            
        Returns:
            Result[ProcessorResult, PatternError | ParseError]: Processing result or error
        """
        path = Path(file_path)
        
        # Parse the file
        parse_result = self.parser.parse_file(path)
        
        if isinstance(parse_result, Failure):
            error = parse_result.failure()
            
            # Handle both ParseError and FileError
            if isinstance(error, ParseError):
                return Failure(PatternError(
                    path=path,
                    pattern_name="parser",
                    message=f"Parse failed: {error.message}",
                    line=error.line,
                    original_error=str(error)
                ))
            else:
                # FileError
                return Failure(PatternError(
                    path=path,
                    pattern_name="file_io",
                    message=f"File operation failed: {error.message}",
                    line=0,
                    original_error=str(error)
                ))
        
        parsed = parse_result.unwrap()
        
        # Apply visitors
        return self._apply_visitors(parsed)
    
    def _apply_visitors(self, parse_result: ParseResult) -> Result[ProcessorResult, PatternError]:
        """Apply enabled visitors to the parsed content.
        
        Args:
            parse_result: Parsed Ada content
            
        Returns:
            Result[ProcessorResult, PatternError]: Processing result or error
        """
        enabled_patterns = self.get_enabled_patterns()
        
        # Determine which visitors to run
        visitors_to_run = set()
        for pattern in enabled_patterns:
            if pattern in self.pattern_to_visitor:
                visitors_to_run.add(self.pattern_to_visitor[pattern])
        
        if not visitors_to_run:
            # No visitors to run
            return Success(ProcessorResult(
                success=True,
                modified_content=parse_result.content,
                original_content=parse_result.content
            ))
        
        # Apply visitors in order
        current_content = parse_result.content
        current_lines = parse_result.source_lines.copy()
        all_visitor_results = []
        all_applied_patterns = set()
        combined_statistics = {}
        
        for visitor_name in sorted(visitors_to_run):
            if visitor_name not in self.visitor_classes:
                continue
            
            # Create and run visitor
            visitor_class = self.visitor_classes[visitor_name]
            visitor = visitor_class(current_lines, parse_result.path)
            
            visitor_result_result = visitor.visit_tree(parse_result.ast)
            
            if isinstance(visitor_result_result, Failure):
                visitor_error = visitor_result_result.failure()
                return Failure(PatternError(
                    path=parse_result.path or Path(""),
                    pattern_name=visitor_name,
                    message=f"Visitor failed: {visitor_error.message}",
                    line=0,
                    original_error=str(visitor_error)
                ))
            
            visitor_result = visitor_result_result.unwrap()
            
            # Update current content if changes were made
            if visitor_result.has_changes:
                current_content = visitor_result.modified_content
                current_lines = current_content.splitlines()
            
            # Collect results
            all_visitor_results.append(visitor_result)
            all_applied_patterns.update(visitor_result.applied_rules)
            combined_statistics[visitor_name] = visitor_result.statistics
        
        return Success(ProcessorResult(
            success=True,
            modified_content=current_content,
            original_content=parse_result.content,
            applied_patterns=all_applied_patterns,
            visitor_results=all_visitor_results,
            statistics=combined_statistics
        ))
    
    def validate_patterns(self, patterns: Set[str]) -> Result[Set[str], PatternError]:
        """Validate that pattern names are supported.
        
        Args:
            patterns: Set of pattern names to validate
            
        Returns:
            Result[Set[str], PatternError]: Valid patterns or error
        """
        available = self.get_available_patterns()
        invalid = patterns - available
        
        if invalid:
            return Failure(PatternError(
                path=Path(""),
                pattern_name="validation",
                message=f"Unknown patterns: {', '.join(sorted(invalid))}. "
                       f"Available: {', '.join(sorted(available))}",
                line=0
            ))
        
        return Success(patterns)
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about available patterns and visitors.
        
        Returns:
            Dict[str, Any]: Pattern statistics
        """
        return {
            'total_patterns': len(self.get_available_patterns()),
            'enabled_patterns': len(self.get_enabled_patterns()),
            'available_patterns': sorted(self.get_available_patterns()),
            'enabled_pattern_list': sorted(self.get_enabled_patterns()),
            'visitor_classes': sorted(self.visitor_classes.keys()),
            'pattern_mappings': dict(self.pattern_to_visitor)
        }


# Convenience functions for direct usage

def process_ada_content(
    content: str,
    path: Optional[Path] = None,
    enabled_patterns: Optional[Set[str]] = None
) -> Result[ProcessorResult, PatternError | ParseError]:
    """Process Ada content with parser-based patterns.
    
    Args:
        content: Ada source code to process
        path: Optional file path for error context
        enabled_patterns: Optional set of patterns to enable
        
    Returns:
        Result[ProcessorResult, PatternError | ParseError]: Processing result or error
    """
    processor = ParserPatternProcessor(enabled_patterns)
    return processor.process_content(content, path)


def process_ada_file(
    file_path: Union[str, Path],
    enabled_patterns: Optional[Set[str]] = None
) -> Result[ProcessorResult, PatternError | ParseError]:
    """Process Ada file with parser-based patterns.
    
    Args:
        file_path: Path to Ada source file
        enabled_patterns: Optional set of patterns to enable
        
    Returns:
        Result[ProcessorResult, PatternError | ParseError]: Processing result or error
    """
    processor = ParserPatternProcessor(enabled_patterns)
    return processor.process_file(file_path)