# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""adafmt test suite.

This package contains comprehensive unit and integration tests for the adafmt
Ada Language Formatter. Tests are organized into unit tests (fast, isolated)
and integration tests (slower, requiring external dependencies like ALS).

Test Organization:
    - unit/: Fast, isolated unit tests using mocks
    - integration/: End-to-end tests with real dependencies
    - conftest.py: Shared pytest fixtures and configuration
    - test_utils.py: Tests for utility functions

Running Tests:
    # All tests
    pytest
    
    # Unit tests only (fast)
    pytest tests/unit/
    
    # With coverage
    pytest --cov=adafmt --cov-report=html
    
    # Specific test
    pytest tests/unit/test_als_client.py::TestALSClient::test_initialization
"""