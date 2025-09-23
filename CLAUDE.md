# Claude Development Standards for adafmt

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This document contains project-specific rules, standards, and context for Claude when working on the adafmt project. It incorporates comprehensive Python development standards for reference-quality implementations.

## Documentation Standards

### Markdown File Headers

All markdown files under `/docs` must include the following header pattern:

```markdown
# <Title>

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

<Description paragraph>
```

## Code Standards

### Core Principles

#### Engineering Philosophy
- **Quality over Speed**: Generate correct code on first attempt, take time to implement solutions properly
- **No Quick Fixes**: Understand root causes before implementing changes
- **Professional Standards**: No hacks, workarounds, or temporary solutions without explicit authorization
- **Reference Quality**: All code should serve as exemplary Python implementations
- **No backward compatibility required**: We can use latest Python features and break APIs as needed
- **Modern Python**: Leverage Python 3.13+ features appropriately
- **Dependency Inversion Principle (DIP)**: High-level modules must not depend on low-level modules. Both must depend on abstractions. Abstractions must not depend on details. Details must depend on abstractions
- **Functional Error Handling**: Use dry-python/returns Either/Result pattern exclusively. All exceptions must be caught locally and transformed to appropriate error objects. No exceptions should propagate beyond function boundaries

#### Code Generation Philosophy
- **Correctness First**: Ensure proper syntax, types, and error handling
- **Idiomatic Python**: Follow Python idioms and conventions
- **Complete Solutions**: Include all necessary imports, type hints, and documentation
- **Testable Design**: Structure code for easy testing and mocking
- **Performance Awareness**: Consider performance implications but prioritize clarity

### Datetime Formatting Standards

- **Always use ISO 8601 BASIC format** for datetime strings: `YYYYMMDDTHHMMSSZ`
- **Use uppercase Z** for UTC timezone indicator (not lowercase 'z')
- **Use the `to_iso8601_basic()` utility function** from `utils.py` for all datetime formatting
- **Always create timezone-aware datetimes** using `timezone.utc` before formatting
- Example: `20250920T143045Z` (not `2025-09-20T14:30:45Z` or other variants)

### File Headers

All Python source files must include the following header:

```python
# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
```

### Import Order

1. Future imports (if needed)
2. Standard library imports
3. Third-party imports
4. Local application imports

Each group must be alphabetically sorted:

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional, Union

import aiofiles
import numpy as np
from pydantic import BaseModel

from .core import Parser
from .exceptions import ParseError
from .utils import normalize_path
```

### Testing Standards

- All new modules must have comprehensive tests (integration tests preferred for CLI projects)
- Test files must be named `test_<module_name>.py`
- Use pytest for all tests
- Follow AAA pattern: Arrange, Act, Assert with clear sections
- Include docstrings describing test scenarios
- Unit tests where beneficial, performance tests where performance matters

#### Test Organization
```
tests/
├── unit/
│   ├── test_parser.py
│   ├── test_lexer.py
│   └── test_utils.py
├── integration/
│   ├── test_full_parse.py
│   └── test_error_recovery.py
├── fixtures/
│   ├── valid_ada_files/
│   └── invalid_ada_files/
└── conftest.py
```

#### Test Patterns
```python
import pytest
from pathlib import Path

from ada2022_parser import Parser, ParseError

