# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Type-safe formatting rules model using Pydantic.

This module defines the structure for formatting rules configuration,
providing type safety and automatic JSON validation.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class SpacingParameters(BaseModel):
    """Common spacing parameters for operators and symbols."""
    spaces_before: int = Field(1, ge=0, description="Spaces before the operator")
    spaces_after: int = Field(1, ge=0, description="Spaces after the operator")


class BinaryOperatorParameters(SpacingParameters):
    """Parameters for binary operators with operator list."""
    operators: list[str] = Field(["+", "-", "*", "/"], description="Operators to apply spacing to")


class CommentParameters(BaseModel):
    """Parameters for comment spacing rules."""
    min_spaces_after: int = Field(1, ge=0, description="Minimum spaces after --")
    preserve_alignment: bool = Field(True, description="Preserve existing comment alignment")


class EndOfLineCommentParameters(BaseModel):
    """Parameters for end-of-line comment spacing."""
    min_spaces_before: int = Field(2, ge=0, description="Minimum spaces before end-of-line comment")


class TrailingWhitespaceParameters(BaseModel):
    """Parameters for trailing whitespace removal (empty for now)."""
    pass


class FinalNewlineParameters(BaseModel):
    """Parameters for final newline handling."""
    newline_count: int = Field(1, ge=0, description="Number of newlines at end of file")


class RuleConfig(BaseModel):
    """Base configuration for a formatting rule."""
    enabled: bool = Field(True, description="Whether this rule is enabled")
    description: str = Field("", description="Human-readable rule description")


class SpacingRule(RuleConfig):
    """Configuration for spacing rules."""
    parameters: SpacingParameters = Field(default_factory=SpacingParameters)


class BinaryOperatorRule(RuleConfig):
    """Configuration for binary operator spacing."""
    parameters: BinaryOperatorParameters = Field(default_factory=BinaryOperatorParameters)


class CommentRule(RuleConfig):
    """Configuration for comment rules."""
    parameters: CommentParameters = Field(default_factory=CommentParameters)


class EndOfLineCommentRule(RuleConfig):
    """Configuration for end-of-line comment rules."""
    parameters: EndOfLineCommentParameters = Field(default_factory=EndOfLineCommentParameters)


class TrailingWhitespaceRule(RuleConfig):
    """Configuration for trailing whitespace rule."""
    parameters: TrailingWhitespaceParameters = Field(default_factory=TrailingWhitespaceParameters)


class FinalNewlineRule(RuleConfig):
    """Configuration for final newline rule."""
    parameters: FinalNewlineParameters = Field(default_factory=FinalNewlineParameters)


class SpacingRules(BaseModel):
    """All spacing-related formatting rules."""
    assignment: SpacingRule = Field(default_factory=SpacingRule)
    type_declaration: SpacingRule = Field(default_factory=SpacingRule)
    parameter_association: SpacingRule = Field(default_factory=SpacingRule)
    range_operator: SpacingRule = Field(default_factory=SpacingRule)
    binary_operators: BinaryOperatorRule = Field(default_factory=BinaryOperatorRule)


class CommentRules(BaseModel):
    """All comment-related formatting rules."""
    inline: CommentRule = Field(default_factory=CommentRule)
    end_of_line: EndOfLineCommentRule = Field(default_factory=EndOfLineCommentRule)


class LineFormattingRules(BaseModel):
    """All line formatting rules."""
    trailing_whitespace: TrailingWhitespaceRule = Field(default_factory=TrailingWhitespaceRule)
    final_newline: FinalNewlineRule = Field(default_factory=FinalNewlineRule)


class FormattingRules(BaseModel):
    """Root configuration for all formatting rules."""
    spacing: SpacingRules = Field(default_factory=SpacingRules)
    comments: CommentRules = Field(default_factory=CommentRules)
    line_formatting: LineFormattingRules = Field(default_factory=LineFormattingRules)
    
    @classmethod
    def load(cls, path: Path) -> "FormattingRules":
        """Load formatting rules from JSON file.
        
        Args:
            path: Path to JSON configuration file
            
        Returns:
            FormattingRules: Validated rules configuration
            
        Raises:
            ValidationError: If JSON doesn't match schema
            FileNotFoundError: If file doesn't exist
        """
        if not path.exists():
            # Return default rules if file doesn't exist
            return cls()
        
        # Pydantic will validate the JSON structure
        return cls.parse_file(path)
    
    @classmethod
    def load_from_path_or_default(cls, path: Optional[Path], default_filename: str = "adafmt_format_rules.json") -> "FormattingRules":
        """Load rules from specified path or look for default file.
        
        Args:
            path: Optional path to rules file
            default_filename: Default filename to look for in current directory
            
        Returns:
            FormattingRules: Loaded or default rules
        """
        if path:
            return cls.load(path)
        
        # Look for default file in current directory
        default_path = Path(default_filename)
        if default_path.exists():
            return cls.load(default_path)
        
        # Return default rules
        return cls()