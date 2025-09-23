# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Parser wrapper for Ada 2022 ANTLR parser integration.

This module provides a functional interface to the Ada 2022 ANTLR parser,
using Result types for comprehensive error handling. The parser wrapper
supports both content parsing and file parsing with proper error context.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Union

from returns.io import IOFailure, impure_safe
from returns.result import Failure, Result, Success

from .errors import FileError, ParseError
from .file_ops import read_text


@dataclass(frozen=True)
class ParseResult:
    """Result of successfully parsing Ada source code.
    
    Attributes:
        ast: The ANTLR parse tree root node
        source_lines: Original source lines for reference
        path: Path to the source file (if parsed from file)
        content: Original content string
    """
    ast: Any  # ANTLR parse tree node
    source_lines: List[str]
    path: Optional[Path]
    content: str
    
    @property
    def line_count(self) -> int:
        """Get the number of lines in the source."""
        return len(self.source_lines)
    
    @property
    def has_preprocessing(self) -> bool:
        """Check if source contains preprocessing directives."""
        return any(line.strip().startswith('#') for line in self.source_lines)


class AdaParserWrapper:
    """Wrapper around Ada 2022 ANTLR parser with functional error handling.
    
    This class provides a clean interface to the Ada 2022 parser while
    ensuring all errors are properly captured and typed. It follows the
    dependency inversion principle by abstracting the parser implementation.
    """
    
    def __init__(self):
        """Initialize the parser wrapper.
        
        Note:
            The actual parser is loaded lazily to avoid import errors
            if ada2022_parser is not available.
        """
        self._parser = None
        self._lexer = None
        self._initialized = False
    
    def _ensure_initialized(self) -> Result[None, ParseError]:
        """Ensure parser components are initialized.
        
        Returns:
            Result[None, ParseError]: Success or initialization error
        """
        if self._initialized:
            return Success(None)
        
        try:
            # Import ada2022_parser components
            # Note: This assumes ada2022_parser follows standard ANTLR patterns
            from ada2022_parser import Ada2022Lexer, Ada2022Parser  # type: ignore[attr-defined]
            from antlr4 import CommonTokenStream, InputStream
            
            # Store classes for later use
            self._lexer_class = Ada2022Lexer
            self._parser_class = Ada2022Parser
            self._token_stream_class = CommonTokenStream
            self._input_stream_class = InputStream
            self._initialized = True
            
            return Success(None)
            
        except ImportError as e:
            return Failure(ParseError(
                path=Path(""),
                line=0,
                column=0,
                message=f"Ada parser not available: {e}. Install ada2022_parser package."
            ))
        except Exception as e:
            return Failure(ParseError(
                path=Path(""),
                line=0,
                column=0,
                message=f"Failed to initialize parser: {e}"
            ))
    
    @impure_safe
    def _parse_content_internal(self, content: str) -> Any:
        """Internal content parsing with automatic exception handling.
        
        Args:
            content: Ada source code to parse
            
        Returns:
            Any: ANTLR parse tree root node
            
        Note:
            @impure_safe automatically converts exceptions to IOResult[Any, Exception]
        """
        # Create input stream
        input_stream = self._input_stream_class(content)
        
        # Create lexer
        lexer = self._lexer_class(input_stream)
        
        # Create token stream
        tokens = self._token_stream_class(lexer)
        
        # Create parser
        parser = self._parser_class(tokens)
        
        # Parse from compilation unit (standard Ada entry point)
        # Note: Adjust method name based on actual ada2022_parser grammar
        return parser.compilation_unit()
    
    def parse_content(self, content: str, path: Optional[Path] = None) -> Result[ParseResult, ParseError]:
        """Parse Ada source content with comprehensive error handling.
        
        Args:
            content: Ada source code to parse
            path: Optional path for error context
            
        Returns:
            Result[ParseResult, ParseError]: Parsed result or specific error
        """
        # Ensure parser is initialized
        init_result = self._ensure_initialized()
        if isinstance(init_result, Failure):
            return init_result
        
        # Validate input
        if not content.strip():
            return Failure(ParseError(
                path=path or Path(""),
                line=0,
                column=0,
                message="Empty or whitespace-only content cannot be parsed"
            ))
        
        # Parse content with error mapping
        parse_result = self._parse_content_internal(content)
        
        if isinstance(parse_result, Failure):
            exc = parse_result.failure()
            return Failure(self._map_parse_error(exc, path or Path("")))
        
        ast = parse_result.unwrap()
        source_lines = content.splitlines()
        
        return Success(ParseResult(
            ast=ast,
            source_lines=source_lines,
            path=path,
            content=content
        ))
    
    def parse_file(self, file_path: Union[str, Path]) -> Result[ParseResult, ParseError | FileError]:
        """Parse Ada file with comprehensive error handling.
        
        Args:
            file_path: Path to Ada source file
            
        Returns:
            Result[ParseResult, ParseError | FileError]: Parsed result or specific error
        """
        path = Path(file_path)
        
        # Read file content
        content_result = read_text(path, encoding="utf-8", errors="ignore")
        
        if isinstance(content_result, IOFailure):
            # File operation failed - extract FileError and wrap in regular Failure
            error = content_result.failure()
            if isinstance(error, FileError):
                return Failure(error)
            else:
                # Shouldn't happen given read_text implementation
                return Failure(FileError(
                    message=str(error),
                    path=path,
                    operation="read",
                    not_found=isinstance(error, FileNotFoundError)
                ))
        
        content = content_result.unwrap()  # type: ignore[assignment]
        
        # Parse content
        return self.parse_content(content, path)  # type: ignore[arg-type]
    
    def _map_parse_error(self, exc: Exception, path: Path) -> ParseError:
        """Map generic exception to ParseError with context.
        
        Args:
            exc: Original exception from parser
            path: File path for context
            
        Returns:
            ParseError: Mapped error with full context
        """
        # Extract location information if available
        line = getattr(exc, 'line', 0)
        column = getattr(exc, 'column', 0)
        
        # Handle specific ANTLR exception types
        if hasattr(exc, 'msg'):
            message = str(exc.msg)
        else:
            message = str(exc)
        
        # Add context for common parse errors
        if "mismatched input" in message.lower():
            message = f"Syntax error: {message}"
        elif "no viable alternative" in message.lower():
            message = f"Invalid syntax: {message}"
        elif "missing" in message.lower():
            message = f"Missing token: {message}"
        
        return ParseError(
            path=path,
            line=line,
            column=column,
            message=message
        )
    
    def validate_syntax(self, content: str, path: Optional[Path] = None) -> Result[bool, ParseError]:
        """Validate Ada syntax without building full AST.
        
        Args:
            content: Ada source code to validate
            path: Optional path for error context
            
        Returns:
            Result[bool, ParseError]: True if valid, or parse error
        """
        parse_result = self.parse_content(content, path)
        
        if isinstance(parse_result, Failure):
            return parse_result
        
        # If parsing succeeded, syntax is valid
        return Success(True)
    
    def validate_file(self, file_path: Union[str, Path]) -> Result[bool, ParseError | FileError]:
        """Validate Ada file syntax.
        
        Args:
            file_path: Path to Ada source file
            
        Returns:
            Result[bool, ParseError | FileError]: True if valid, or specific error
        """
        parse_result = self.parse_file(file_path)
        
        if isinstance(parse_result, Failure):
            return parse_result
        
        return Success(True)


