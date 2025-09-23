# Modern Architecture Design (No Backward Compatibility)

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Draft

This document presents a modern, clean-slate architecture design for adafmt without backward compatibility constraints.

## Key Changes from Current Architecture

### 1. Unified Tool Approach

Instead of `adafmt` as a formatter with additional commands, create `adatool` as a comprehensive Ada development tool:

```bash
# Instead of:
adafmt format file.adb
adafmt rename old_name new_name

# We have:
adatool format file.adb
adatool rename old_name new_name
adatool extract function_name
adatool inline procedure_name
adatool check file.adb
```

### 2. Pure Async Architecture

Everything is async from the ground up:

```python
# No more sync/async split
async def main() -> None:
    async with AdaTool() as tool:
        await tool.run()

if __name__ == "__main__":
    # Use uvloop for performance
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())
```

### 3. Plugin-Based Command System

Commands are plugins that are automatically discovered:

```python
from typing import Protocol

class Command(Protocol):
    """Protocol for command plugins."""
    
    name: str
    description: str
    
    async def configure_parser(self, parser: ArgumentParser) -> None:
        """Add command-specific arguments."""
        ...
    
    async def execute(self, context: CommandContext) -> Result[Any]:
        """Execute the command."""
        ...

# Commands are discovered via entry points or filesystem
@register_command
class FormatCommand:
    name = "format"
    description = "Format Ada source files"
    
    async def execute(self, context: CommandContext) -> Result[FormattedFiles]:
        # Implementation
        pass
```

### 4. Unified Configuration System

Single configuration system using Pydantic models:

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class FormatConfig(BaseModel):
    """Format command configuration."""
    
    use_tabs: bool = False
    tab_width: int = 3
    line_length: int = 120
    
    class Config:
        json_schema_extra = {
            "example": {
                "use_tabs": False,
                "tab_width": 3,
                "line_length": 120
            }
        }

class AdaToolConfig(BaseSettings):
    """Global tool configuration."""
    
    # ALS settings
    als_command: list[str] = Field(
        default=["ada_language_server"],
        description="Command to start ALS"
    )
    als_timeout: float = Field(
        default=30.0,
        description="ALS startup timeout"
    )
    
    # Parser settings
    use_parser: bool = Field(
        default=True,
        description="Use Ada parser for analysis"
    )
    
    # Performance settings
    workers: int = Field(
        default=4,
        description="Number of worker processes"
    )
    use_uvloop: bool = Field(
        default=True,
        description="Use uvloop for better performance"
    )
    
    # Command configs
    format: FormatConfig = Field(default_factory=FormatConfig)
    
    class Config:
        env_prefix = "ADATOOL_"
        env_file = ".adatool.env"
        env_file_encoding = "utf-8"
```

### 5. Dependency Injection Container

Use a DI container for clean dependency management:

```python
from typing import AsyncContextManager
import inject

class ServiceContainer:
    """Service container with dependency injection."""
    
    def __init__(self, config: AdaToolConfig):
        self.config = config
        self._services: dict[type, Any] = {}
    
    async def __aenter__(self) -> 'ServiceContainer':
        # Configure injection
        inject.configure(self._configure_injection)
        
        # Initialize services
        self._services[ALSClient] = await self._create_als_client()
        self._services[AdaParser] = await self._create_parser()
        self._services[PatternEngine] = await self._create_pattern_engine()
        
        return self
    
    async def __aexit__(self, *args) -> None:
        # Cleanup services
        for service in self._services.values():
            if hasattr(service, 'close'):
                await service.close()
    
    def _configure_injection(self, binder: inject.Binder) -> None:
        for service_type, instance in self._services.items():
            binder.bind(service_type, instance)
    
    @inject.autoparams()
    def get[T](self, service_type: type[T]) -> T:
        """Get a service instance."""
        return self._services[service_type]
```

### 6. Simplified Pipeline Architecture

Use Python 3.13's new features and type system:

```python
from typing import Protocol, TypeVar, ParamSpec
from collections.abc import AsyncIterator

P = ParamSpec('P')
T = TypeVar('T')
R = TypeVar('R')

