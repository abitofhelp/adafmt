# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Validation pipeline for Ada source code formatting.

This module provides a complete pipeline that combines parsing, formatting,
and GNAT validation to ensure that formatting changes do not introduce
errors in Ada source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from returns.result import Failure, Result, Success

from .errors import ParseError, PatternError, ValidationError
from .gnat_validator import GNATValidator, ValidationResult
from .parser_pattern_processor import ParserPatternProcessor, ProcessorResult
from .parser_wrapper import AdaParserWrapper


@dataclass
class PipelineResult:
    """Complete result of the validation pipeline.
    
    Attributes:
        success: Whether the entire pipeline succeeded
        original_content: The original source content
        formatted_content: The formatted source content
        formatting_applied: Whether any formatting was applied
        validation_passed: Whether GNAT validation passed
        parse_result: Parser result (if parsing succeeded)
        formatting_result: Formatting result (if formatting was applied)
        validation_result: GNAT validation result (if validation was run)
        applied_patterns: Set of patterns that were applied
        error: Error message if pipeline failed
        stage_failed: Which stage failed ('parse', 'format', 'validate')
    """
    success: bool
    original_content: str = ""
    formatted_content: str = ""
    formatting_applied: bool = False
    validation_passed: bool = False
    parse_result: Optional[Any] = None
    formatting_result: Optional[ProcessorResult] = None
    validation_result: Optional[ValidationResult] = None
    applied_patterns: Set[str] = field(default_factory=set)
    error: Optional[str] = None
    stage_failed: Optional[str] = None
    
    @property
    def has_changes(self) -> bool:
        """Check if any formatting changes were made."""
        return self.formatted_content != self.original_content
    
    @property
    def is_safe_to_apply(self) -> bool:
        """Check if changes are safe to apply (passed validation)."""
        return self.success and (not self.has_changes or self.validation_passed)


