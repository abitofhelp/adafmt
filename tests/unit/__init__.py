"""Unit tests for adafmt components.

This package contains fast, isolated unit tests that verify individual
components of adafmt without requiring external dependencies. All tests
in this package should:

1. Run quickly (< 100ms per test)
2. Use mocks for external dependencies (ALS, file system, etc.)
3. Test a single unit of functionality
4. Be deterministic and repeatable

Test Modules:
    - test_als_client.py: ALS client protocol and communication
    - test_cli.py: Command-line interface logic
    - test_edits.py: Text edit operations and transformations
    - test_file_discovery.py: Ada file discovery and filtering
    - test_logging_jsonl.py: JSONL structured logging

Example:
    # Run all unit tests
    pytest tests/unit/
    
    # Run with coverage
    pytest tests/unit/ --cov=adafmt
    
    # Run specific module
    pytest tests/unit/test_als_client.py
"""