# Multi-Command Architecture Design

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Draft

This document outlines the architectural design for supporting multiple CLI commands (format, rename, extract, etc.) with shared ALS interaction patterns.

## Overview

The adafmt tool is evolving from a single-purpose formatter to a multi-command Ada development tool. This design leverages common patterns to minimize code duplication while maintaining flexibility for command-specific behavior.

## Core Design Patterns

### 1. Command Pattern with Template Method

We use the Command Pattern combined with Template Method to define the common flow:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Protocol

T = TypeVar('T')  # Result type
R = TypeVar('R')  # Request type

class CommandProcessor(ABC, Generic[T]):
    """Base processor for all CLI commands."""
    
    async def execute(self, args: CommandArgs) -> int:
        """Template method defining the common execution flow."""
        try:
            # 1. Setup phase
            await self.setup_environment(args)
            als_client = await self.initialize_als(args)
            
            # 2. Discovery phase
            targets = await self.discover_targets(args)
            
            # 3. Processing phase (command-specific)
            results = await self.process_targets(als_client, targets, args)
            
            # 4. Finalization phase
            return await self.finalize(results, args)
            
        except Exception as e:
            await self.handle_error(e)
            return 1
    
    async def setup_environment(self, args: CommandArgs) -> None:
        """Common environment setup."""
        setup_logging(args.verbose)
        redirect_stderr(args.quiet)
        setup_signal_handlers()
    
    async def initialize_als(self, args: CommandArgs) -> ALSClient:
        """Common ALS initialization."""
        return await ALSClient.create(args.als_command)
    
    @abstractmethod
    async def discover_targets(self, args: CommandArgs) -> list[Path]:
        """Discover files/symbols to process."""
        pass
    
    @abstractmethod
    async def process_targets(
        self, 
        als_client: ALSClient, 
        targets: list[Any], 
        args: CommandArgs
    ) -> list[T]:
        """Process targets - command-specific implementation."""
        pass
```

### 2. Strategy Pattern for LSP Operations

Define a protocol for LSP operations that can be plugged into the processor:

```python
class LSPOperation(Protocol[R, T]):
    """Protocol for LSP operations."""
    
    def prepare_request(self, target: Path, content: str) -> R:
        """Prepare LSP request for the target."""
        ...
    
    def process_response(self, response: dict) -> T:
        """Process LSP response into result type."""
        ...
    
    def apply_result(self, target: Path, result: T) -> bool:
        """Apply the result to the target."""
        ...

# Concrete implementations
class FormatOperation(LSPOperation[dict, str]):
    """LSP formatting operation."""
    
    def prepare_request(self, target: Path, content: str) -> dict:
        return {
            "method": "textDocument/formatting",
            "params": {
                "textDocument": {"uri": f"file://{target}"},
                "options": {"tabSize": 4, "insertSpaces": True}
            }
        }
    
    def process_response(self, response: dict) -> str:
        # Convert TextEdit[] to formatted string
        return apply_text_edits(response)

class RenameOperation(LSPOperation[dict, list[TextEdit]]):
    """LSP rename operation."""
    
    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
    
    def prepare_request(self, target: Path, content: str) -> dict:
        position = find_symbol_position(content, self.old_name)
        return {
            "method": "textDocument/rename",
            "params": {
                "textDocument": {"uri": f"file://{target}"},
                "position": position,
                "newName": self.new_name
            }
        }
```

### 3. Composition for Processing Pipelines

Use composition to build flexible processing pipelines:

```python
class ProcessingPipeline:
    """Composable processing pipeline."""
    
    def __init__(self):
        self.stages: list[ProcessingStage] = []
    
    def add_stage(self, stage: ProcessingStage) -> 'ProcessingPipeline':
        self.stages.append(stage)
        return self
    
    async def process(self, item: Any) -> Any:
        result = item
        for stage in self.stages:
            result = await stage.process(result)
        return result

class ProcessingStage(Protocol):
    """Protocol for pipeline stages."""
    
    async def process(self, item: Any) -> Any:
        ...

# Example stages
class ParseStage:
    """Parse Ada source for AST."""
    async def process(self, file_data: FileData) -> ParsedFile:
        ast = await parse_ada(file_data.content)
        return ParsedFile(file_data, ast)

class ValidateStage:
    """Validate operations against AST."""
    async def process(self, parsed: ParsedFile) -> ValidatedFile:
        # Use AST to validate operation safety
        return ValidatedFile(parsed, is_safe=True)

class LSPStage:
    """Execute LSP operation."""
    def __init__(self, als_client: ALSClient, operation: LSPOperation):
        self.als_client = als_client
        self.operation = operation
    
    async def process(self, validated: ValidatedFile) -> ProcessedFile:
        request = self.operation.prepare_request(validated.path, validated.content)
        response = await self.als_client.send_request(request)
        result = self.operation.process_response(response)
        return ProcessedFile(validated, result)

class PatternStage:
    """Apply post-processing patterns."""
    def __init__(self, patterns: list[Pattern], phase: str):
        self.patterns = patterns
        self.phase = phase
    
    async def process(self, processed: ProcessedFile) -> FormattedFile:
        content = processed.result
        for pattern in self.patterns:
            if pattern.phase == self.phase:
                content = pattern.apply(content, processed.ast)
        return FormattedFile(processed, content)