class TestParser:
    """Test suite for Ada 2022 parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return Parser()
    
    def test_parse_simple_type_declaration(self, parser):
        """Test parsing a simple type declaration."""
        # Arrange
        source = "type Count is range 0 .. 100;"
        
        # Act
        result = parser.parse(source)
        
        # Assert
        assert result.is_success
        assert result.ast.type == "type_declaration"
        assert result.ast.name == "Count"
```

### Async Code Standards

- Use `asyncio` for all asynchronous operations
- Prefer `async`/`await` over callbacks
- Use `aiofiles` for async file operations
- All async functions must have `_async` suffix or be clearly async from context

## Project-Specific Context

### Current Work: Parallel Worker Implementation

We are implementing a worker pool for parallel post-ALS processing with the following design:
- Queue-based architecture with bounded size (default 100 items)
- Queue memory limit: ~640KB (10 items * 64KB max file size)
- 3 workers by default (configurable via `--num-workers`)
- Thread-safe metrics collection
- Buffered async file I/O (8KB buffer size)
- Out-of-order completion is acceptable

**File Size Context**: Based on Ada project analysis, typical Ada source files are under 64KB, with most being much smaller. 1MB would be excessive.

### Key Commands

Before committing code changes, always run:
- `make lint` - Run linting checks
- `make typecheck` - Run type checking
- `make test` - Run unit tests
- `make test-all` - Run all tests including integration

### Git Workflow

- Work on feature branches (e.g., `parallel-workers`)
- Commit messages must be descriptive and follow conventional commits
- Include Claude attribution in commits:
  ```
  🤖 Generated with [Claude Code](https://claude.ai/code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### Version Management

- Documentation version is fixed at `1.0.0`
- `pyproject.toml` version is managed by python-semantic-release
- Do not manually update version numbers

## Architecture Decisions

### Worker Pool Design

1. **AsyncIO-based**: Use Python's native asyncio for concurrency
2. **Bounded Queue**: Prevent memory issues with maxsize=100
3. **Worker Health Monitoring**: 30-second timeout for health checks
4. **Atomic File Writes**: Use temp file + rename pattern
5. **Graceful Shutdown**: Handle signals and cleanup properly

### Error Handling

- **Comprehensive error handling required** for all error types:
  - Regular exceptions (file I/O, permissions, etc.)
  - Exceptional errors (out of memory, system failures)
  - OS signals (SIGTERM, SIGINT, etc.)
- Log all errors with full context
- Continue processing other files on single file failure
- Collect error messages in metrics (limit 100)
- Report errors to UI via queue
- Graceful degradation where possible
- Clean resource cleanup on all error paths

## Performance Considerations

- File I/O buffer size: 8KB (optimal for typical Ada source files)
- Queue size: 10 items (with 64KB max file size = ~640KB memory)
- Worker count must not exceed (0.6 * CPU cores)
- Monitor queue wait times in metrics
- Track pattern processing vs I/O time separately
- Consider `uvloop` for improved async performance (especially for ALS communication)

## Future Considerations

- **uvloop integration**: Strong candidate for performance improvement given ALS network bottleneck
- May need to implement backpressure if queue fills frequently  
- Could add priority queue for certain file types
- Might benefit from connection pooling for ALS

## Type Hints and Modern Python

### Type Annotations
- **Required for all public APIs**: Every public function, method, and class
- **Use modern syntax**: PEP 585 (3.9+) and PEP 604 (3.10+) where appropriate
- **Type aliases for clarity**:

```python
from typing import TypeAlias

# Clear type aliases
NodeId: TypeAlias = str
ParseResult: TypeAlias = dict[str, Any]
ErrorList: TypeAlias = list[tuple[int, str]]  # (line_number, message)

def parse_file(path: Path) -> ParseResult | None:
    """Parse an Ada source file."""
    ...
```

### Pattern Matching (3.10+)
Use structural pattern matching for clear, exhaustive handling:

```python
match node.type:
    case "type_declaration":
        return self._process_type(node)
    case "subprogram_declaration":
        return self._process_subprogram(node)
    case "package_declaration":
        return self._process_package(node)
    case _:
        raise ValueError(f"Unknown node type: {node.type}")
```

### Dataclasses and Pydantic
- Use `@dataclass` for simple data containers
- Use Pydantic models for validation and serialization
- Prefer immutable structures with `frozen=True`

## Error Handling

### Functional Error Handling with dry-python/returns

**MANDATORY**: All functions that can fail MUST use the Result/IOResult pattern from dry-python/returns. No exceptions should ever propagate beyond function boundaries.

#### Core Error Handling Principles

1. **All exceptions must be caught locally** and transformed to Result types
2. **Use Result for pure functions**, IOResult for I/O operations
3. **Define specific error types**, not generic strings
4. **Chain operations** using bind, map, and other combinators
5. **Handle concurrency errors** explicitly in async functions

#### Error Type Definitions

```python
from dataclasses import dataclass
from typing import Literal
from pathlib import Path

@dataclass(frozen=True)
class FileError:
    """File operation error."""
    path: Path
    operation: Literal["read", "write", "delete"]
    message: str
    original_error: str

@dataclass(frozen=True)
class ParseError:
    """Ada parsing error."""
    path: Path
    line: int
    column: int
    message: str

@dataclass(frozen=True)
class ALSError:
    """ALS communication error."""
    operation: str
    message: str
    timeout: bool = False

@dataclass(frozen=True)
class ValidationError:
    """Validation error."""
    path: Path
    rule: str
    message: str

@dataclass(frozen=True)
class ConcurrencyError:
    """Concurrency-related error."""
    operation: str
    message: str
    worker_id: int | None = None
```

#### Function Signatures with Result

```python
from returns.result import Result, Success, Failure
from returns.io import IOResult
from returns.future import FutureResult
from typing import TypeAlias

# Type aliases for common results
FileResult: TypeAlias = Result[str, FileError]
ParseResult: TypeAlias = Result[AST, ParseError]
FormatResult: TypeAlias = Result[FormattedFile, ALSError | ParseError | FileError]

# Pure functions return Result
def parse_ada(content: str, path: Path) -> Result[AST, ParseError]:
    """Parse Ada source - pure function."""
    try:
        ast = parser.parse(content)
        return Success(ast)
    except SyntaxError as e:
        return Failure(ParseError(
            path=path,
            line=e.lineno,
            column=e.offset,
            message=str(e)
        ))

# I/O functions return IOResult
def read_file(path: Path) -> IOResult[str, FileError]:
    """Read file - I/O operation."""
    @impure_safe
    def _read():
        return path.read_text(encoding="utf-8")
    
    return _read().alt(
        lambda e: Failure(FileError(
            path=path,
            operation="read",
            message=f"Failed to read file",
            original_error=str(e)
        ))
    )

# Async functions return FutureResult
async def format_with_als(
    client: ALSClient, 
    content: str, 
    path: Path
) -> FutureResult[str, ALSError]:
    """Format using ALS - async operation."""
    @future_safe
    async def _format():
        return await client.format_document(str(path), content)
    
    return await _format().alt(
        lambda e: Failure(ALSError(
            operation="format",
            message=f"ALS formatting failed: {e}",
            timeout=isinstance(e, asyncio.TimeoutError)
        ))
    )
```

#### Composing Operations

```python
from returns.pipeline import flow
from returns.pointfree import bind, alt
from returns.result import collect

async def process_file(path: Path) -> Result[FormattedFile, ProcessingError]:
    """Process file with full error handling."""
    return await flow(
        path,
        read_file,                    # IOResult[str, FileError]
        bind(parse_ada),             # Result[AST, ParseError]
        bind(validate_safety),       # Result[AST, ValidationError]
        bind(apply_pre_patterns),    # Result[str, PatternError]
        bind_async(format_with_als), # FutureResult[str, ALSError]
        bind(apply_post_patterns),   # Result[str, PatternError]
        bind_async(write_result),    # IOResult[Path, FileError]
        map(create_formatted_file),  # Result[FormattedFile, ...]
        alt(handle_error)           # Provide fallback on any error
    )

# Collecting multiple results
async def process_files(paths: list[Path]) -> Result[list[FormattedFile], list[ProcessingError]]:
    """Process multiple files, collecting all results."""
    results = await asyncio.gather(
        *[process_file(path) for path in paths],
        return_exceptions=True  # Don't let exceptions escape
    )
    
    # Separate successes and failures
    successes = []
    failures = []
    
    for result in results:
        match result:
            case Success(value):
                successes.append(value)
            case Failure(error):
                failures.append(error)
            case Exception() as e:
                # Should never happen with proper error handling
                failures.append(UnexpectedError(str(e)))
    
    return Success(successes) if not failures else Failure(failures)
```

#### Concurrency Error Handling

```python
from returns.future import future_safe
from contextlib import asynccontextmanager

class WorkerPool:
    """Worker pool with comprehensive error handling."""
    
    @future_safe
    async def submit(self, work_item: WorkItem) -> ProcessedItem:
        """Submit work with error handling."""
        try:
            # Acquire semaphore with timeout
            async with asyncio.timeout(5.0):
                async with self._semaphore:
                    return await self._process_item(work_item)
        except asyncio.TimeoutError:
            return Failure(ConcurrencyError(
                operation="submit",
                message="Failed to acquire worker",
                worker_id=None
            ))
    
    @asynccontextmanager
    async def worker(self, worker_id: int):
        """Worker context with error handling."""
        try:
            yield
        except Exception as e:
            # Log but don't propagate
            await self._log_worker_error(worker_id, e)
            raise ConcurrencyError(
                operation="worker",
                message=str(e),
                worker_id=worker_id
            )
```

#### Error Recovery Patterns

```python
# Retry with exponential backoff
@retry_on_failure(max_attempts=3, backoff=exponential_backoff)
async def resilient_als_call(client: ALSClient, request: dict) -> Result[dict, ALSError]:
    """ALS call with automatic retry."""
    return await client.send_request(request)

# Provide defaults on failure
def with_default[T](default: T):
    """Provide default value on failure."""
    def handler(error: Any) -> Result[T, Never]:
        log_error(f"Using default due to: {error}")
        return Success(default)
    return handler

# Circuit breaker for ALS
class ALSCircuitBreaker:
    """Circuit breaker for ALS failures."""
    
    async def call(self, operation: Callable) -> Result[T, ALSError]:
        """Call with circuit breaker."""
        if self._is_open():
            return Failure(ALSError(
                operation="circuit_breaker",
                message="Circuit breaker is open"
            ))
        
        result = await operation()
        self._record_result(result)
        return result
```

#### Testing Error Handling

```python
import pytest
from returns.result import Success, Failure

class TestErrorHandling:
    """Test error handling patterns."""
    
    def test_parse_error_handling(self):
        """Test parse errors are properly handled."""
        result = parse_ada("invalid ada code", Path("test.adb"))
        
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ParseError)
        assert "invalid" in result.failure().message
    
    async def test_concurrent_error_handling(self):
        """Test concurrent operations handle errors."""
        paths = [Path(f"test{i}.adb") for i in range(10)]
        
        # Inject some failures
        with mock.patch('read_file') as mock_read:
            mock_read.side_effect = [
                Success("content") if i % 3 else 
                Failure(FileError(...))
                for i in range(10)
            ]
            
            results = await process_files(paths)
            
            # Should have collected all results
            assert len(results.failure()) == 3
```

### Migration from Exceptions

When migrating existing code:

1. **Wrap at boundaries**: Start by wrapping exception-throwing code
2. **Define error types**: Create specific error classes for each domain
3. **Update signatures**: Change return types to Result/IOResult
4. **Update callers**: Use bind/map instead of try/catch
5. **Test thoroughly**: Ensure all error paths are tested

### Exception Hierarchy (Legacy - Do Not Use)

The following exception classes exist for compatibility but should not be used in new code:

```python
class AdafmtError(Exception):
    """Base exception for all adafmt errors."""
    pass

class PatternError(AdafmtError):
    """Raised when pattern application fails."""
    pass

class ALSError(AdafmtError):
    """Raised for ALS communication issues."""
    pass
```

## File and I/O Operations

### Configuration File Handling
- **NEVER modify user's configuration files** without explicit permission
- Create temporary copies for testing

### File I/O Best Practices
For synchronous I/O:
```python
def read_file(path: Path, encoding: str = "utf-8") -> str:
    """Read file with proper error handling."""
    try:
        return path.read_text(encoding=encoding)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {path}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Encoding error in {path}: {e}")
```

### Buffered Operations
```python
DEFAULT_BUFFER_SIZE = 8192  # 8KB, optimal for most text files

def process_large_file(path: Path) -> None:
    """Process file in chunks."""
    with open(path, 'r', buffering=DEFAULT_BUFFER_SIZE) as f:
        while chunk := f.read(DEFAULT_BUFFER_SIZE):
            process_chunk(chunk)
```

## Documentation Standards

### Module Documentation
```python
"""
Adafmt Pattern Processing Module.

