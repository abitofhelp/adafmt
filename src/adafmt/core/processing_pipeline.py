# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Processing pipeline with composable stages.

This module provides a flexible pipeline architecture for processing
files through multiple stages (parsing, validation, LSP operations, etc.).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar

from returns.result import Failure

try:
    from ada2022_parser import Parser as AdaParser  # type: ignore[import-not-found]
except ImportError:
    AdaParser = None  # type: ignore[misc,assignment]  # Parser is optional

from ..als_client import ALSClient

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class FileData:
    """Base data for file processing."""
    path: Path
    content: str
    encoding: str = "utf-8"
    
    @classmethod
    def from_path(cls, path: Path, encoding: str = "utf-8") -> 'FileData':
        """Load file data from path."""
        content = path.read_text(encoding=encoding)
        return cls(path=path, content=content, encoding=encoding)


@dataclass
class ParsedFile(FileData):
    """File with parsed AST."""
    ast: dict[str, Any] | None = None
    parse_errors: list[str] | None = None
    
    def __post_init__(self):
        if self.parse_errors is None:
            self.parse_errors = []
        if self.ast is None:
            self.ast = {}


@dataclass  
class ValidatedFile(ParsedFile):
    """File with validation results."""
    is_safe: bool = True
    validation_messages: list[str] | None = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.validation_messages is None:
            self.validation_messages = []


@dataclass
class ProcessedFile(ValidatedFile):
    """File after LSP processing."""
    lsp_result: Any = None
    lsp_success: bool = True


@dataclass
class FormattedFile(ProcessedFile):
    """File after formatting/pattern application."""
    final_content: str = ""
    patterns_applied: list[str] | None = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.patterns_applied is None:
            self.patterns_applied = []


class ProcessingStage(Protocol):
    """Protocol for pipeline stages."""
    
    async def process(self, item: Any) -> Any:
        """Process an item and return the result."""
        ...


class ProcessingPipeline:
    """
    Composable processing pipeline.
    
    Stages are executed in order, with each stage receiving
    the output of the previous stage.
    """
    
    def __init__(self):
        self.stages: list[ProcessingStage] = []
        self._als_client: ALSClient | None = None
    
    def add_stage(self, stage: ProcessingStage) -> 'ProcessingPipeline':
        """
        Add a stage to the pipeline.
        
        Args:
            stage: Processing stage to add
            
        Returns:
            Self for method chaining
        """
        self.stages.append(stage)
        return self
    
    def set_als_client(self, client: ALSClient) -> None:
        """
        Set ALS client for stages that need it.
        
        Args:
            client: ALS client instance
        """
        self._als_client = client
        # Inject into stages that need it
        for stage in self.stages:
            if isinstance(stage, LSPStage):
                stage.als_client = client
    
    async def process(self, item: Any) -> Any:
        """
        Process an item through all stages.
        
        Args:
            item: Item to process
            
        Returns:
            Final processed result
        """
        result = item
        for stage in self.stages:
            result = await stage.process(result)
        return result


class ParseStage:
    """Parse Ada source code to AST."""
    
    def __init__(self, parser: AdaParser | None = None):
        self.parser = parser or AdaParser()
    
    async def process(self, file_data: FileData) -> ParsedFile:
        """Parse file content to AST."""
        try:
            # Parse the Ada source
            ast = self.parser.parse(file_data.content)
            # Handle the parsed AST
            if hasattr(ast, 'to_dict'):
                parsed_ast = ast.to_dict()
            elif isinstance(ast, dict):
                parsed_ast = ast
            else:
                parsed_ast = {"root": str(ast)}  # Fallback for unknown types
                
            return ParsedFile(
                path=file_data.path,
                content=file_data.content,
                encoding=file_data.encoding,
                ast=parsed_ast,
                parse_errors=[]
            )
        except Exception as e:
            # Return with parse errors
            return ParsedFile(
                path=file_data.path,
                content=file_data.content,
                encoding=file_data.encoding,
                ast={},
                parse_errors=[str(e)]
            )


class ValidateStage:
    """Validate operations are safe to perform."""
    
    def __init__(self, validators: list[Any] | None = None):
        self.validators = validators or []
    
    async def process(self, parsed: ParsedFile) -> ValidatedFile:
        """Validate the parsed file."""
        messages = []
        is_safe = True
        
        # Run all validators
        for validator in self.validators:
            result = await validator.validate(parsed)
            if not result.is_valid:
                is_safe = False
                messages.extend(result.messages)
        
        return ValidatedFile(
            path=parsed.path,
            content=parsed.content,
            encoding=parsed.encoding,
            ast=parsed.ast,
            parse_errors=parsed.parse_errors,
            is_safe=is_safe,
            validation_messages=messages
        )


