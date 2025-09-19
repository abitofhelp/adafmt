# Testing Guidelines for adafmt

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

This guide covers testing best practices, test organization, and how to write effective tests for adafmt.

## Overview

The adafmt test suite follows Python testing best practices with comprehensive unit and integration tests. Tests are organized by type and scope, with clear separation between fast unit tests and slower integration tests that require external dependencies.

For comprehensive test documentation, see the [Test Suite Documentation](../../tests/README.md).

## Test Organization

- **Unit tests**: Fast, isolated, extensive mocking
- **Integration tests**: End-to-end, real dependencies
- **Fixtures**: Shared test data in `conftest.py`

### Test Structure

```
tests/
├── conftest.py                    # Shared pytest fixtures
├── unit/                          # Unit tests (fast, isolated)
│   ├── test_als_client.py        # ALS client unit tests
│   ├── test_cli.py               # CLI module unit tests
│   ├── test_edits.py             # Text edit operation tests
│   ├── test_file_discovery.py    # File discovery tests
│   └── test_logging_jsonl.py     # JSONL logging tests
├── integration/                   # Integration tests (slower, real dependencies)
│   ├── test_adafmt_integration.py # End-to-end formatting tests
│   └── test_cli_integration.py    # CLI command integration tests
└── test_utils.py                  # Tests for utility functions
```

## Running Tests

### Quick Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=adafmt --cov-report=html

# Run only unit tests (fast)
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_als_client.py

# Run specific test
pytest tests/unit/test_als_client.py::TestClass::test_method -v
```

### Test Categories

#### Unit Tests (Fast)
```bash
# Run only unit tests (no ALS required)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=adafmt
```

#### Integration Tests (Slower)
```bash
# Run integration tests (requires ALS)
pytest tests/integration/ -v

# Skip ALS-dependent tests
pytest tests/integration/ -m "not requires_als"
```

### Test Markers

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests (fast CI)
pytest -m "not integration"

# Run only async tests
pytest -m asyncio

# Run tests that require ALS
pytest -m requires_als
```

## Writing Good Tests

### Test Class Structure

```python
class TestComponentFeature:
    """Test suite for specific component feature."""

    def test_normal_case(self):
        """Test normal operation.

        Given: Normal input conditions
        When: Operation is performed
        Then: Expected result is produced
        """
        # Arrange
        input_data = create_test_data()

        # Act
        result = component.operation(input_data)

        # Assert
        assert result == expected_result
```

### Best Practices

1. **Descriptive Names**: Test names should describe what is being tested
2. **AAA Pattern**: Arrange, Act, Assert
3. **One Assertion**: Each test should verify one behavior
4. **Independent Tests**: Tests should not depend on each other
5. **Deterministic**: Tests should always produce same results
6. **Fast Tests**: Unit tests should run in milliseconds

### Example Test Implementation

```python
"""Test module for component X.

This module contains unit tests for the X component, covering:
- Normal operation scenarios
- Edge cases and boundary conditions
- Error handling and recovery
- Performance characteristics
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from adafmt.module import function_under_test


class TestComponentX:
    """Test suite for ComponentX functionality.

    Tests are organized by feature/behavior rather than by method,
    focusing on what the component should do rather than how it's implemented.
    """

    @pytest.fixture
    def component(self):
        """Create a ComponentX instance for testing."""
        return ComponentX(test_param="value")

    def test_normal_operation(self, component):
        """Test that component handles normal input correctly.

        Given: Valid input parameters
        When: Operation is performed
        Then: Expected output is produced
        """
        result = component.process("input")
        assert result == "expected output"

    def test_edge_case_empty_input(self, component):
        """Test handling of empty input.

        Given: Empty string input
        When: Operation is performed
        Then: Component returns None without error
        """
        result = component.process("")
        assert result is None

    @pytest.mark.parametrize("invalid_input,expected_error", [
        (None, ValueError),
        (123, TypeError),
        ([], TypeError),
    ])
    def test_invalid_input_raises_error(self, component, invalid_input, expected_error):
        """Test that invalid inputs raise appropriate errors.

        Given: Various invalid input types
        When: Operation is attempted
        Then: Appropriate exception is raised
        """
        with pytest.raises(expected_error):
            component.process(invalid_input)
```

## Mocking Strategies

