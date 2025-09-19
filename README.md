# adafmt — Ada Language Formatter

**Version:** 0.0.0  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.

`adafmt` is an opinionated Ada 2022 formatter that leverages the Ada Language Server (ALS) to provide consistent, modern formatting while maintaining compatibility with earlier Ada versions. Built with extensibility in mind, it supports custom pattern formatting functions that allow teams to enforce project-specific style rules beyond what GNATFORMAT provides. It delivers a robust, production-ready solution for maintaining consistent code style across Ada projects of any size.

## Why Use AdaFmt?

### 🚀 Single-Pass Formatting
Unlike tools that require multiple passes to converge on a stable format, adafmt achieves consistent results in a single run. No need to run it three times hoping for convergence.

### 📊 Comprehensive Logging
Every formatting transformation is logged in structured JSON Lines format, providing complete visibility into what changed and why. Perfect for auditing and debugging formatting decisions.

### ✨ Modern Architecture
Built on the Ada Language Server (ALS) using the Language Server Protocol, avoiding known issues with chaining gnatformat and gnatpp. Get reliable, consistent results every time.

### 🎯 Extensible Pattern System
Configure custom formatting patterns in a simple JSON file. Override defaults, add project-specific transformations, or enforce team style guides beyond what standard tools provide.

### 🛡️ Safe by Default
- Dry-run mode shows changes before applying them
- Atomic file updates prevent partial writes
- Automatic validation catches syntax errors before writing
- Comprehensive error reporting for troubleshooting

### 🔧 Additional Benefits
- **CI/CD Integration**: Check mode with proper exit codes for automated pipelines
- **Performance Metrics**: Detailed statistics on processing time and throughput
- **Cross-Platform**: Works on Linux, macOS, and Windows with appropriate ALS
- **Project-Aware**: Understands GNAT project files (.gpr) for accurate formatting
- **Flexible Discovery**: Smart file finding with include/exclude path support

## Features

- **Language Server Protocol (LSP) Integration**: Uses the official Ada Language Server for accurate, specification-compliant formatting
- **Multiple UI Modes**: Choose from pretty (curses), basic, plain, or headless operation modes
- **Standalone Operation**: Works directly with Ada Language Server without external package managers
- **Robust Error Handling**: Retry logic for transient failures with configurable timeouts
- **Dry-Run by Default**: Preview changes safely before applying them
- **CI/CD Ready**: Exit codes and check mode for integration into automated workflows
- **Comprehensive Logging**: Structured JSON Lines logging for debugging and auditing
- **Cross-Platform**: Works on Linux, macOS, and Windows (with appropriate ALS installation)
- **Syntax Error Detection**: Compiler verification to catch GNATFORMAT false positives
- **Performance Statistics**: Detailed summary with files processed, time elapsed, and processing rate
- **Atomic File Updates**: Safe file writing with automatic backup during updates

## Quick Start

### Installation

#### From PyPI (Recommended)

```bash
pip install adafmt
```

#### From GitHub Releases

