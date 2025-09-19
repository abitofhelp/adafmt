# Configuration Guide

**Version:** 0.0.0  
**Last Updated:** September 2025

Complete guide for configuring adafmt, including command-line options, environment variables, ALS tracing, and advanced configuration patterns.

---

## Table of Contents

### Basic Configuration
1. [Command-Line Arguments](#1-command-line-arguments)
2. [Environment Variables](#2-environment-variables)
3. [Configuration Patterns](#3-configuration-patterns)

### Advanced Configuration
4. [ALS Traces Configuration](#4-als-traces-configuration)
5. [Performance Tuning](#5-performance-tuning)
6. [Environment-Specific Setup](#6-environment-specific-setup)

### Troubleshooting
7. [Common Configuration Issues](#7-common-configuration-issues)
8. [Debugging Configuration](#8-debugging-configuration)

---

## 1. Command-Line Arguments

### Required Arguments

#### `--project-path` (Required)
**Format**: `--project-path PATH`  
**Purpose**: Specifies the path to the GNAT project file (.gpr)  
**Examples**:
```bash
adafmt --project-path project.gpr
adafmt --project-path /path/to/my_project.gpr
```

### File Selection

#### `--include-path`
**Format**: `--include-path PATH` (can be used multiple times)  
**Purpose**: Directories to search for Ada files  
**Default**: Current directory  
**Examples**:
```bash
# Single directory
adafmt --project-path project.gpr --include-path src/

# Multiple directories
adafmt --project-path project.gpr \
    --include-path src/ \
    --include-path lib/ \
    --include-path tests/
```

#### `--exclude-path`
**Format**: `--exclude-path PATH` (can be used multiple times)  
**Purpose**: Directories to exclude from formatting  
**Examples**:
```bash
# Exclude generated code
adafmt --project-path project.gpr \
    --include-path src/ \
    --exclude-path src/generated/

# Exclude multiple directories
adafmt --project-path project.gpr \
    --exclude-path build/ \
    --exclude-path .git/ \
    --exclude-path tmp/
```

### Operation Modes

#### `--write`
**Purpose**: Write formatted content back to files (default is dry-run)
**Example**:
```bash
# Preview changes (default)
adafmt --project-path project.gpr

# Apply changes
adafmt --project-path project.gpr --write
```

#### `--check`
**Purpose**: Check if files need formatting (exit code 1 if changes needed)
**Example**:
```bash
# CI/CD usage
adafmt --project-path project.gpr --check
if [ $? -ne 0 ]; then
    echo "Files need formatting"
    exit 1
fi
```

#### `--diff`
**Purpose**: Show unified diff of changes
**Example**:
```bash
adafmt --project-path project.gpr --diff
```

### User Interface

adafmt uses a plain text TTY UI that provides clear output with:
- Color-coded file status indicators
- Progress tracking during processing
- Detailed metrics summary
- Unified diffs for changes (controlled by `--diff`/`--no-diff`)

The UI automatically adapts to terminal capabilities and respects standard color environment variables like `NO_COLOR`.

### Timeout Configuration

#### `--init-timeout`
**Format**: `--init-timeout SECONDS`
**Default**: 180 seconds (3 minutes)
**Purpose**: How long to wait for ALS initialization
**Examples**:
```bash
# Large project
adafmt --project-path large_project.gpr --init-timeout 300

# Fast CI environment
adafmt --project-path project.gpr --init-timeout 60
```

#### `--format-timeout`
**Format**: `--format-timeout SECONDS`
**Default**: 60 seconds (1 minute)
**Purpose**: Timeout for individual file formatting
**Examples**:
```bash
# Complex files
adafmt --project-path project.gpr --format-timeout 120

# Quick formatting
adafmt --project-path project.gpr --format-timeout 30
```

#### `--max-consecutive-timeouts`
**Format**: `--max-consecutive-timeouts COUNT`
**Default**: 5
**Purpose**: Abort after this many consecutive timeouts (0 = no limit)
**Examples**:
```bash
# Strict timeout handling
adafmt --project-path project.gpr --max-consecutive-timeouts 2

# Lenient timeout handling
adafmt --project-path project.gpr --max-consecutive-timeouts 10

# No timeout limit
adafmt --project-path project.gpr --max-consecutive-timeouts 0
```

### Process Management

#### `--preflight`
**Format**: `--preflight MODE`
**Options**: `auto`, `warn`, `kill`, `aggressive`
**Default**: `auto`

| Mode | Behavior | Use Case |
|------|----------|----------|
| `auto` | Warn about existing processes | Normal use |
| `warn` | Only warn, don't clean up | Information only |
| `kill` | Kill stale processes (>30 min) | Clean up old processes |
| `aggressive` | Kill all user ALS processes | Force cleanup |

**Examples**:
```bash
# Normal cleanup
adafmt --project-path project.gpr --preflight kill

# Force cleanup of all ALS processes
adafmt --project-path project.gpr --preflight aggressive
```

### Logging and Debugging

#### `--log-path`
**Format**: `--log-path PATH`
**Purpose**: Path for JSONL debug log file
**Examples**:
```bash
# Basic logging
adafmt --project-path project.gpr --log-path debug.jsonl

# Timestamped logs
adafmt --project-path project.gpr --log-path "adafmt_$(date +%Y%m%d_%H%M%S).jsonl"
```

#### `--stderr-path`
**Format**: `--stderr-path PATH`
**Purpose**: Path for capturing ALS stderr output
**Examples**:
```bash
# Capture ALS errors
adafmt --project-path project.gpr --stderr-path als_errors.log

# Debug ALS issues
adafmt --project-path project.gpr \
    --stderr-path als_debug.log \
    --log-path debug.jsonl
```

### Pattern Formatter Options

#### `--patterns-path`
**Format**: `--patterns-path PATH`
**Default**: `./adafmt_patterns.json`
**Purpose**: Path to pattern file
**Examples**:
```bash
# Custom pattern file
adafmt --project-path project.gpr --patterns-path custom_patterns.json

# Disable patterns
adafmt --project-path project.gpr --no-patterns
```

#### `--patterns-timeout-ms`
**Format**: `--patterns-timeout-ms MS`
**Default**: 50ms
**Purpose**: Timeout per pattern application
**Examples**:
```bash
# Increase pattern timeout
adafmt --project-path project.gpr --patterns-timeout-ms 100
```

#### `--validate-patterns`
**Purpose**: Validate patterns don't conflict with ALS
**Examples**:
```bash
# Validate patterns before commit
adafmt --project-path project.gpr --validate-patterns
```

### Hooks

#### `--pre-hook`
**Format**: `--pre-hook "COMMAND"`
**Purpose**: Command to run before formatting (60s timeout)
**Behavior**: Non-zero exit aborts formatting
**Examples**:
```bash
# Git status check
adafmt --project-path project.gpr --pre-hook "git status --porcelain"

# Build verification
adafmt --project-path project.gpr --pre-hook "gprbuild -P project.gpr -c"
```

#### `--post-hook`
**Format**: `--post-hook "COMMAND"`
**Purpose**: Command to run after formatting (60s timeout)
**Behavior**: Non-zero exit is logged but doesn't abort
**Examples**:
```bash
# Git add changes
adafmt --project-path project.gpr --post-hook "git add -A" --write

# Run tests
adafmt --project-path project.gpr --post-hook "make test" --write
```

## 2. Environment Variables

### ALS Configuration

#### `ALS_HOME`
**Purpose**: Override Ada Language Server installation path
**Example**:
```bash
export ALS_HOME=/opt/ada_language_server
adafmt --project-path project.gpr
```

#### `GPR_PROJECT_PATH`
**Purpose**: Additional GNAT project search paths
**Example**:
```bash
export GPR_PROJECT_PATH=/usr/local/lib/gnat:/opt/ada/lib/gnat
adafmt --project-path project.gpr
```

### Development Environment

#### `DEBUG`
**Purpose**: Enable debug mode (more verbose output)
**Example**:
```bash
export DEBUG=1
adafmt --project-path project.gpr
```

#### `CI`
**Purpose**: Detected automatically, affects UI mode selection
**Effect**: Forces plain UI mode when set
**Example**:
```bash
export CI=true
adafmt --project-path project.gpr  # Uses plain UI automatically
```

## 3. Configuration Patterns

### Development Workflow

```bash
# Interactive development
adafmt --project-path project.gpr \
    --ui pretty \
    --diff \
    --log-path "dev_$(date +%Y%m%d_%H%M%S).jsonl"
```

### CI/CD Pipeline

```bash
# Fast CI check
adafmt --project-path project.gpr \
    --check \
    --ui plain \
    --init-timeout 60 \
    --format-timeout 30 \
    --max-consecutive-timeouts 2 \
    --preflight aggressive
```

### Large Project Processing

```bash
# Optimized for large codebases
adafmt --project-path large_project.gpr \
    --init-timeout 300 \
    --format-timeout 120 \
    --max-consecutive-timeouts 10 \
    --ui json \
    --write
```

### Debug Configuration

```bash
# Maximum debugging
adafmt --project-path project.gpr \
    --log-path debug.jsonl \
    --stderr-path als_stderr.log \
    --ui plain \
    --preflight aggressive
```

## 4. ALS Traces Configuration

### Overview

adafmt can configure Ada Language Server tracing for debugging ALS communication and performance issues.

### Default Traces Behavior

When `--als-traces-config-path` is not provided, adafmt automatically:

1. Creates a temporary directory with prefix `adafmt_als_`
2. Generates a default GNATCOLL traces configuration file
3. Configures ALS to log to `<temp_dir>/als.log`
4. Passes the config to ALS using `--tracefile=<config>`
5. Displays the ALS log path in the UI
6. Cleans up the temporary directory on exit

**Before**: "ALS Log: Not configured"  
**After**: "ALS Log: /var/folders/.../adafmt_als_xyz/als.log"

### Custom Traces Configuration

#### `--als-traces-config-path`
**Format**: `--als-traces-config-path PATH`
**Purpose**: Path to custom GNATCOLL traces configuration file
**Example**:
```bash
adafmt --project-path project.gpr --als-traces-config-path my_traces.conf
```

### Traces Configuration File Format

GNATCOLL traces configuration uses this format:

```ini
# Basic ALS logging
ALS.MAIN=yes

# Detailed LSP protocol logging
ALS.LSP=yes

# File system operations
ALS.FS=yes

# Custom log file location
>als_debug.log
```

### Common Traces Configurations

#### Basic Logging
```ini
# my_traces.conf
ALS.MAIN=yes
>als_basic.log
```

#### Detailed Protocol Logging
```ini
# debug_traces.conf
ALS.MAIN=yes
ALS.LSP=yes
ALS.PROTOCOL=yes
>als_detailed.log
```

#### Performance Analysis
```ini
# perf_traces.conf
ALS.MAIN=yes
ALS.TIMING=yes
ALS.MEMORY=yes
>als_performance.log
```

### Trace Levels and Performance Impact

| Level | Performance Impact | Information Provided |
|-------|-------------------|---------------------|
| `ALS.MAIN=yes` | Low | Basic operation info |
| `ALS.LSP=yes` | Moderate | LSP message details |
| `ALS.PROTOCOL=yes` | High | Full protocol messages |
| `ALS.TIMING=yes` | Low | Performance timing |
| `ALS.MEMORY=yes` | Moderate | Memory usage info |

### Using Traces for Debugging

#### ALS Communication Issues
```bash
# Enable protocol logging
cat > debug_traces.conf << EOF
ALS.MAIN=yes
ALS.LSP=yes
>als_protocol.log
EOF

adafmt --project-path project.gpr --als-traces-config-path debug_traces.conf
```

#### Performance Problems
```bash
# Enable timing analysis
cat > perf_traces.conf << EOF
ALS.MAIN=yes
ALS.TIMING=yes
>als_timing.log
EOF

adafmt --project-path project.gpr --als-traces-config-path perf_traces.conf
```

#### Analyzing Trace Output
```bash
# View ALS log
cat als_protocol.log | grep -i error

# Analyze timing
cat als_timing.log | grep -i "took"

# Count message types
cat als_protocol.log | grep "LSP:" | cut -d':' -f3 | sort | uniq -c
```

## 5. Performance Tuning

### Timeout Optimization

For different environments:

```bash
# Development (generous timeouts)
adafmt --project-path project.gpr \
    --init-timeout 300 \
    --format-timeout 120

# CI/CD (strict timeouts)
adafmt --project-path project.gpr \
    --init-timeout 60 \
    --format-timeout 30 \
    --max-consecutive-timeouts 2

# Large files (extended timeouts)
adafmt --project-path project.gpr \
    --format-timeout 180 \
    --max-consecutive-timeouts 0
```

### Process Management

```bash
# Clean environment
adafmt --project-path project.gpr --preflight aggressive

# Minimal cleanup
adafmt --project-path project.gpr --preflight warn
```

### Pattern Performance

```bash
# Faster pattern processing
adafmt --project-path project.gpr \
    --patterns-timeout-ms 25 \
    --patterns-max-bytes 1048576
```

## 6. Environment-Specific Setup

### Development Environment

```bash
# ~/.adafmt_dev
export DEBUG=1
export ALS_HOME=/usr/local/ada_language_server

# Development alias
alias adafmt-dev='adafmt --ui pretty --diff --log-path dev.jsonl'
```

### CI/CD Environment

```bash
# GitHub Actions
- name: Format Ada code
  run: |
    adafmt --project-path project.gpr \
           --check \
           --ui plain \
           --init-timeout 60 \
           --format-timeout 30 \
           --preflight aggressive
```

### Docker Environment

```dockerfile
# Dockerfile
FROM ada-base
RUN pip install adafmt
ENV CI=true
CMD ["adafmt", "--project-path", "project.gpr", "--ui", "plain"]
```

## 7. Common Configuration Issues

### "Invalid project file"

**Check project path:**
```bash
# Verify file exists
ls -la project.gpr

# Use absolute path
adafmt --project-path "$(pwd)/project.gpr"
```

### "Timeouts still occurring"

**Progressive timeout increases:**
```bash
# Step 1: Increase init timeout
adafmt --project-path project.gpr --init-timeout 300

# Step 2: Increase format timeout
adafmt --project-path project.gpr --format-timeout 120

# Step 3: Remove consecutive limit
adafmt --project-path project.gpr --max-consecutive-timeouts 0
```

### "ALS not found"

**Check ALS installation:**
```bash
# Verify ALS is in PATH
which ada_language_server

# Set custom ALS location
export ALS_HOME=/path/to/als
adafmt --project-path project.gpr
```

### "Patterns not working"

**Debug pattern issues:**
```bash
# Check pattern file
jq . adafmt_patterns.json

# Validate patterns
adafmt --project-path project.gpr --validate-patterns

# Disable patterns temporarily
adafmt --project-path project.gpr --no-patterns
```

## 8. Debugging Configuration

### Enable Full Debugging

```bash
# Maximum debug information
export DEBUG=1
adafmt --project-path project.gpr \
    --log-path debug.jsonl \
    --stderr-path als_stderr.log \
    --als-traces-config-path debug_traces.conf \
    --ui plain
```

### Analyze Configuration Issues

```bash
# Check parsed configuration
cat debug.jsonl | jq 'select(.type == "config")'

# Verify ALS startup
cat debug.jsonl | jq 'select(.type == "als_init")'

# Check timeout patterns
cat debug.jsonl | jq 'select(.status == "timeout")'
```

### Test Configuration

```bash
# Test with minimal project
echo 'project Test is end Test;' > test.gpr
echo 'procedure Main is begin null; end Main;' > main.adb
adafmt --project-path test.gpr main.adb
```

## Best Practices

### Configuration Management

1. **Use consistent timeouts** across environments
2. **Enable logging** for troubleshooting
3. **Use preflight cleanup** in CI/CD
4. **Validate patterns** before deployment
5. **Monitor ALS performance** with traces

### Security Considerations

1. **Validate all paths** are absolute
2. **Don't log sensitive information**
3. **Use secure temp directories** for traces
4. **Limit hook command execution**

### Performance Guidelines

1. **Start with default timeouts** and adjust as needed
2. **Use aggressive preflight** in CI/CD
3. **Monitor pattern performance** with logs
4. **Consider file size limits** for large projects

## See Also

- [Getting Started Guide](getting-started-guide.md) - Basic usage examples
- [Troubleshooting Guide](troubleshooting-guide.md) - Specific problem solutions
- [Timeout Guide](timeout-guide.md) - Detailed timeout configuration
- [Pattern Guide](patterns-guide.md) - Pattern configuration and usage