class Stage[T, R](Protocol):
    """Protocol for pipeline stages."""
    
    async def process(self, item: T) -> R:
        """Process an item."""
        ...

class Pipeline[T, R]:
    """Type-safe async pipeline."""
    
    def __init__(self, *stages: Stage[Any, Any]):
        self.stages = stages
    
    async def process(self, item: T) -> R:
        """Process item through all stages."""
        result = item
        for stage in self.stages:
            result = await stage.process(result)
        return result
    
    async def process_stream(
        self, 
        items: AsyncIterator[T]
    ) -> AsyncIterator[R]:
        """Process a stream of items."""
        async for item in items:
            yield await self.process(item)

# Usage with new pattern matching
class FormatStage:
    async def process(self, file: AdaFile) -> AdaFile:
        match file.status:
            case FileStatus.PARSED:
                return await self._format_parsed(file)
            case FileStatus.RAW:
                return await self._format_raw(file)
            case _:
                raise ValueError(f"Invalid status: {file.status}")
```

### 7. Event-Driven Architecture

Use events for loose coupling:

```python
from dataclasses import dataclass
from typing import AsyncContextManager
import asyncio

@dataclass
class Event:
    """Base event class."""
    timestamp: float = field(default_factory=time.time)

@dataclass
class FileProcessedEvent(Event):
    """File processing completed."""
    path: Path
    success: bool
    duration: float

class EventBus:
    """Async event bus."""
    
    def __init__(self):
        self._handlers: dict[type[Event], list[Handler]] = {}
    
    def subscribe[E: Event](
        self, 
        event_type: type[E], 
        handler: Callable[[E], Awaitable[None]]
    ) -> None:
        """Subscribe to events."""
        self._handlers.setdefault(event_type, []).append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish an event."""
        for handler in self._handlers.get(type(event), []):
            asyncio.create_task(handler(event))

# Usage
@event_bus.subscribe(FileProcessedEvent)
async def log_processing(event: FileProcessedEvent) -> None:
    logger.info(f"Processed {event.path} in {event.duration}s")
```

### 8. Structured Result Types

Use discriminated unions for results:

```python
from typing import Literal

@dataclass
class Success[T]:
    """Successful result."""
    value: T
    warnings: list[str] = field(default_factory=list)
    kind: Literal["success"] = "success"

@dataclass
class Failure:
    """Failed result."""
    error: str
    details: dict[str, Any] = field(default_factory=dict)
    kind: Literal["failure"] = "failure"

Result = Success[T] | Failure

# Usage with pattern matching
async def handle_result(result: Result[FormattedFile]) -> None:
    match result:
        case Success(value=file, warnings=warns) if warns:
            logger.warning(f"Formatted with warnings: {warns}")
            await save_file(file)
        case Success(value=file):
            await save_file(file)
        case Failure(error=err):
            logger.error(f"Format failed: {err}")
```

### 9. Actor Model for Concurrency

Use actors for better concurrency control:

```python
from typing import Any
import trio

class FileProcessor:
    """Actor for processing files."""
    
    def __init__(self, processor_id: int):
        self.id = processor_id
        self._inbox: trio.MemorySendChannel
        self._outbox: trio.MemoryReceiveChannel
        
    async def run(self) -> None:
        """Main actor loop."""
        async with trio.open_nursery() as nursery:
            async for message in self._outbox:
                match message:
                    case ("process", file):
                        nursery.start_soon(self._process_file, file)
                    case ("shutdown",):
                        break
    
    async def _process_file(self, file: Path) -> None:
        """Process a single file."""
        # Implementation
        pass

class ActorSystem:
    """Manage a pool of actors."""
    
    def __init__(self, num_actors: int):
        self.actors = [FileProcessor(i) for i in range(num_actors)]
    
    async def process_files(self, files: list[Path]) -> None:
        """Distribute files among actors."""
        async with trio.open_nursery() as nursery:
            for actor in self.actors:
                nursery.start_soon(actor.run)
            
            # Distribute work
            for i, file in enumerate(files):
                actor = self.actors[i % len(self.actors)]
                await actor.send(("process", file))
```

### 10. Native Parser Integration

Parser is a first-class citizen:

```python
class ParserService:
    """Ada parser service with caching."""
    
    def __init__(self, cache_size: int = 1000):
        self._cache = LRUCache(maxsize=cache_size)
        self._parser = ada2022_parser.Parser()
    
    async def parse(self, content: str, path: Path) -> ParseResult:
        """Parse Ada source with caching."""
        cache_key = hash((content, path))
        
        if cached := self._cache.get(cache_key):
            return cached
        
        # Parse in thread pool to avoid blocking
        result = await asyncio.to_thread(
            self._parser.parse,
            content,
            str(path)
        )
        
        self._cache[cache_key] = result
        return result
    
    def analyze_safety(self, ast: AST, operation: Operation) -> SafetyResult:
        """Analyze if operation is safe on AST."""
        visitor = SafetyAnalyzer(operation)
        return visitor.visit(ast)
```

### 11. Unified CLI with Rich UI

Modern CLI using Click + Rich:

```python
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.group()
@click.option('--config', type=click.Path(), help='Config file path')
@click.option('--quiet', is_flag=True, help='Quiet mode')
@click.pass_context
async def cli(ctx: click.Context, config: str, quiet: bool) -> None:
    """Ada development tool."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = await load_config(config)
    ctx.obj['quiet'] = quiet

