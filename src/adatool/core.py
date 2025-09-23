# =============================================================================
# adatool - Ada Development Tool
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Core infrastructure for adatool - a modern Ada development tool.

This module provides the foundational components for a plugin-based,
async-first architecture without backward compatibility constraints.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, TypeAlias, TypeVar

import inject
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from rich.console import Console

# Type aliases for clarity
T = TypeVar('T')
R = TypeVar('R')
CommandName: TypeAlias = str
EventHandler: TypeAlias = Callable[['Event'], asyncio.Future[None]]

# Global console for rich output
console = Console()


# ============================================================================
# Result Types (Discriminated Unions)
# ============================================================================

@dataclass(frozen=True)
class Success[T]:
    """Successful operation result."""
    value: T
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    kind: Literal["success"] = field(default="success", init=False)


@dataclass(frozen=True)
class Failure:
    """Failed operation result."""
    error: str
    error_type: str
    details: dict[str, Any] = field(default_factory=dict)
    traceback: str | None = None
    kind: Literal["failure"] = field(default="failure", init=False)


Result: TypeAlias = Success[T] | Failure


# ============================================================================
# Event System
# ============================================================================

@dataclass
class Event:
    """Base event class."""
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    source: str = "system"


@dataclass
class CommandStartedEvent(Event):
    """Command execution started."""
    command: str
    args: dict[str, Any]


@dataclass
class CommandCompletedEvent(Event):
    """Command execution completed."""
    command: str
    success: bool
    duration: float
    result: Result[Any]


@dataclass
class FileProcessedEvent(Event):
    """File processing completed."""
    path: Path
    operation: str
    success: bool
    duration: float
    changes: int = 0


class EventBus:
    """Async event bus for loose coupling."""
    
    def __init__(self):
        self._handlers: dict[type[Event], list[EventHandler]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None
    
    def subscribe[E: Event](
        self,
        event_type: type[E],
        handler: Callable[[E], asyncio.Future[None]]
    ) -> Callable[[], None]:
        """
        Subscribe to events of a specific type.
        
        Returns an unsubscribe function.
        """
        self._handlers.setdefault(event_type, []).append(handler)
        
        def unsubscribe():
            self._handlers[event_type].remove(handler)
        
        return unsubscribe
    
    async def publish(self, event: Event) -> None:
        """Publish an event asynchronously."""
        await self._queue.put(event)
    
    async def start(self) -> None:
        """Start the event bus."""
        self._running = True
        self._task = asyncio.create_task(self._process_events())
    
    async def stop(self) -> None:
        """Stop the event bus."""
        self._running = False
        if self._task:
            await self._task
    
    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running or not self._queue.empty():
            try:
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=0.1
                )
                
                # Dispatch to handlers
                handlers = self._handlers.get(type(event), [])
                if handlers:
                    await asyncio.gather(
                        *[handler(event) for handler in handlers],
                        return_exceptions=True
                    )
                    
            except asyncio.TimeoutError:
                continue


# ============================================================================
# Configuration System
# ============================================================================

class FormatConfig(BaseModel):
    """Format command configuration."""
    
    use_tabs: bool = Field(default=False, description="Use tabs instead of spaces")
    tab_width: int = Field(default=3, description="Tab width in spaces")
    line_length: int = Field(default=120, description="Maximum line length")
    use_parser: bool = Field(default=True, description="Use parser for analysis")
    pre_als_phase: bool = Field(default=True, description="Run pre-ALS phase")
    post_als_phase: bool = Field(default=True, description="Run post-ALS phase")
    validate_with_gnat: bool = Field(default=False, description="Validate with GNAT")


class RenameConfig(BaseModel):
    """Rename command configuration."""
    
    case_sensitive: bool = Field(default=True, description="Case-sensitive matching")
    dry_run: bool = Field(default=False, description="Preview changes without applying")
    validate_with_gnat: bool = Field(default=True, description="Validate after rename")


