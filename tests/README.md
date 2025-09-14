# Test Suite Documentation

**Version:** 1.0.0  
**Last Updated:** January 2025  
**Test Framework:** pytest

## Overview

The adafmt test suite follows Python testing best practices with comprehensive unit and integration tests. Tests are organized by type and scope, with clear separation between fast unit tests and slower integration tests that require external dependencies.

## Test Organization

```
tests/
├── README.md                      # This file
├── __init__.py                    # Package marker
├── conftest.py                    # Shared pytest fixtures
├── unit/                          # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_als_client.py        # ALS client unit tests
│   ├── test_cli.py               # CLI module unit tests
│   ├── test_edits.py             # Text edit operation tests
│   ├── test_file_discovery.py    # File discovery tests
│   └── test_logging_jsonl.py     # JSONL logging tests
├── integration/                   # Integration tests (slower, real dependencies)
│   ├── __init__.py
│   ├── test_adafmt_integration.py # End-to-end formatting tests
│   └── test_cli_integration.py    # CLI command integration tests
└── test_utils.py                  # Tests for utility functions
```

## Test Categories

### Unit Tests (`unit/`)

Unit tests verify individual components in isolation:
- **Fast**: Run in milliseconds
- **Isolated**: Use mocks for external dependencies
- **Focused**: Test one specific behavior
- **Deterministic**: Always produce same results

### Integration Tests (`integration/`)

Integration tests verify component interactions:
- **End-to-end**: Test complete workflows
- **Real dependencies**: May require ALS installation
- **Environment-aware**: Test actual file I/O and processes
- **Comprehensive**: Verify system behavior

## Running Tests

### Quick Start

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
pytest tests/unit/test_als_client.py::TestALSClient::test_initialization
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

### Verbose Output

```bash
# Show test names
pytest -v

# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Maximum verbosity
pytest -vvs
```

## Writing Tests

### Test Structure

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

### Best Practices

1. **Descriptive Names**: Test names should describe what is being tested
2. **AAA Pattern**: Arrange, Act, Assert
3. **One Assertion**: Each test should verify one behavior
4. **Independent Tests**: Tests should not depend on each other
5. **Deterministic**: Tests should always produce same results
6. **Fast Tests**: Unit tests should run in milliseconds

### Fixtures

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

## Test Coverage

### Coverage Goals

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

### Coverage Configuration

```ini
# .coveragerc or pyproject.toml
[tool.coverage.run]
source = ["adafmt"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Mocking Strategies

### Mock External Dependencies

```python
@patch('subprocess.Popen')
def test_als_client_start(mock_popen):
    """Test ALS client process startup."""
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

## Continuous Integration

### GitHub Actions Configuration

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[test]"
        
    - name: Run unit tests
      run: pytest tests/unit/ -v
      
    - name: Run integration tests
      run: pytest tests/integration/ -v
      
    - name: Upload coverage
      uses: codecov/codecov-action@v3
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

### VS Code Configuration

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Current Test",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${file}::${selectedText}",
                "-vvs"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

## Test Data

### Fixtures Directory

```
tests/fixtures/
├── valid/                 # Valid Ada files
│   ├── simple.adb
│   └── complex_package.ads
├── invalid/              # Invalid Ada files
│   ├── syntax_error.adb
│   └── missing_end.ads
└── edge_cases/          # Edge case files
    ├── empty.adb
    └── unicode_names.ads
```

### Using Test Data

```python
@pytest.fixture
def fixture_file():
    """Load test fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "valid" / "simple.adb"
    return fixture_path

def test_with_fixture(fixture_file):
    """Test using fixture file."""
    result = format_file(fixture_file)
    assert result.success
```

## Common Patterns

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test asynchronous operation."""
    client = AsyncClient()
    result = await client.async_method()
    assert result == "expected"
```

### Timeout Testing

```python
@pytest.mark.timeout(5)
def test_with_timeout():
    """Test that completes within timeout."""
    result = potentially_slow_operation()
    assert result is not None
```

### Temporary Files

```python
def test_file_operations(tmp_path):
    """Test file operations with temporary files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    
    result = process_file(test_file)
    assert result.success
    assert test_file.read_text() == "modified content"
```

## See Also

- [pytest Documentation](https://docs.pytest.org/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- [DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md)