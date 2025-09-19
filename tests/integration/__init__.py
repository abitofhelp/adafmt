# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for adafmt.

This package contains integration tests that verify the interaction between
multiple components and test the system end-to-end. These tests may:

1. Require external dependencies (ALS installation)
2. Perform actual file I/O operations
3. Test complete workflows from CLI to formatted output
4. Take longer to execute than unit tests

Requirements:
    - Ada Language Server (ada_language_server) in PATH
    - Write permissions in temporary directories
    - Valid GNAT installation for project files

Test Modules:
    - test_adafmt_integration.py: Full formatting workflow tests
    - test_cli_integration.py: CLI command and argument processing

Markers:
    - @pytest.mark.integration: All tests in this package
    - @pytest.mark.requires_als: Tests that need ALS installed
    - @pytest.mark.slow: Tests taking > 1 second

Example:
    # Run integration tests
    pytest tests/integration/
    
    # Skip if no ALS
    pytest tests/integration/ -m "not requires_als"
    
    # Run specific workflow
    pytest tests/integration/test_adafmt_integration.py::test_format_project
"""