class AdaToolConfig(BaseSettings):
    """Global adatool configuration."""
    
    # Core settings
    workers: int = Field(default=4, description="Number of worker processes")
    use_uvloop: bool = Field(default=True, description="Use uvloop for performance")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # ALS settings
    als_command: list[str] = Field(
        default=["ada_language_server"],
        description="Command to start ALS"
    )
    als_startup_timeout: float = Field(default=30.0, description="ALS startup timeout")
    als_request_timeout: float = Field(default=60.0, description="ALS request timeout")
    
    # Parser settings
    parser_cache_size: int = Field(default=1000, description="Parser cache size")
    parser_timeout: float = Field(default=5.0, description="Parser timeout")
    
    # GNAT settings
    gnat_command: list[str] = Field(
        default=["gcc", "-c", "-gnatc", "-gnat2022"],
        description="GNAT compiler command"
    )
    
    # Command configurations
    format: FormatConfig = Field(default_factory=FormatConfig)
    rename: RenameConfig = Field(default_factory=RenameConfig)
    
    model_config = {
        "env_prefix": "ADATOOL_",
        "env_file": ".adatool.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# ============================================================================
# Command System
# ============================================================================

class CommandContext:
    """Context passed to commands."""
    
    def __init__(
        self,
        config: AdaToolConfig,
        args: dict[str, Any],
        services: 'ServiceContainer',
        event_bus: EventBus
    ):
        self.config = config
        self.args = args
        self.services = services
        self.event_bus = event_bus
        self.console = console


class Command(Protocol):
    """Protocol for command plugins."""
    
    name: str
    description: str
    
    async def configure_parser(self, parser: Any) -> None:
        """Configure argument parser for this command."""
        ...
    
    async def execute(self, context: CommandContext) -> Result[Any]:
        """Execute the command."""
        ...


class CommandRegistry:
    """Registry for command plugins."""
    
    def __init__(self):
        self._commands: dict[str, Command] = {}
    
    def register(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.name] = command
    
    def get(self, name: str) -> Command | None:
        """Get a command by name."""
        return self._commands.get(name)
    
    def list(self) -> list[Command]:
        """List all registered commands."""
        return list(self._commands.values())


# Global registry
command_registry = CommandRegistry()


def register_command(cls: type[Command]) -> type[Command]:
    """Decorator to register commands."""
    command_registry.register(cls())
    return cls


# ============================================================================
# Service Container (Dependency Injection)
# ============================================================================

class ServiceContainer:
    """Service container with dependency injection."""
    
    def __init__(self, config: AdaToolConfig):
        self.config = config
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
    
    async def __aenter__(self) -> ServiceContainer:
        """Initialize services."""
        # Register service factories
        self._register_factories()
        
        # Configure injection
        inject.configure(self._configure_injection)
        
        # Initialize core services
        await self._initialize_services()
        
        return self
    
    async def __aexit__(self, *args) -> None:
        """Cleanup services."""
        for service in self._services.values():
            if hasattr(service, '__aexit__'):
                await service.__aexit__(*args)
            elif hasattr(service, 'close'):
                await service.close()
            elif hasattr(service, 'shutdown'):
                await service.shutdown()
        
        inject.clear()
    
    def _register_factories(self) -> None:
        """Register service factories."""
        from .als import ALSClient
        from .parser import ParserService
        from .patterns import PatternEngine
        
        self._factories[ALSClient] = lambda: ALSClient(self.config.als_command)
        self._factories[ParserService] = lambda: ParserService(self.config.parser_cache_size)
        self._factories[PatternEngine] = lambda: PatternEngine()
    
    async def _initialize_services(self) -> None:
        """Initialize core services."""
        # Create services lazily on first access
        pass
    
    def _configure_injection(self, binder: inject.Binder) -> None:
        """Configure dependency injection."""
        binder.bind(ServiceContainer, self)
        binder.bind(AdaToolConfig, self.config)
        
        # Bind service factories
        for service_type, factory in self._factories.items():
            binder.bind_to_provider(service_type, factory)
    
    @inject.autoparams()
    def get[T](self, service_type: type[T]) -> T:
        """Get or create a service instance."""
        if service_type not in self._services:
            if factory := self._factories.get(service_type):
                self._services[service_type] = factory()
            else:
                raise ValueError(f"No service registered for {service_type}")
        
        return self._services[service_type]


# ============================================================================
# Pipeline Architecture
# ============================================================================

class Stage[T, R](Protocol):
    """Protocol for pipeline stages."""
    
    async def process(self, item: T) -> R:
        """Process an item through this stage."""
        ...
    
    @property
    def name(self) -> str:
        """Stage name for debugging."""
        ...


@dataclass
class PipelineResult[T]:
    """Result of pipeline execution."""
    result: T
    stages_completed: list[str]
    duration: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Pipeline[T, R]:
    """
    Type-safe async pipeline with error handling and monitoring.
    """
    
    def __init__(self, *stages: Stage[Any, Any]):
        self.stages = stages
        self._event_bus: EventBus | None = None
    
    def set_event_bus(self, event_bus: EventBus) -> None:
        """Set event bus for pipeline events."""
        self._event_bus = event_bus
    
    async def process(self, item: T) -> Result[PipelineResult[R]]:
        """Process item through all stages."""
        start_time = time.time()
        stages_completed = []
        result = item
        
        try:
            for stage in self.stages:
                stage_start = time.time()
                result = await stage.process(result)
                
                stages_completed.append(stage.name)
                
                if self._event_bus:
                    await self._event_bus.publish(
                        StageCompletedEvent(
                            stage=stage.name,
                            duration=time.time() - stage_start
                        )
                    )
            
            return Success(
                PipelineResult(
                    result=result,
                    stages_completed=stages_completed,
                    duration=time.time() - start_time
                )
            )
            
        except Exception as e:
            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                details={
                    "stage": stages_completed[-1] if stages_completed else "init",
                    "stages_completed": stages_completed
                }
            )
    
    async def process_stream(
        self,
        items: AsyncIterator[T]
    ) -> AsyncIterator[Result[PipelineResult[R]]]:
        """Process a stream of items."""
        async for item in items:
            yield await self.process(item)