class ValidationPipeline:
    """Complete validation pipeline for Ada source formatting.
    
    This pipeline coordinates:
    1. Ada parsing for syntax validation
    2. Pattern-based formatting
    3. GNAT compiler validation
    4. Result reporting and error handling
    """
    
    def __init__(
        self,
        enabled_patterns: Optional[Set[str]] = None,
        gnat_flags: Optional[List[str]] = None,
        validate_with_gnat: bool = True,
        gnat_timeout: float = 30.0,
        ada_version: str = "2022"
    ):
        """Initialize the validation pipeline.
        
        Args:
            enabled_patterns: Set of patterns to enable for formatting
            gnat_flags: Additional GNAT compiler flags
            validate_with_gnat: Whether to run GNAT validation
            gnat_timeout: Timeout for GNAT validation
            ada_version: Ada language version to use
        """
        self.enabled_patterns = enabled_patterns
        self.validate_with_gnat = validate_with_gnat
        self.ada_version = ada_version
        
        # Initialize components
        self.parser = AdaParserWrapper()
        self.formatter = ParserPatternProcessor(enabled_patterns)
        
        self.validator: GNATValidator | None
        if validate_with_gnat:
            self.validator = GNATValidator(
                gnat_flags=gnat_flags,
                timeout_seconds=gnat_timeout
            )
        else:
            self.validator = None
    
    def is_gnat_available(self) -> Result[bool, ValidationError]:
        """Check if GNAT validation is available.
        
        Returns:
            Result[bool, ValidationError]: True if GNAT is available, or error
        """
        if not self.validator:
            return Success(False)
        
        return self.validator.is_available()
    
    def process_content(
        self,
        content: str,
        file_path: Optional[Path] = None
    ) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
        """Process Ada content through the complete pipeline.
        
        Args:
            content: Ada source code to process
            file_path: Optional file path for context
            
        Returns:
            Result[PipelineResult, Error]: Pipeline result or error
        """
        return self._run_pipeline(content, file_path)
    
    def process_file(
        self,
        file_path: Union[str, Path]
    ) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
        """Process Ada file through the complete pipeline.
        
        Args:
            file_path: Path to Ada source file
            
        Returns:
            Result[PipelineResult, Error]: Pipeline result or error
        """
        path = Path(file_path)
        
        # Read file content
        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            return Failure(ParseError(
                path=path,
                line=0,
                column=0,
                message=f"Failed to read file: {e}"
            ))
        
        return self._run_pipeline(content, path)
    
    def _run_pipeline(
        self,
        content: str,
        file_path: Optional[Path]
    ) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
        """Run the complete validation pipeline.
        
        Args:
            content: Ada source code to process
            file_path: Optional file path for context
            
        Returns:
            Result[PipelineResult, Error]: Pipeline result or error
        """
        original_content = content
        
        # Stage 1: Parse the Ada content
        parse_result = self.parser.parse_content(content, file_path)
        
        if isinstance(parse_result, Failure):
            parse_error = parse_result.failure()
            return Failure(parse_error)
        
        parsed = parse_result.unwrap()
        
        # Stage 2: Apply formatting patterns
        formatting_result = self.formatter.process_content(content, file_path)
        
        if isinstance(formatting_result, Failure):
            formatting_error = formatting_result.failure()
            return Failure(formatting_error)
        
        formatted = formatting_result.unwrap()
        
        # Check if any formatting was applied
        formatting_applied = formatted.has_changes
        final_content = formatted.modified_content if formatting_applied else original_content
        
        # Stage 3: GNAT validation (if enabled and changes were made)
        validation_result = None
        validation_passed = True  # Default to passed if not validating
        
        if self.validate_with_gnat and self.validator and formatting_applied:
            gnat_result = self.validator.validate_content(
                final_content,
                file_path,
                self.ada_version
            )
            
            if isinstance(gnat_result, Failure):
                gnat_error = gnat_result.failure()
                return Failure(gnat_error)
            
            validation_result = gnat_result.unwrap()
            validation_passed = validation_result.valid
        
        # Build pipeline result
        pipeline_result = PipelineResult(
            success=True,
            original_content=original_content,
            formatted_content=final_content,
            formatting_applied=formatting_applied,
            validation_passed=validation_passed,
            parse_result=parsed,
            formatting_result=formatted,
            validation_result=validation_result,
            applied_patterns=formatted.applied_patterns
        )
        
        return Success(pipeline_result)
    
    async def process_content_async(
        self,
        content: str,
        file_path: Optional[Path] = None
    ) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
        """Asynchronously process Ada content through the pipeline.
        
        Args:
            content: Ada source code to process
            file_path: Optional file path for context
            
        Returns:
            Result[PipelineResult, Error]: Pipeline result or error
        """
        return await self._run_pipeline_async(content, file_path)
    
    async def _run_pipeline_async(
        self,
        content: str,
        file_path: Optional[Path]
    ) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
        """Run the complete validation pipeline asynchronously.
        
        Args:
            content: Ada source code to process
            file_path: Optional file path for context
            
        Returns:
            Result[PipelineResult, Error]: Pipeline result or error
        """
        original_content = content
        
        # Stage 1: Parse the Ada content (synchronous)
        parse_result = self.parser.parse_content(content, file_path)
        
        if isinstance(parse_result, Failure):
            return parse_result
        
        parsed = parse_result.unwrap()
        
        # Stage 2: Apply formatting patterns (synchronous)
        formatting_result = self.formatter.process_content(content, file_path)
        
        if isinstance(formatting_result, Failure):
            return formatting_result
        
        formatted = formatting_result.unwrap()
        
        # Check if any formatting was applied
        formatting_applied = formatted.has_changes
        final_content = formatted.modified_content if formatting_applied else original_content
        
        # Stage 3: GNAT validation (asynchronous if enabled and changes were made)
        validation_result = None
        validation_passed = True
        
        if self.validate_with_gnat and self.validator and formatting_applied:
            gnat_result = await self.validator.validate_content_async(
                final_content,
                file_path,
                self.ada_version
            )
            
            if isinstance(gnat_result, Failure):
                return gnat_result
            
            validation_result = gnat_result.unwrap()
            validation_passed = validation_result.valid
        
        # Build pipeline result
        pipeline_result = PipelineResult(
            success=True,
            original_content=original_content,
            formatted_content=final_content,
            formatting_applied=formatting_applied,
            validation_passed=validation_passed,
            parse_result=parsed,
            formatting_result=formatted,
            validation_result=validation_result,
            applied_patterns=formatted.applied_patterns
        )
        
        return Success(pipeline_result)
    
    def validate_patterns(self, patterns: Set[str]) -> Result[Set[str], PatternError]:
        """Validate that pattern names are supported.
        
        Args:
            patterns: Set of pattern names to validate
            
        Returns:
            Result[Set[str], PatternError]: Valid patterns or error
        """
        return self.formatter.validate_patterns(patterns)
    
    def get_available_patterns(self) -> Set[str]:
        """Get set of available pattern names."""
        return self.formatter.get_available_patterns()
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pipeline configuration.
        
        Returns:
            Dict[str, Any]: Pipeline statistics
        """
        stats = {
            'gnat_validation_enabled': self.validate_with_gnat,
            'ada_version': self.ada_version,
            'enabled_patterns': list(self.enabled_patterns) if self.enabled_patterns else None,
        }
        
        # Add formatter statistics
        stats.update(self.formatter.get_pattern_statistics())
        
        # Add GNAT availability
        if self.validator:
            gnat_available = self.validator.is_available()
            stats['gnat_available'] = isinstance(gnat_available, Success) and gnat_available.unwrap()
        else:
            stats['gnat_available'] = False
        
        return stats


# Convenience functions for common pipeline operations

def validate_and_format_content(
    content: str,
    file_path: Optional[Path] = None,
    enabled_patterns: Optional[Set[str]] = None,
    validate_with_gnat: bool = True
) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
    """Validate and format Ada content using default pipeline settings.
    
    Args:
        content: Ada source code to process
        file_path: Optional file path for context
        enabled_patterns: Optional set of patterns to enable
        validate_with_gnat: Whether to run GNAT validation
        
    Returns:
        Result[PipelineResult, Error]: Pipeline result or error
    """
    pipeline = ValidationPipeline(
        enabled_patterns=enabled_patterns,
        validate_with_gnat=validate_with_gnat
    )
    return pipeline.process_content(content, file_path)


def validate_and_format_file(
    file_path: Union[str, Path],
    enabled_patterns: Optional[Set[str]] = None,
    validate_with_gnat: bool = True
) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
    """Validate and format Ada file using default pipeline settings.
    
    Args:
        file_path: Path to Ada source file
        enabled_patterns: Optional set of patterns to enable
        validate_with_gnat: Whether to run GNAT validation
        
    Returns:
        Result[PipelineResult, Error]: Pipeline result or error
    """
    pipeline = ValidationPipeline(
        enabled_patterns=enabled_patterns,
        validate_with_gnat=validate_with_gnat
    )
    return pipeline.process_file(file_path)


async def validate_and_format_content_async(
    content: str,
    file_path: Optional[Path] = None,
    enabled_patterns: Optional[Set[str]] = None,
    validate_with_gnat: bool = True
) -> Result[PipelineResult, ParseError | PatternError | ValidationError]:
    """Asynchronously validate and format Ada content.
    
    Args:
        content: Ada source code to process
        file_path: Optional file path for context
        enabled_patterns: Optional set of patterns to enable
        validate_with_gnat: Whether to run GNAT validation
        
    Returns:
        Result[PipelineResult, Error]: Pipeline result or error
    """
    pipeline = ValidationPipeline(
        enabled_patterns=enabled_patterns,
        validate_with_gnat=validate_with_gnat
    )
    return await pipeline.process_content_async(content, file_path)