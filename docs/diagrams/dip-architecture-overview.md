# DIP-Compliant Architecture Overview

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

This document explains how the adafmt/adatool architecture adheres to the Dependency Inversion Principle (DIP).

## Dependency Inversion Principle

The DIP states:
1. High-level modules should not depend on low-level modules. Both should depend on abstractions.
2. Abstractions should not depend on details. Details should depend on abstractions.

## Architecture Diagrams

### 1. Command Architecture (command-architecture-dip.puml)

This diagram shows how commands depend on abstractions:

- **High-level**: `CommandProcessor`, `FormatCommand`, `RenameCommand`
- **Abstractions**: `IALSClient`, `IParserService`, `IPatternEngine`, `IWorkerPool`
- **Low-level**: `ALSClient`, `AdaParser`, `PatternEngine`, `WorkerPool`

Key DIP compliance points:
- `CommandProcessor` depends on `IALSClient` interface, not the concrete `ALSClient`
- `FormatCommand` uses `IWorkerPool` abstraction, not the concrete implementation
- All concrete implementations depend on the interfaces defined by high-level policy

### 2. Pipeline Architecture (pipeline-architecture-dip.puml)

This diagram illustrates the processing pipeline:

- **Abstraction**: `Stage` protocol defines the contract for all pipeline stages
- **Implementations**: `ParseStage`, `LSPStage`, `PatternStage`, etc.
- **Service Dependencies**: Stages depend on service abstractions (`IALSClient`, `IParserService`)

Key DIP compliance points:
- `Pipeline` class depends only on the `Stage` abstraction
- Each stage depends on service interfaces, not concrete implementations
- New stages can be added without modifying the pipeline

### 3. Service Container (service-container-dip.puml)

This diagram shows dependency injection:

- **Container**: Manages service creation but returns abstractions
- **Factories**: Create concrete implementations
- **Consumers**: Commands receive services as abstractions

Key DIP compliance points:
- `ServiceContainer.get[T]()` returns abstractions, not concrete types
- Commands never import or know about concrete implementations
- Configuration determines which implementations to use

## Code Examples

### Defining Abstractions (Protocols)

```python
from typing import Protocol

class IALSClient(Protocol):
    """ALS client abstraction."""
    
    async def start(self) -> None:
        """Start the ALS process."""
        ...
    
    async def send_request(self, method: str, params: dict) -> dict:
        """Send LSP request."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown ALS."""
        ...
```

### High-Level Module Depending on Abstraction

```python
class FormatCommand(CommandProcessor):
    """High-level command depending on abstractions."""
    
    async def process_file(self, als_client: IALSClient) -> FormattedFile:
        """Process using abstraction, not concrete type."""
        # als_client is IALSClient, not ALSClient
        response = await als_client.send_request(
            "textDocument/formatting",
            {"textDocument": {"uri": file_uri}}
        )
        return self.apply_formatting(response)
```

### Low-Level Module Implementing Abstraction

```python
class ALSClient:
    """Concrete implementation of IALSClient."""
    
    async def start(self) -> None:
        """Implementation details."""
        self.process = await asyncio.create_subprocess_exec(...)
    
    async def send_request(self, method: str, params: dict) -> dict:
        """Implementation details."""
        # JSON-RPC communication
        ...
```

### Dependency Injection

```python
class ServiceContainer:
    """Manages dependencies following DIP."""
    
    def get[T](self, service_type: type[T]) -> T:
        """Return service as abstraction."""
        if service_type == IALSClient:
            # Create concrete but return as abstraction
            return ALSClient(self.config.als_command)
```

## Benefits

1. **Testability**: Easy to mock abstractions for testing
2. **Flexibility**: Can swap implementations without changing high-level code
3. **Maintainability**: Changes to low-level details don't affect high-level policy
4. **Extensibility**: New implementations can be added without modifying existing code

## Anti-Patterns to Avoid

❌ **Direct dependency on concrete class:**
```python
class FormatCommand:
    def __init__(self):
        self.als_client = ALSClient()  # Wrong!
```

❌ **Importing concrete implementations:**
```python
from ..als_client import ALSClient  # Wrong!

class FormatCommand:
    def process(self, client: ALSClient):  # Wrong!
        pass
```

❌ **Abstraction depending on details:**
```python
class IALSClient(Protocol):
    process: subprocess.Popen  # Wrong! Implementation detail
```

## Correct Patterns

✅ **Depend on abstractions:**
```python
class FormatCommand:
    def __init__(self, als_client: IALSClient):
        self.als_client = als_client  # Correct!
```

✅ **Import only protocols:**
```python
from ..protocols import IALSClient  # Correct!

class FormatCommand:
    def process(self, client: IALSClient):  # Correct!
        pass
```

✅ **Abstractions define behavior:**
```python
class IALSClient(Protocol):
    async def send_request(self, method: str, params: dict) -> dict:
        """Define behavior, not implementation."""
        ...
```

## Generating SVG Diagrams

To generate SVG files from the PlantUML diagrams:

```bash
# Generate all SVGs
plantuml -tsvg docs/diagrams/*.puml

# Or individually
plantuml -tsvg docs/diagrams/command-architecture-dip.puml
plantuml -tsvg docs/diagrams/pipeline-architecture-dip.puml
plantuml -tsvg docs/diagrams/service-container-dip.puml
```

## Summary

The architecture strictly follows DIP by:
1. Defining clear abstractions (protocols) for all services
2. Making high-level modules depend only on abstractions
3. Using dependency injection to provide implementations
4. Keeping abstractions stable and implementation-agnostic