### Mock External Dependencies

```python
@patch('adafmt.als_client.subprocess.Popen')
def test_als_start(mock_popen):
    """Test ALS process startup."""
    # Configure mock
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    # Test
    client = ALSClient(Path("test.gpr"))
    client.start()

    # Verify
    mock_popen.assert_called_once()
    assert client.process == mock_process
```

### Mock File System

```python
def test_file_discovery(tmp_path):
    """Test file discovery in temporary directory."""
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.adb").touch()
    (tmp_path / "src" / "package.ads").touch()
    (tmp_path / "doc.txt").touch()

    # Test discovery
    files = collect_files([tmp_path])

    # Verify only Ada files found
    assert len(files) == 2
    assert all(f.suffix in ['.adb', '.ads'] for f in files)
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test asynchronous operation."""
    client = AsyncClient()
    result = await client.async_method()
    assert result == "expected"
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def temp_ada_file(tmp_path):
    """Create a temporary Ada file for testing."""
    file_path = tmp_path / "test.adb"
    file_path.write_text('procedure Test is\nbegin\n   null;\nend Test;')
    return file_path

@pytest.fixture
def mock_als_client():
    """Create a mock ALS client for testing."""
    client = Mock(spec=ALSClient)
    client.format_file.return_value = []
    return client

@pytest.fixture
async def async_client():
    """Create an async ALS client for testing."""
    async with ALSClient(Path("test.gpr")) as client:
        yield client
```

## Coverage Goals

- **Line Coverage**: Minimum 80%
- **Branch Coverage**: Minimum 70%
- **Critical Paths**: 100% coverage

### Viewing Coverage

```bash
# Generate HTML coverage report
pytest --cov=adafmt --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=adafmt --cov-report=term-missing
```

## Performance Testing

### Benchmarking

```python
@pytest.mark.benchmark
def test_format_performance(benchmark, large_ada_file):
    """Benchmark file formatting performance."""
    client = ALSClient(Path("test.gpr"))

    def format_file():
        return client.format_file(large_ada_file)

    result = benchmark(format_file)
    assert benchmark.stats['mean'] < 1.0  # Under 1 second
```

### Load Testing

```python
@pytest.mark.slow
def test_format_many_files(tmp_path):
    """Test formatting large number of files."""
    # Create 100 test files
    for i in range(100):
        file_path = tmp_path / f"test_{i}.adb"
        file_path.write_text(f"procedure Test_{i} is\nbegin\n   null;\nend Test_{i};")

    # Format all files
    files = collect_files([tmp_path])
    results = format_all_files(files)

    # Verify
    assert len(results) == 100
    assert all(r.success for r in results)
```

## Worker Pool Testing

### Integration Tests for Parallel Processing