```

### 4. Factory Pattern for Command Creation

Use factories to create properly configured command processors:

```python
class CommandFactory:
    """Factory for creating command processors."""
    
    @staticmethod
    def create_format_command(config: Config) -> CommandProcessor:
        """Create format command with full pipeline."""
        pipeline = ProcessingPipeline()
        
        if config.use_parser:
            pipeline.add_stage(ParseStage())
            
            if config.pre_als_patterns:
                pipeline.add_stage(PatternStage(
                    patterns=config.pre_als_patterns,
                    phase="pre-als"
                ))
        
        pipeline.add_stage(LSPStage(
            als_client=None,  # Injected later
            operation=FormatOperation()
        ))
        
        if config.post_als_patterns:
            pipeline.add_stage(PatternStage(
                patterns=config.post_als_patterns,
                phase="post-als"
            ))
        
        if config.validate_with_gnat:
            pipeline.add_stage(GNATValidationStage())
        
        return FormatCommand(pipeline)
    
    @staticmethod
    def create_rename_command(
        old_name: str, 
        new_name: str,
        config: Config
    ) -> CommandProcessor:
        """Create rename command."""
        pipeline = ProcessingPipeline()
        
        # Parse to understand scope
        pipeline.add_stage(ParseStage())
        pipeline.add_stage(ValidateStage())
        
        # Perform rename
        pipeline.add_stage(LSPStage(
            als_client=None,
            operation=RenameOperation(old_name, new_name)
        ))
        
        # Validate result compiles
        if config.validate_with_gnat:
            pipeline.add_stage(GNATValidationStage())
        
        return RenameCommand(pipeline)
```

## Concrete Command Implementations

### Format Command

```python
class FormatCommand(CommandProcessor[FormattedFile]):
    """Format Ada source files."""
    
    def __init__(self, pipeline: ProcessingPipeline):
        self.pipeline = pipeline
    
    async def discover_targets(self, args: FormatArgs) -> list[Path]:
        """Discover Ada files to format."""
        return await discover_ada_files(
            args.files,
            recursive=args.recursive,
            ignore=args.ignore
        )
    
    async def process_targets(
        self,
        als_client: ALSClient,
        targets: list[Path],
        args: FormatArgs
    ) -> list[FormattedFile]:
        """Process files through formatting pipeline."""
        # Inject ALS client into pipeline
        self.pipeline.set_als_client(als_client)
        
        # Process with worker pool
        async with WorkerPool(num_workers=args.num_workers) as pool:
            return await pool.process_all(
                targets,
                lambda path: self.pipeline.process(FileData.from_path(path))
            )
```

### Rename Command

```python
class RenameCommand(CommandProcessor[RenameResult]):
    """Rename Ada symbols across project."""
    
    async def discover_targets(self, args: RenameArgs) -> list[Path]:
        """Discover files containing the symbol."""
        all_files = await discover_ada_files(args.project_root)
        
        # Use grep or parser to find files with symbol
        return await find_files_with_symbol(
            all_files,
            args.old_name,
            use_parser=args.use_parser
        )
```

## Benefits of This Architecture

### 1. **Type Safety with Generics**
- Commands are generic over their result type
- Type-safe throughout the pipeline
- Clear contracts between components

### 2. **Flexibility through Composition**
- Pipelines can be composed differently per command
- Easy to add/remove stages
- Testable individual stages

### 3. **Code Reuse**
- Common flow in base class
- Shared stages across commands
- Consistent error handling

### 4. **Extensibility**
- New commands just implement abstract methods
- New stages implement ProcessingStage protocol
- New LSP operations implement LSPOperation protocol

### 5. **Testability**
- Mock individual stages
- Test pipelines in isolation
- Test command logic separately

## Implementation Plan

1. **Phase 1**: Extract common base classes
   - Create CommandProcessor base class
   - Extract common setup/teardown logic
   - Maintain backward compatibility

2. **Phase 2**: Implement pipeline architecture
   - Create ProcessingPipeline and stages
   - Refactor format command to use pipeline
   - Add parser integration stages

3. **Phase 3**: Add new commands
   - Implement rename command
   - Implement extract command
   - Share pipeline stages

4. **Phase 4**: Optimize and refine
   - Performance tuning
   - Add caching where beneficial
   - Refine abstractions based on usage

## Example Usage

```python
# Format command
async def format_main(args: FormatArgs) -> int:
    config = load_config(args.config_file)
    command = CommandFactory.create_format_command(config)
    return await command.execute(args)

# Rename command
async def rename_main(args: RenameArgs) -> int:
    config = load_config(args.config_file)
    command = CommandFactory.create_rename_command(
        args.old_name,
        args.new_name,
        config
    )
    return await command.execute(args)
```

## Conclusion

This architecture provides:
- Clear separation of concerns
- Maximum code reuse
- Type safety through generics
- Flexibility through composition
- Easy extension for new commands

The design follows SOLID principles and established patterns while maintaining the simplicity needed for a CLI tool.