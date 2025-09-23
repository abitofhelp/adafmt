# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Tests for parser wrapper functionality.

These tests verify the parser wrapper integrates correctly with the 
Ada 2022 ANTLR parser and handles errors appropriately.
"""

import pytest
from pathlib import Path
from returns.result import Failure, Success

from adafmt.parser_wrapper import (
    AdaParserWrapper,
    parse_ada_content,
    validate_ada_syntax
)
from adafmt.errors import ParseError


class TestAdaParserWrapper:
    """Test the Ada parser wrapper."""
    
    def test_initialization(self):
        """Test parser wrapper can be initialized."""
        parser = AdaParserWrapper()
        assert parser is not None
        assert not parser._initialized
    
    def test_empty_content(self):
        """Test parsing empty content."""
        parser = AdaParserWrapper()
        result = parser.parse_content("", Path("test.adb"))
        
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ParseError)
        assert "Empty or whitespace-only content" in error.message
    
    def test_whitespace_only_content(self):
        """Test parsing whitespace-only content."""
        parser = AdaParserWrapper()
        result = parser.parse_content("   \n\t  \n  ", Path("test.adb"))
        
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ParseError)
        assert "Empty or whitespace-only content" in error.message
    
    @pytest.mark.skipif(
        condition=True,  # Skip until ada2022_parser is available
        reason="ada2022_parser package not available in test environment"
    )
    def test_simple_ada_content(self):
        """Test parsing simple Ada content."""
        ada_code = """
        procedure Hello is
        begin
           null;
        end Hello;
        """
        
        parser = AdaParserWrapper()
        result = parser.parse_content(ada_code, Path("hello.adb"))
        
        assert isinstance(result, Success)
        parse_result = result.unwrap()
        
        assert parse_result.content == ada_code
        assert len(parse_result.source_lines) > 0
        assert parse_result.path == Path("hello.adb")
        assert parse_result.ast is not None
    
    @pytest.mark.skipif(
        condition=True,  # Skip until ada2022_parser is available  
        reason="ada2022_parser package not available in test environment"
    )
    def test_invalid_ada_syntax(self):
        """Test parsing invalid Ada syntax."""
        invalid_code = """
        procedure Hello is
        begin
           invalid syntax here +++
        end Hello;
        """
        
        parser = AdaParserWrapper()
        result = parser.parse_content(invalid_code, Path("invalid.adb"))
        
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ParseError)
        assert error.path == Path("invalid.adb")
    
    def test_convenience_functions(self):
        """Test convenience functions work."""
        # Test with empty content (should fail gracefully)
        result = parse_ada_content("", Path("test.adb"))
        assert isinstance(result, Failure)
        
        result = validate_ada_syntax("", Path("test.adb"))
        assert isinstance(result, Failure)
    
    def test_parse_result_properties(self):
        """Test ParseResult properties."""
        from adafmt.parser_wrapper import ParseResult
        
        # Create a test parse result
        source_lines = ["-- Comment", "procedure Test is", "begin", "   null;", "end Test;"]
        parse_result = ParseResult(
            ast=None,  # Would be actual AST in real usage
            source_lines=source_lines,
            path=Path("test.adb"),
            content="\n".join(source_lines)
        )
        
        assert parse_result.line_count == 5
        assert not parse_result.has_preprocessing  # No # directives
        
        # Test with preprocessing
        source_with_preprocessing = ["#if DEBUG", "-- Debug code", "#endif", "procedure Test is"]
        parse_result_with_pp = ParseResult(
            ast=None,
            source_lines=source_with_preprocessing,
            path=Path("test.adb"),
            content="\n".join(source_with_preprocessing)
        )
        
        assert parse_result_with_pp.has_preprocessing