Download the appropriate package from the [latest release](https://github.com/abitofhelp/adafmt/releases/latest):

**Python Wheel (All Platforms)**
```bash
# Download the wheel file, then:
pip install adafmt-0.0.0-py3-none-any.whl
```

**Python Zipapp (Portable, No Installation)**
```bash
# Download adafmt.pyz, then run directly:
python3 adafmt.pyz --help

# Or make it executable (Unix-like systems):
chmod +x adafmt.pyz
./adafmt.pyz --help
```

**Standalone Executables (No Python Required)**
```bash
# Linux
wget https://github.com/abitofhelp/adafmt/releases/latest/download/adafmt-linux-x64
chmod +x adafmt-linux-x64
./adafmt-linux-x64 --help

# macOS
curl -LO https://github.com/abitofhelp/adafmt/releases/latest/download/adafmt-macos-x64
chmod +x adafmt-macos-x64
./adafmt-macos-x64 --help

# Windows (PowerShell)
Invoke-WebRequest -Uri https://github.com/abitofhelp/adafmt/releases/latest/download/adafmt-windows-x64.exe -OutFile adafmt.exe
.\adafmt.exe --help
```

#### From Source (Development Mode)

```bash
# Clone the repository
git clone https://github.com/abitofhelp/adafmt.git
cd adafmt

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Verify installation
adafmt --version
```

#### System Requirements

- Python 3.8 or higher
- Ada Language Server (ALS) installed and available in PATH
- For Alire projects: `alr` command available in PATH
- For curses UI: Terminal with curses support (most Unix-like systems)

### Basic Usage

#### Format Ada Files in a Directory

```bash
# Preview changes (dry-run mode)
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src

# Apply changes
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       --write
```

#### Format Specific Files

```bash
# Format individual files
adafmt --project-path /path/to/project.gpr \
       main.adb utils.ads types.ads

# Mix files and directories
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       special_file.adb
```

#### CI/CD Integration

```bash
# Check if any files need formatting (exits 1 if changes needed)
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       --check

# Use plain output for CI logs
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       --ui plain \
       --check
```

## Command-Line Interface

### Required Arguments

- `--project-path PATH`: Path to your GNAT project file (.gpr)
  
### Optional Arguments

#### File Selection
- `--include-path PATH`: Directory to search for Ada files (can be specified multiple times)
- `--exclude-path PATH`: Directory to exclude from search (can be specified multiple times)
- `FILES...`: Specific Ada files to format (positional arguments)

#### Output Options
- `--write`: Apply changes to files (default: dry-run mode)
- `--diff` / `--no-diff`: Show/hide unified diffs of changes (default: --diff)
- `--check`: Exit with code 1 if any files need formatting

#### User Interface
- `--ui {off,auto,pretty,basic,plain}`: UI mode selection
  - `off`: No UI, only output diffs
  - `auto`: Best available UI (default)
  - `pretty`: Curses UI with progress bar
  - `basic`: Simple text UI
  - `plain`: Minimal output for scripts

#### Advanced Error Handling
- **Smart Error Detection**: Distinguishes between syntax errors (prevent formatting) and semantic errors (allow formatting)
- **Compiler Verification**: Automatically verifies GNATFORMAT syntax errors to detect false positives
- **Detailed Error Reporting**: Comprehensive stderr output with timestamps, error types, and actionable guidance

#### Advanced Options
- `--preflight {off,warn,safe,kill,kill+clean,aggressive,fail}`: Handle existing ALS processes
  - `off`/`none`: Skip all checks
  - `warn`: Report processes and locks only
  - `safe` (default): Kill ALS processes older than `--als-stale-minutes`
  - `kill`: Same as `safe`
  - `kill+clean`: Kill stale ALS + remove stale lock files
  - `aggressive`: Kill ALL user's ALS processes + remove all locks
  - `fail`: Exit with error if any processes/locks found
- `--als-stale-minutes N`: Age threshold for stale ALS processes (default: 30)
- `--init-timeout SECONDS`: Timeout for ALS initialization (default: 180.0)
- `--warmup-seconds SECONDS`: Time to let ALS warm up (default: 10.0)
- `--format-timeout SECONDS`: Timeout per file formatting (default: 60.0)
- `--max-attempts N`: Retry attempts for transient errors (default: 2)

#### Debugging
- `--log-file-path PATH`: Write structured logs to JSONL file
- `--stderr-file-path PATH`: Capture ALS stderr output to file

### Environment Variables

- `ADAFMT_UI_FORCE`: Override the UI mode parameter
- `ADAFMT_UI_DEBUG`: Enable UI selection debug output

## File Discovery

adafmt searches for Ada source files using these rules:

1. **File Extensions**: `.ads` (spec), `.adb` (body), `.ada` (either)
2. **Search Behavior**: 
   - Recursively searches `--include-path` directories
   - Skips `--exclude-path` directories and their subdirectories
   - Processes explicitly named files regardless of location
3. **Common Exclusions**: Consider excluding:
   - Build directories (`obj/`, `lib/`, `.build/`)
   - Dependencies (`alire/`, `deps/`)
   - Generated files (`b__*.ad[sb]`)

## Integration Examples

### Makefile Integration

```makefile
.PHONY: format format-check

format:
	adafmt --project-file-path $(PROJECT_GPR) \
	       --include-path src \
	       --exclude-path obj \
	       --write

format-check:
	adafmt --project-file-path $(PROJECT_GPR) \
	       --include-path src \
	       --exclude-path obj \
	       --check
```

### Git Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check Ada files formatting
adafmt --project-file-path project.gpr \
       --include-path src \
       --check \
       --ui plain

if [ $? -ne 0 ]; then
    echo "Error: Ada files need formatting. Run 'make format' and try again."
    exit 1
fi
```

### GitHub Actions

```yaml
name: Ada Format Check
on: [push, pull_request]

jobs:
  format-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Ada
        uses: ada-actions/ada-toolchain@v1
        with:
          target: native
          distrib: community
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'
          
      - name: Install adafmt
        run: |
          pip install adafmt
          
      - name: Check formatting
        run: |
          adafmt --project-file-path project.gpr \
                 --include-path src \
                 --check \
                 --ui plain
```

## Troubleshooting

### Common Issues

#### "Ada Language Server not found"
- Ensure ALS is installed: `which ada_language_server`
- Add ALS to PATH or ensure it's available in your environment

#### "Existing ALS processes detected"
- Use `--preflight kill` to clean up stuck processes
- Or manually: `pkill -f ada_language_server`

#### Timeout Errors
- Increase timeouts: `--init-timeout 300 --warmup-seconds 20 --format-timeout 120`
- Check ALS stderr: `--stderr-file-path als-debug.log`

#### Understanding Error Types

**Syntax vs Semantic Errors:**
- **Syntax errors**: Malformed code structure (missing semicolons, unmatched parentheses, etc.)
  - These prevent formatting - ALS cannot parse the code structure
  - adafmt reports these as failures with error code -32803
- **Semantic errors**: Valid syntax but incorrect meaning (undefined types, missing imports, etc.)
  - These do NOT prevent formatting - code structure is valid
  - Examples: `"Domain_Event" not declared`, `invalid prefix in selected component`
  - Your code will format successfully but won't compile

**When ALS Reports Syntax Errors:**
- adafmt attempts compilation to verify (only for .adb/.ada files)
- False positives are tracked and shown as yellow warnings
- Real syntax errors prevent formatting and are reported as failures
- Failed files show "(details in the stderr log)" on terminal
- Full error details with timestamps are written to the stderr log file

#### No Changes Applied
- Ensure `--write` flag is used (default is dry-run)
- Check file permissions and disk space

### Debugging

Enable comprehensive logging to diagnose issues:

```bash
adafmt --project-file-path /path/to/project.gpr \
       --include-path /path/to/src \
       --log-file-path adafmt-debug.jsonl \
       --stderr-file-path als-stderr.log \
       --ui plain
```

View logs:
```bash
# View structured logs
jq . adafmt-debug.jsonl

# View ALS errors
cat als-stderr.log
```

## Architecture

adafmt follows a modular architecture:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     CLI     │────▶│  ALS Client │────▶│     ALS     │
│   (cli.py)  │     │(als_client) │     │  (subprocess│
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐     ┌─────────────┐
│     TUI     │     │    Edits    │
│  (tui.py)   │     │ (edits.py)  │
└─────────────┘     └─────────────┘
```

### Project Structure

```
adafmt/
├── src/adafmt/          # Main package source code
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # Command-line interface and main entry point
│   ├── als_client.py    # Ada Language Server async client
│   ├── tui.py           # Terminal UI with curses/plain fallback
│   ├── file_discovery.py # Ada source file discovery logic
│   ├── edits.py         # LSP TextEdit application and diff generation
│   ├── utils.py         # Utility functions (atomic write, Alire detection)
│   └── logging_jsonl.py # Structured JSON Lines logging
├── tests/               # Test suite
│   ├── test_*.py        # Unit tests for each module
│   └── test_integration.py # Integration tests with ALS
├── docs/                # Comprehensive documentation
│   ├── api/            # API reference documentation
│   ├── guides/          # User and developer guides  
│   ├── formal/         # Requirements and design documents
│   ├── reference/      # Technical references and deep-dives
│   └── user/           # User guides and troubleshooting
├── scripts/             # Build and release scripts
├── pyproject.toml       # Project configuration and dependencies
├── Makefile            # Common development tasks
└── README.md           # This file
```

### Key Components

- **CLI** (`cli.py`): Command-line argument parsing and orchestration
- **ALS Client** (`als_client.py`): Async JSON-RPC client for Language Server Protocol
- **TUI** (`tui.py`): Terminal UI with automatic fallback to simpler modes
- **File Discovery** (`file_discovery.py`): Smart Ada source file detection with exclusion support
- **Edit Engine** (`edits.py`): LSP TextEdit application with unified diff generation
- **Logger** (`logging_jsonl.py`): Structured logging for debugging and auditing
- **Utilities** (`utils.py`): Atomic file writes, process management, preflight checks

## Contributing

We welcome contributions! Please see our [Developer Documentation](docs/guides/index.md) for:

- Setting up a development environment
- Code style guidelines
- Testing requirements
- Submitting pull requests

## Documentation

📚 **Complete documentation is available in the [`docs/`](docs/) directory:**

### For Users
- **[Getting Started Guide](docs/user/getting-started.md)** - **New users start here!** Complete examples and workflows
- **[User Guides](docs/user/index.md)** - Troubleshooting, configuration, and usage guides
- **[Timeout Configuration](docs/user/timeout-guide.md)** - ALS timeout tuning and optimization

### For Developers  
- **[Developer Documentation](docs/guides/index.md)** - Complete development guide
- **[API Reference](docs/api/index.md)** - Technical API documentation
- **[Testing Guide](docs/guides/testing-guide.md)** - Comprehensive testing documentation

### Technical References
- **[Software Requirements Specification](docs/formal/SRS.md)** - Formal requirements
- **[Software Design Document](docs/formal/SDD.md)** - Architecture and design decisions
- **[Technical Reference](docs/reference/index.md)** - Advanced technical details

## License

**BSD-3-Clause** — see [LICENSE](./LICENSE) for the full text.

© 2025 Michael Gardner, A Bit of Help, Inc.  
SPDX-License-Identifier: BSD-3-Clause

## Acknowledgments

- Ada Language Server team for providing a robust LSP implementation
- Alire community for modern Ada package management
- Python asyncio contributors for excellent async subprocess support