class LSPStage:
    """Execute LSP operation via ALS."""
    
    def __init__(self, operation: 'LSPOperation', als_client: ALSClient | None = None):
        self.operation = operation
        self.als_client = als_client
    
    async def process(self, validated: ValidatedFile) -> ProcessedFile:
        """Execute LSP operation."""
        if not self.als_client:
            raise RuntimeError("ALS client not set")
        
        if not validated.is_safe:
            # Skip unsafe operations
            return ProcessedFile(
                **validated.__dict__,
                lsp_result=None,
                lsp_success=False
            )
        
        try:
            # Prepare and send request
            request = self.operation.prepare_request(validated.path, validated.content)
            # Use the request_with_timeout method instead of send_request
            response_result = await self.als_client.request_with_timeout({
                "method": request["method"],
                "params": request["params"]
            }, timeout=60.0)  # Default 60 second timeout
            
            if isinstance(response_result, Failure):
                raise RuntimeError(f"ALS request failed: {response_result.failure()}")
                
            response = response_result.unwrap()
            
            # Process response
            result = self.operation.process_response(response)
            
            return ProcessedFile(
                **validated.__dict__,
                lsp_result=result,
                lsp_success=True
            )
        except Exception as e:
            return ProcessedFile(
                **validated.__dict__,
                lsp_result=str(e),
                lsp_success=False
            )


class PatternStage:
    """Apply formatting patterns."""
    
    def __init__(self, patterns: list[Any], phase: str):
        self.patterns = patterns
        self.phase = phase
    
    async def process(self, processed: ProcessedFile) -> FormattedFile:
        """Apply patterns to content."""
        # Start with LSP result or original content
        if processed.lsp_success and isinstance(processed.lsp_result, str):
            content = processed.lsp_result
        else:
            content = processed.content
        
        patterns_applied = []
        
        # Apply each pattern
        for pattern in self.patterns:
            if hasattr(pattern, 'phase') and pattern.phase == self.phase:
                # Parser-aware pattern application
                if processed.ast:
                    content = await self._apply_pattern_with_ast(
                        content, pattern, processed.ast
                    )
                else:
                    # Fallback to regex
                    content = pattern.apply(content)
                
                patterns_applied.append(pattern.name)
        
        return FormattedFile(
            **processed.__dict__,
            final_content=content,
            patterns_applied=patterns_applied
        )
    
    async def _apply_pattern_with_ast(
        self, 
        content: str, 
        pattern: Any, 
        ast: dict[str, Any]
    ) -> str:
        """Apply pattern with AST awareness."""
        # This would use the visitor pattern to safely apply transformations
        # For now, return as-is
        return pattern.apply_with_ast(content, ast) if hasattr(pattern, 'apply_with_ast') else content


class GNATValidationStage:
    """Validate result with GNAT compiler."""
    
    def __init__(self, gnat_command: list[str] | None = None):
        self.gnat_command = gnat_command or ["gcc", "-c", "-gnatc"]
    
    async def process(self, formatted: FormattedFile) -> FormattedFile:
        """Validate with GNAT."""
        # Would implement GNAT validation here
        # For now, pass through
        return formatted


# LSP Operation Protocol and implementations

class LSPOperation(Protocol):
    """Protocol for LSP operations."""
    
    def prepare_request(self, target: Path, content: str) -> dict:
        """Prepare LSP request."""
        ...
    
    def process_response(self, response: dict | list) -> Any:
        """Process LSP response."""
        ...


class FormatOperation:
    """LSP formatting operation."""
    
    def __init__(self, options: dict[str, Any] | None = None):
        self.options = options or {
            "tabSize": 3,
            "insertSpaces": True,
            "trimTrailingWhitespace": True
        }
    
    def prepare_request(self, target: Path, content: str) -> dict:
        """Prepare formatting request."""
        return {
            "method": "textDocument/formatting",
            "params": {
                "textDocument": {
                    "uri": f"file://{target.absolute()}"
                },
                "options": self.options
            }
        }
    
    def process_response(self, response: dict | list) -> str:
        """Process formatting response to formatted text."""
        # ALS returns TextEdit[] for formatting
        # This would apply the edits to produce formatted content
        # Simplified for example
        if isinstance(response, list) and response:
            # Apply text edits
            return response[0].get("newText", "")
        return ""


class RenameOperation:
    """LSP rename operation."""
    
    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
    
    def prepare_request(self, target: Path, content: str) -> dict:
        """Prepare rename request."""
        # Would find position of old_name in content
        line, character = self._find_position(content, self.old_name)
        
        return {
            "method": "textDocument/rename",
            "params": {
                "textDocument": {
                    "uri": f"file://{target.absolute()}"
                },
                "position": {
                    "line": line,
                    "character": character
                },
                "newName": self.new_name
            }
        }
    
    def process_response(self, response: dict | list) -> Any:
        """Process rename response."""
        # Returns WorkspaceEdit with changes across files
        return response
    
    def _find_position(self, content: str, name: str) -> tuple[int, int]:
        """Find line and character position of name."""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if name in line:
                return i, line.index(name)
        return 0, 0