# Convenience functions for common operations

def parse_ada_content(content: str, path: Optional[Path] = None) -> Result[ParseResult, ParseError]:
    """Parse Ada content using default parser instance.
    
    Args:
        content: Ada source code to parse
        path: Optional path for error context
        
    Returns:
        Result[ParseResult, ParseError]: Parsed result or specific error
    """
    parser = AdaParserWrapper()
    return parser.parse_content(content, path)


def parse_ada_file(file_path: Union[str, Path]) -> Result[ParseResult, ParseError | FileError]:
    """Parse Ada file using default parser instance.
    
    Args:
        file_path: Path to Ada source file
        
    Returns:
        Result[ParseResult, ParseError | FileError]: Parsed result or specific error
    """
    parser = AdaParserWrapper()
    return parser.parse_file(file_path)


def validate_ada_syntax(content: str, path: Optional[Path] = None) -> Result[bool, ParseError]:
    """Validate Ada syntax using default parser instance.
    
    Args:
        content: Ada source code to validate
        path: Optional path for error context
        
    Returns:
        Result[bool, ParseError]: True if valid, or parse error
    """
    parser = AdaParserWrapper()
    return parser.validate_syntax(content, path)


def validate_ada_file(file_path: Union[str, Path]) -> Result[bool, ParseError | FileError]:
    """Validate Ada file syntax using default parser instance.
    
    Args:
        file_path: Path to Ada source file
        
    Returns:
        Result[bool, ParseError | FileError]: True if valid, or specific error
    """
    parser = AdaParserWrapper()
    return parser.validate_file(file_path)