This module provides pattern-based formatting for Ada source code,
implementing Pre-ALS and Post-ALS processing phases.

Example:
    >>> from adafmt import PatternProcessor
    >>> processor = PatternProcessor()
    >>> result = processor.process_file("example.adb")
    >>> print(result.status)

Note:
    This module uses the Ada 2022 reference grammar parser for
    context-aware transformations.
"""
```

### Function Documentation
```python
def apply_pattern(
    source: str,
    pattern: Pattern,
    *,
    phase: Literal["pre-als", "post-als"],
    strict: bool = False
) -> str:
    """
    Apply formatting pattern to Ada source code.
    
    Args:
        source: Ada source code to format.
        pattern: Pattern to apply.
        phase: Processing phase (pre-ALS or post-ALS).
        strict: Enable strict mode. Defaults to False.
    
    Returns:
        Formatted source code.
    
    Raises:
        PatternError: If pattern application fails.
        ValueError: If phase is invalid.
    
    Example:
        >>> formatted = apply_pattern(source, comment_pattern, phase="post-als")
    """
```

## Security Considerations

### Path Validation
Always validate and normalize paths:

```python
def safe_path(base_dir: Path, user_input: str) -> Path:
    """Safely resolve user path within base directory."""
    base = base_dir.resolve()
    target = (base / user_input).resolve()
    
    # Ensure target is within base directory
    if not target.is_relative_to(base):
        raise ValueError(f"Path escapes base directory: {user_input}")
    
    return target
```

## Release Checklist

Before releasing:

1. **Run all quality checks**:
   ```bash
   make lint        # Ruff linting
   make typecheck   # MyPy type checking
   make test        # All tests pass
   make test-all    # Including integration tests
   ```

2. **Update documentation**:
   - API docs are complete
   - Examples work
   - CHANGELOG is updated

3. **Version management**:
   - Use semantic versioning
   - Let python-semantic-release handle versions
   - Tag releases properly

## Notes for Claude

When working on this project:
1. **Always check existing patterns** before implementing new features
2. **Maintain consistency** with established code style
3. **Consider cross-platform compatibility** (Windows, Linux, macOS)
4. **Write comprehensive tests** for all public APIs
5. **Document edge cases** and limitations
6. **Use type hints** for all public interfaces
7. **Follow PEP 8** with modern interpretations
8. **Test with both small and large Ada projects**
9. **Keep UI updates non-blocking**
10. **Preserve existing CLI behavior** while adding new features
11. **Provide clear examples** in documentation
12. **Handle errors gracefully** with informative messages
13. **Benchmark performance-critical code** before optimizing

## Queue Size Recommendations

Based on Ada file size analysis:
- **Queue item limit**: 10 items (down from 100)
- **Max file size assumption**: 64KB per file
- **Total queue memory**: ~640KB maximum
- **Rationale**: Most Ada source files are well under 64KB, and limiting queue size prevents memory bloat while still allowing good parallelism