```python
# tests/integration/test_worker_pool.py
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from adafmt.worker_pool import WorkerPool, WorkItem
from adafmt.thread_safe_metrics import ThreadSafeMetrics


class TestWorkerPoolIntegration:
    """Integration tests for the worker pool functionality."""

    @pytest.mark.asyncio
    async def test_worker_pool_processes_items(self, tmp_path):
        """Test that worker pool processes all queued items."""
        # Create test files
        files = []
        for i in range(10):
            file = tmp_path / f"test_{i}.adb"
            file.write_text(f"procedure Test_{i} is\nbegin null; end;")
            files.append(file)

        # Create worker pool
        pool = WorkerPool(num_workers=3)
        metrics = ThreadSafeMetrics()

        # Mock pattern formatter
        pattern_formatter = Mock()
        pattern_formatter.format.return_value = Mock(
            content="formatted content",
            replacements=5
        )

        # Start pool
        await pool.start(metrics, pattern_formatter, write_enabled=True)

        # Queue items
        for i, file in enumerate(files):
            item = WorkItem(
                path=file,
                content="original content",
                index=i+1,
                total=len(files)
            )
            await pool.submit(item)

        # Shutdown and wait
        await pool.shutdown()

        # Verify all files processed
        assert await metrics.get_changed() == 10
        assert all(f.read_text() == "formatted content" for f in files)

    @pytest.mark.asyncio
    async def test_worker_pool_handles_errors(self):
        """Test that worker pool handles worker errors gracefully."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()

        # Mock pattern formatter that fails
        pattern_formatter = Mock()
        pattern_formatter.format.side_effect = Exception("Pattern error")

        await pool.start(metrics, pattern_formatter, write_enabled=False)

        # Queue items
        for i in range(5):
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="content",
                index=i+1,
                total=5
            )
            await pool.submit(item)

        await pool.shutdown()

        # Verify errors recorded
        assert await metrics.get_errors() == 5

    @pytest.mark.asyncio
    async def test_worker_pool_shutdown_timeout(self):
        """Test worker pool shutdown with timeout."""
        pool = WorkerPool(num_workers=1)

        # Mock a stuck worker
        async def stuck_worker():
            await asyncio.sleep(60)  # Longer than timeout

        pool._worker_func = stuck_worker
        await pool.start(Mock(), Mock(), False)

        # Shutdown with short timeout
        with pytest.raises(asyncio.TimeoutError):
            await pool.shutdown(timeout=0.1)

    @pytest.mark.asyncio
    async def test_queue_full_handling(self):
        """Test behavior when queue is full."""
        # Small queue for testing
        pool = WorkerPool(num_workers=1, queue_size=2)

        # Slow pattern formatter
        pattern_formatter = AsyncMock()
        pattern_formatter.format.side_effect = lambda *args: asyncio.sleep(0.1)

        await pool.start(Mock(), pattern_formatter, False)

        # Fill queue
        items = []
        for i in range(3):
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="content",
                index=i+1,
                total=3
            )
            items.append(item)

        # First two should queue immediately
        await pool.submit(items[0])
        await pool.submit(items[1])

        # Third should block until space available
        submit_task = asyncio.create_task(pool.submit(items[2]))

        # Should not complete immediately
        await asyncio.sleep(0.05)
        assert not submit_task.done()

        # After processing starts, should complete
        await asyncio.sleep(0.2)
        assert submit_task.done()

        await pool.shutdown()
```

### Performance Benchmarking

```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_worker_pool_performance(benchmark, large_project_files):
    """Benchmark worker pool performance vs sequential."""

    async def process_sequential():
        for file in large_project_files:
            # Simulate pattern processing
            await asyncio.sleep(0.01)

    async def process_parallel():
        pool = WorkerPool(num_workers=3)
        await pool.start(Mock(), Mock(), False)

        for i, file in enumerate(large_project_files):
            item = WorkItem(file, "content", i+1, len(large_project_files))
            await pool.submit(item)

        await pool.shutdown()

    # Benchmark both approaches
    seq_time = benchmark(process_sequential)
    par_time = benchmark(process_parallel)

    # Parallel should be faster
    assert par_time < seq_time * 0.7  # At least 30% faster
```

### Stress Testing

```python
@pytest.mark.stress
@pytest.mark.asyncio
async def test_worker_pool_stress(tmp_path):
    """Stress test with many files and workers."""
    # Create 1000 files
    files = []
    for i in range(1000):
        file = tmp_path / f"stress_{i}.adb"
        file.write_text(f"procedure Stress_{i} is begin null; end;")
        files.append(file)

    # Process with various worker counts
    for num_workers in [1, 2, 4, 8]:
        pool = WorkerPool(num_workers=num_workers)
        metrics = ThreadSafeMetrics()

        start = asyncio.get_event_loop().time()
        await pool.start(metrics, Mock(), True)

        for i, file in enumerate(files):
            await pool.submit(WorkItem(file, "content", i+1, len(files)))

        await pool.shutdown()
        duration = asyncio.get_event_loop().time() - start

        print(f"Workers: {num_workers}, Time: {duration:.2f}s")
        assert await metrics.get_changed() == 1000
```

## Debugging Tests

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show local variables
pytest -l

# Capture print output
pytest -s
```

## Continuous Integration

The project runs tests in GitHub Actions across multiple Python versions. See the comprehensive [Test Suite Documentation](../../tests/README.md) for CI configuration details and advanced testing patterns.

## Related Documentation

- [Test Suite Documentation](../../tests/README.md) - Complete testing reference
- [Contributing Guide](contributing-guide.md) - Development workflow and standards
- [Troubleshooting Guide](troubleshooting-guide.md) - Troubleshooting and development tools
- [Developer Overview](index.md) - Complete developer resource index

---

*Keep tests simple, focused, and maintainable. Good tests are documentation for your code.*