# ============================================================================
# File Processing
# ============================================================================

@dataclass
class AdaFile:
    """Represents an Ada source file."""
    path: Path
    content: str
    encoding: str = "utf-8"
    ast: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    async def from_path(cls, path: Path, encoding: str = "utf-8") -> AdaFile:
        """Load file asynchronously."""
        import aiofiles
        
        async with aiofiles.open(path, 'r', encoding=encoding) as f:
            content = await f.read()
        
        return cls(path=path, content=content, encoding=encoding)
    
    async def save(self) -> None:
        """Save file atomically."""
        import aiofiles
        import tempfile
        import os
        
        # Write to temp file
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp"
        )
        
        try:
            async with aiofiles.open(fd, 'w', encoding=self.encoding) as f:
                await f.write(self.content)
            
            # Atomic rename
            os.replace(temp_path, self.path)
            
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise


# ============================================================================
# Main Application
# ============================================================================

class AdaTool:
    """Main application class."""
    
    def __init__(self, config: AdaToolConfig | None = None):
        self.config = config or AdaToolConfig()
        self.event_bus = EventBus()
        self._setup_logging()
    
    async def __aenter__(self) -> AdaTool:
        """Start the application."""
        # Setup uvloop if requested
        if self.config.use_uvloop:
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                console.print("[yellow]uvloop not available, using default event loop[/yellow]")
        
        # Start event bus
        await self.event_bus.start()
        
        # Subscribe to events
        self._setup_event_handlers()
        
        return self
    
    async def __aexit__(self, *args) -> None:
        """Cleanup application."""
        await self.event_bus.stop()
    
    async def run(self, command_name: str, **kwargs) -> Result[Any]:
        """Run a command."""
        command = command_registry.get(command_name)
        if not command:
            return Failure(
                error=f"Unknown command: {command_name}",
                error_type="CommandNotFound"
            )
        
        # Create context
        async with ServiceContainer(self.config) as services:
            context = CommandContext(
                config=self.config,
                args=kwargs,
                services=services,
                event_bus=self.event_bus
            )
            
            # Publish start event
            await self.event_bus.publish(
                CommandStartedEvent(
                    command=command_name,
                    args=kwargs
                )
            )
            
            # Execute command
            start_time = time.time()
            result = await command.execute(context)
            duration = time.time() - start_time
            
            # Publish completion event
            await self.event_bus.publish(
                CommandCompletedEvent(
                    command=command_name,
                    success=isinstance(result, Success),
                    duration=duration,
                    result=result
                )
            )
            
            return result
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        import logging
        
        logging.basicConfig(
            level=self.config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _setup_event_handlers(self) -> None:
        """Setup default event handlers."""
        
        @self.event_bus.subscribe(FileProcessedEvent)
        async def log_file_processed(event: FileProcessedEvent) -> None:
            """Log file processing events."""
            if event.success:
                console.print(f"✓ {event.path}", style="green")
            else:
                console.print(f"✗ {event.path}", style="red")
        
        @self.event_bus.subscribe(CommandCompletedEvent)
        async def log_command_completed(event: CommandCompletedEvent) -> None:
            """Log command completion."""
            status = "✓" if event.success else "✗"
            style = "green" if event.success else "red"
            console.print(
                f"{status} Command '{event.command}' completed in {event.duration:.2f}s",
                style=style
            )


# ============================================================================
# Helpers
# ============================================================================

import time
from uuid import uuid4


@dataclass
class StageCompletedEvent(Event):
    """Pipeline stage completed."""
    stage: str
    duration: float