# Getting Started with adafmt

**Version:** 0.0.0
**Last Updated:** January 2025

This guide provides step-by-step instructions for getting started with adafmt, including installation, first usage, and common workflow examples with real command combinations.

## Quick Start Checklist

- ✅ **Install adafmt** - See [Installation](#installation)
- ✅ **Install Ada Language Server** - See [Prerequisites](#prerequisites)
- ✅ **Have a GNAT project file** - Required for formatting
- ✅ **Test basic command** - See [First Steps](#first-steps)

## Installation

### Option 1: Install from PyPI (Recommended)
```bash
pip install adafmt
adafmt --version  # Verify installation
```

### Option 2: Install from GitHub Releases
```bash
# Download and install wheel
wget https://github.com/abitofhelp/adafmt/releases/latest/download/adafmt-0.0.0-py3-none-any.whl
pip install adafmt-0.0.0-py3-none-any.whl
```

### Option 3: Development Installation
```bash
git clone https://github.com/abitofhelp/adafmt.git
cd adafmt
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# Install package in editable mode with dev dependencies
make dev
# Or manually: pip install -e ".[dev]"
```

## Prerequisites

### Ada Language Server (Required)
adafmt requires ALS to be installed and available in your PATH:

```bash
# Check if ALS is installed
which ada_language_server

# Should output something like: /usr/local/bin/ada_language_server
```

**If ALS is not installed:**
- **GNAT Community/Pro**: ALS is included with modern GNAT distributions
- **Alire**: `alr install ada_language_server`
- **From source**: [Ada Language Server repository](https://github.com/AdaCore/ada_language_server)

### GNAT Project File (Required)
adafmt requires a `.gpr` project file. If you don't have one, create a basic one:

```ada
-- project.gpr
project My_Project is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
end My_Project;
```

## First Steps

### 1. Test Installation
```bash
# Check version
adafmt --version

# View help
adafmt --help

# View license (BSD-3-Clause)
adafmt license
```

### 2. Preview Formatting (Dry Run)
```bash
# Basic dry run - shows what would change without writing
adafmt --project-path project.gpr --include-path src/

# More verbose output
adafmt --project-path project.gpr --include-path src/ --ui pretty
```

### 3. Apply Formatting
```bash
# Apply changes to files
adafmt --project-path project.gpr --include-path src/ --write
```

## Common Usage Patterns

### Basic Formatting Workflows

#### Simple Project Formatting
```bash
# Preview changes
adafmt --project-path project.gpr --include-path src/

# Apply changes
adafmt --project-path project.gpr --include-path src/ --write

# Show diff of changes
adafmt --project-path project.gpr --include-path src/ --diff
```

#### Multi-Directory Project
```bash
# Format source and test directories
adafmt --project-path project.gpr \
    --include-path src/ \
    --include-path tests/ \
    --include-path examples/ \
    --write
```

#### Exclude Generated Code
```bash
# Format src/ but exclude generated/
adafmt --project-path project.gpr \
    --include-path src/ \
    --exclude-path src/generated/ \
    --write
```

### Development Workflows

#### Interactive Development
```bash
# Pretty UI with comprehensive feedback
adafmt --project-path project.gpr \
    --include-path src/ \
    --ui pretty \
    --log-path dev_format.jsonl \
    --write
```

#### Pre-commit Hook
```bash
# Check if files need formatting (for git hooks)
adafmt --project-path project.gpr \
    --include-path src/ \
    --check \
    --ui quiet

# Returns exit code 1 if formatting is needed
```

#### Format Before Git Commit
```bash
# Format and add to git
adafmt --project-path project.gpr \
    --include-path src/ \
    --pre-hook "git status --porcelain" \
    --post-hook "git add -A" \
    --write
```

### CI/CD Workflows

#### GitHub Actions / CI Check
```bash
# Fast CI check with strict timeouts
adafmt --project-path project.gpr \
    --include-path src/ \
    --check \
    --ui plain \
    --init-timeout 60 \
    --format-timeout 30 \
    --max-consecutive-timeouts 2
```

#### Automated Formatting in CI
```bash
# Apply formatting in CI pipeline
adafmt --project-path project.gpr \
    --include-path src/ \
    --ui json \
    --preflight aggressive \
    --write \
    --post-hook "git add -A && git commit -m 'Auto-format code' || true"
```

### Large Project Workflows

#### Large Codebase Processing
```bash
# Optimized for large projects with extended timeouts
adafmt --project-path large_project.gpr \
    --include-path src/ \
    --include-path lib/ \
    --exclude-path src/legacy/ \
    --init-timeout 300 \
    --format-timeout 120 \
    --max-consecutive-timeouts 10 \
    --ui json \
    --log-path large_project_format.jsonl \
    --write
```

#### Batch Processing Multiple Projects
```bash
# Script for multiple projects
for project in project1.gpr project2.gpr project3.gpr; do
    echo "Formatting $project..."
    adafmt --project-path "$project" \
        --include-path "$(dirname $project)/src" \
        --ui plain \
        --write
done
```

### Debugging and Troubleshooting Workflows

#### Debug ALS Issues
```bash
# Maximum debugging information
adafmt --project-path project.gpr \
    --include-path src/ \
    --log-path debug.jsonl \
    --stderr-path als_stderr.log \
    --ui plain \
    --init-timeout 600 \
    --format-timeout 180 \
    --preflight aggressive
```

#### Clean Up Before Formatting
```bash
# Aggressive cleanup of ALS processes
adafmt --project-path project.gpr \
    --include-path src/ \
    --preflight aggressive \
    --init-timeout 120 \
    --write
```

## Project Structure Examples

### Standard Ada Project
```
my_project/
├── project.gpr           # GNAT project file
├── src/                  # Source directory
│   ├── main.adb
│   ├── package.ads
│   └── package.adb
└── obj/                  # Object directory (auto-created)
```

**Command:**
```bash
cd my_project
adafmt --project-path project.gpr --include-path src/ --write
```

### Complex Project Structure
```
complex_project/
├── main.gpr              # Main project file
├── lib/                  # Library directory
│   ├── lib.gpr
│   └── src/
│       ├── utils.ads
│       └── utils.adb
├── app/                  # Application directory
│   └── src/
│       └── main.adb
├── tests/                # Test directory
│   └── src/
│       └── test_main.adb
└── generated/            # Generated code (exclude)
    └── bindings.ads
```

**Command:**
```bash
cd complex_project
adafmt --project-path main.gpr \
    --include-path lib/src/ \
    --include-path app/src/ \
    --include-path tests/src/ \
    --exclude-path generated/ \
    --write
```

## Environment-Specific Examples

### Development Machine
```bash
# Interactive development with full feedback
adafmt --project-path project.gpr \
    --include-path src/ \
    --ui pretty \
    --diff \
    --log-path "dev_format_$(date +%Y%m%d_%H%M%S).jsonl" \
    --write
```

### Build Server
```bash
# Automated build server formatting
adafmt --project-path project.gpr \
    --include-path src/ \
    --ui json \
    --check \
    --init-timeout 90 \
    --format-timeout 45 \
    --max-consecutive-timeouts 3 \
    --log-path build_format.jsonl
```

### Docker Container
```bash
# Containerized formatting
docker run --rm -v "$(pwd):/workspace" -w /workspace adafmt:latest \
    adafmt --project-path project.gpr \
    --include-path src/ \
    --ui plain \
    --write
```

## Flag Combinations Reference

### Essential Combinations

#### Basic Usage
```bash
# Minimum required flags
adafmt --project-path PROJECT.gpr --include-path DIR/

# With output control
adafmt --project-path PROJECT.gpr --include-path DIR/ --write
adafmt --project-path PROJECT.gpr --include-path DIR/ --check
adafmt --project-path PROJECT.gpr --include-path DIR/ --diff
```

#### UI Control
```bash
# UI modes
--ui auto     # Auto-detect terminal capabilities (default)
--ui pretty   # Rich interactive UI with progress bars
--ui plain    # Simple text output for logs
--ui json     # JSON Lines output for scripts
--ui quiet    # Minimal output, errors only
```

#### File Selection
```bash
# Include/exclude patterns
--include-path src/ --include-path lib/ --include-path tests/
--exclude-path build/ --exclude-path generated/ --exclude-path .git/
```

#### Timeout Control
```bash
# Timeout configurations
--init-timeout 180          # ALS initialization (default: 180s)
--format-timeout 60         # Per-file formatting (default: 60s)
--max-consecutive-timeouts 5 # Abort limit (default: 5)
```

### Advanced Combinations

#### Development Setup
```bash
adafmt --project-path project.gpr \
    --include-path src/ \
    --ui pretty \
    --diff \
    --log-path debug.jsonl \
    --pre-hook "git status --porcelain" \
    --post-hook "git add -A" \
    --write
```

#### CI/CD Setup
```bash
adafmt --project-path project.gpr \
    --include-path src/ \
    --check \
    --ui plain \
    --init-timeout 60 \
    --format-timeout 30 \
    --max-consecutive-timeouts 2 \
    --preflight aggressive
```

#### Debugging Setup
```bash
adafmt --project-path project.gpr \
    --include-path src/ \
    --log-path debug.jsonl \
    --stderr-path als_stderr.log \
    --ui plain \
    --init-timeout 600 \
    --format-timeout 180 \
    --preflight aggressive
```

## Common Mistakes and Solutions

### ❌ Wrong: Using old flag names
```bash
# Old/incorrect flag names
adafmt --project-file-path project.gpr  # Wrong!
adafmt --project project.gpr            # Wrong!
```

### ✅ Correct: Using current flag names
```bash
# Correct flag names
adafmt --project-path project.gpr
```

### ❌ Wrong: Forgetting required arguments
```bash
# Missing project path
adafmt --include-path src/  # Error: project path required
```

### ✅ Correct: Include required arguments
```bash
# All required arguments present
adafmt --project-path project.gpr --include-path src/
```

### ❌ Wrong: Not handling ALS issues
```bash
# No cleanup, may hang on existing processes
adafmt --project-path project.gpr --include-path src/
```

### ✅ Correct: Clean up before formatting
```bash
# Clean up stale processes first
adafmt --project-path project.gpr --include-path src/ --preflight kill
```

## Development Setup

This section is for developers who want to contribute to adafmt or understand its internals.

### Development Prerequisites

Before getting started with development, ensure you have:
- Python 3.11 or higher
- Git for version control
- Ada Language Server (for integration testing)
- Basic understanding of:
  - Python asyncio
  - Language Server Protocol (LSP)
  - Command-line tool development
  - Testing with pytest

### Repository Structure

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
│   ├── guides/            # User and developer guides (you are here!)
│   ├── api/               # API documentation
│   └── formal/            # Requirements and design documents
├── Makefile               # Development shortcuts
├── pyproject.toml         # Project configuration (PEP 518)
└── README.md             # Project overview
```

### Development Environment Setup

1. **Clone and setup** (if not done already):
   ```bash
   git clone https://github.com/abitofhelp/adafmt.git
   cd adafmt
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install in development mode**:
   ```bash
   # Install package in editable mode with dev dependencies
   make dev
   
   # Or manually:
   pip install -e ".[dev]"
   ```

3. **Verify installation**:
   ```bash
   # Test basic functionality
   adafmt --version
   
   # Run basic checks
   make check
   
   # Run the full test suite
   make test-all
   ```

### Development Commands

```bash
# Development setup
make dev          # Install with dev dependencies
make install      # Basic installation

# Code quality
make lint         # Run ruff linting
make format       # Format with black
make typecheck    # Run mypy type checking

# Testing
make test         # Unit tests only (fast)
make test-all     # All tests including integration
make coverage     # Test coverage report

# Ada formatting (requires project.gpr)
make ada-format   # Dry-run format
make ada-write    # Format and write files
make ada-check    # Check if formatting needed

# Distribution
make build        # Build packages
make dist-all     # All distribution formats
```

### Development Tools

The `tools/` directory contains specialized debugging utilities:

- **`als_rpc_probe.py`**: High-level ALS testing tool
  ```bash
  python tools/als_rpc_probe.py --project-path project.gpr --verbose
  ```

- **`als_rpc_probe_stdio.py`**: Low-level LSP protocol debugging
  ```bash
  python tools/als_rpc_probe_stdio.py --project-path project.gpr --file test.ads
  ```

- **`harness_mocked.py`**: Test without ALS dependency
  ```bash
  python tools/harness_mocked.py --test-scenario basic
  ```

### Next Steps for Developers

Once you have your development environment set up:

1. **Read the [Contributing Guide](contributing-guide.md)** - Learn about the development workflow, coding standards, and pull request process
2. **Review the [Testing Guide](testing-guide.md)** - Understand how to write and run tests effectively
3. **Check the [Troubleshooting Guide](troubleshooting-guide.md)** - Learn about debugging tools and issue resolution
4. **Explore the API Documentation** - Understand the codebase architecture and components

## Next Steps

Once you're comfortable with basic usage:

1. **Learn Advanced Configuration**: [Configuration Guide](configuration-guide.md)
2. **Troubleshoot Issues**: [Troubleshooting Guide](troubleshooting-guide.md)
3. **Optimize Performance**: [Timeout Configuration](timeout-guide.md)
4. **Use Pattern Formatting**: [Pattern Guide](patterns-guide.md)
5. **Contribute to Development**: See [Development Setup](#development-setup) above

## Getting Help

If you encounter issues:

1. **Check Prerequisites**: Ensure ALS is installed and accessible
2. **Verify Project File**: Ensure your `.gpr` file is valid
3. **Enable Logging**: Use `--log-path debug.jsonl` for detailed information
4. **Check Documentation**: [Troubleshooting Guide](troubleshooting-guide.md)
5. **Create Issue**: [GitHub Issues](https://github.com/abitofhelp/adafmt/issues) with logs and examples

---

*This getting started guide provides practical examples for immediate use. For comprehensive configuration options, see the [Configuration Reference](configuration.md).*
