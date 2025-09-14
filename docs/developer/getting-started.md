# Getting Started with adafmt Development

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

## 1. Introduction

Welcome to the adafmt developer guide! This document provides comprehensive information for developers who want to contribute to adafmt, integrate it into their projects, or understand its internals.

### 1.1 Prerequisites

Before getting started, ensure you have:
- Python 3.11 or higher
- Git for version control
- Ada Language Server (for integration testing)
- Basic understanding of:
  - Python asyncio
  - Language Server Protocol (LSP)
  - Command-line tool development
  - Testing with pytest

### 1.2 Quick Links

- [GitHub Repository](https://github.com/abitofhelp/adafmt)
- [Issue Tracker](https://github.com/abitofhelp/adafmt/issues)
- [API Documentation](../api/index.md)
- [Software Requirements Specification (SRS)](../SRS.md)
- [Software Design Document (SDD)](../SDD.md)
- [Test Documentation](../../tests/README.md)

## 2. Repository Structure

```
adafmt/
├── src/
│   └── adafmt/              # Main package
│       ├── __init__.py      # Package metadata and version
│       ├── __main__.py      # Module entry point
│       ├── cli.py           # CLI entry point (Typer-based)
│       ├── als_client.py    # ALS communication
│       ├── tui.py           # Terminal UI components
│       ├── file_discovery.py # File finding and filtering
│       ├── edits.py         # Text editing operations
│       ├── logging_jsonl.py # Structured logging
│       └── utils.py         # Utility functions
├── tests/                   # Comprehensive test suite
│   ├── conftest.py         # Shared pytest fixtures
│   ├── unit/               # Fast, isolated unit tests
│   │   ├── test_als_client.py
│   │   ├── test_cli.py
│   │   ├── test_edits.py
│   │   ├── test_file_discovery.py
│   │   └── test_logging_jsonl.py
│   ├── integration/        # End-to-end integration tests
│   │   ├── test_adafmt_integration.py
│   │   └── test_cli_integration.py
│   └── test_utils.py       # Utility function tests
├── tools/                  # Development and debugging tools
│   ├── README.md          # Tools documentation
│   ├── als_rpc_probe.py   # High-level ALS debugging
│   ├── als_rpc_probe_stdio.py # Low-level LSP debugging
│   └── harness_mocked.py  # Mock testing harness
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   │   ├── index.md       # API overview
│   │   ├── als_client.md  # ALS client docs
│   │   ├── cli.md         # CLI documentation
│   │   ├── edits.md       # Text editing docs
│   │   ├── file_discovery.md
│   │   ├── logging_jsonl.md
│   │   └── tui.md         # UI documentation
│   ├── developer/         # Developer guides
│   │   ├── overview.md    # This overview
│   │   ├── getting-started.md # Getting started guide
│   │   ├── contributing.md # Contributing workflow
│   │   ├── testing.md     # Testing guidelines
│   │   └── debugging.md   # Debugging and troubleshooting
│   ├── SRS.md             # Requirements specification
│   ├── SDD.md             # Design document
│   └── TROUBLESHOOTING.md # Common issues and solutions
├── Makefile               # Development shortcuts
├── pyproject.toml         # Project configuration (PEP 518)
├── .gitignore            # Git excludes
├── LICENSE               # MIT license
└── README.md             # User guide
```

## 3. Development Environment Setup

### 3.1 Clone the Repository

```bash
git clone https://github.com/abitofhelp/adafmt.git
cd adafmt
```

### 3.2 Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel
```

### 3.3 Install in Development Mode

```bash
# Install package in editable mode with dev dependencies
make dev

# Or manually:
pip install -e ".[dev]"
```

### 3.4 Verify Installation

```bash
# Test basic functionality
adafmt --version

# Run basic checks
make check

# Run the full test suite
make test-all
```

## Next Steps

Once you have your development environment set up:

1. **Read the [Contributing Guide](contributing.md)** - Learn about the development workflow, coding standards, and pull request process
2. **Review the [Testing Guide](testing.md)** - Understand how to write and run tests effectively
3. **Check the [Debugging Guide](debugging.md)** - Learn about development tools and troubleshooting techniques
4. **Explore the API Documentation** - Understand the codebase architecture and components

For a complete overview of all developer resources, see the [Developer Overview](overview.md).