@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--workers', default=4, help='Number of workers')
@click.pass_context
async def format(ctx: click.Context, files: tuple[str], workers: int) -> None:
    """Format Ada source files."""
    config = ctx.obj['config']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Formatting files...", total=len(files))
        
        async with ServiceContainer(config) as container:
            formatter = container.get(Formatter)
            
            async for result in formatter.format_files(files):
                progress.update(task, advance=1)
                
                match result:
                    case Success(value=file):
                        console.print(f"✓ {file.path}", style="green")
                    case Failure(error=err):
                        console.print(f"✗ {err}", style="red")
```

### 12. Integrated Testing Framework

Built-in testing support:

```python
class CommandTestCase:
    """Base test case for commands."""
    
    async def run_command(
        self, 
        command: str, 
        *args: str,
        config: dict[str, Any] | None = None
    ) -> CommandResult:
        """Run a command in test mode."""
        test_config = self.get_test_config()
        if config:
            test_config.update(config)
        
        async with TestEnvironment(test_config) as env:
            result = await env.run_command(command, *args)
            return result
    
    async def assert_file_formatted(
        self, 
        path: Path, 
        expected: str
    ) -> None:
        """Assert file was formatted correctly."""
        actual = path.read_text()
        assert actual == expected, f"Format mismatch in {path}"

# Usage
class TestFormatCommand(CommandTestCase):
    async def test_format_with_parser(self):
        result = await self.run_command(
            "format",
            "test.adb",
            config={"format": {"use_parser": True}}
        )
        
        assert result.exit_code == 0
        await self.assert_file_formatted(
            Path("test.adb"),
            expected_content
        )
```

## Benefits of Modern Architecture

1. **Cleaner Code**: No legacy compatibility code
2. **Better Performance**: Native async, uvloop, better concurrency
3. **Type Safety**: Full use of modern Python typing
4. **Extensibility**: Plugin architecture for commands
5. **Testability**: Built-in testing framework
6. **Maintainability**: Clear separation of concerns
7. **Developer Experience**: Modern tooling and patterns

## Migration Strategy

1. Create new `adatool` package alongside `adafmt`
2. Port core functionality to new architecture
3. Add new commands that were difficult in old architecture
4. Deprecate `adafmt` in favor of `adatool`
5. Provide migration guide for users

## Technology Stack

- **Python 3.13+**: Latest features and performance
- **uvloop**: High-performance async event loop
- **Pydantic**: Configuration and validation
- **Click**: Modern CLI framework
- **Rich**: Beautiful terminal UI
- **trio**: Alternative async runtime (optional)
- **inject**: Dependency injection
- **ada2022_parser**: Native parser integration