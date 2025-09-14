# Configuration Reference

**Version:** 1.0.0  
**Last Updated:** January 2025

This document provides a complete reference for all adafmt configuration options, including command-line arguments, environment variables, and configuration best practices.

## Command-Line Arguments

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

#### `--ui`
**Format**: `--ui MODE`  
**Options**: `auto`, `pretty`, `plain`, `json`, `quiet`  
**Default**: `auto`

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` | Automatically select UI based on terminal | General use |
| `pretty` | Rich UI with progress bars and colors | Interactive terminals |
| `plain` | Simple text output | Basic terminals, logs |
| `json` | JSON Lines output | Scripting, integration |
| `quiet` | Minimal output | Automated scripts |

**Examples**:
```bash
# Interactive use
adafmt --project-path project.gpr --ui pretty

# CI/CD use  
adafmt --project-path project.gpr --ui plain

# Scripting use
adafmt --project-path project.gpr --ui json
```

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
# Clean up before formatting
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

## Environment Variables

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

## Configuration Patterns

### Development Environment
```bash
# Interactive development with comprehensive logging
adafmt --project-path project.gpr \
    --ui pretty \
    --log-path dev_debug.jsonl \
    --pre-hook "git status --porcelain" \
    --post-hook "git add -A" \
    --write
```

### CI/CD Environment
```bash
# Fast, strict CI/CD formatting check
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
# Optimized for large projects
adafmt --project-path large_project.gpr \
    --init-timeout 300 \
    --format-timeout 120 \
    --max-consecutive-timeouts 10 \
    --ui json \
    --log-path large_project_format.jsonl \
    --write
```

### Debugging ALS Issues
```bash
# Maximum debugging information
adafmt --project-path project.gpr \
    --log-path debug.jsonl \
    --stderr-path als_stderr.log \
    --ui plain \
    --init-timeout 600 \
    --format-timeout 180 \
    --preflight aggressive
```

## Configuration Files

*Note: adafmt currently uses command-line configuration only. Configuration file support may be added in future versions.*

### Planned Configuration File Format

```toml
# .adafmt.toml (future feature)
[adafmt]
project_path = "project.gpr"
include_paths = ["src", "lib"]
exclude_paths = ["build", "generated"]

[ui]
mode = "auto"
show_diff = false

[timeouts]
init = 180
format = 60
max_consecutive = 5

[hooks]
pre = "git status --porcelain"  
post = "git add -A"

[logging]
log_path = "adafmt.jsonl"
stderr_path = "als_stderr.log"
```

## Best Practices

### General Configuration
1. **Start Simple**: Begin with minimal configuration and add options as needed
2. **Environment-Specific**: Use different settings for development vs CI/CD
3. **Document Settings**: Keep a record of working configurations for your projects
4. **Monitor Performance**: Use logging to identify performance bottlenecks

### Timeout Configuration
1. **Conservative Defaults**: Start with longer timeouts and reduce based on experience
2. **Environment Tuning**: Adjust timeouts based on system performance characteristics
3. **Consecutive Limits**: Set reasonable consecutive timeout limits to avoid hanging

### Hook Configuration
1. **Pre-hook Validation**: Use pre-hooks for validation that should prevent formatting
2. **Post-hook Actions**: Use post-hooks for actions that should happen regardless
3. **Timeout Awareness**: Remember that hooks have a 60-second timeout

### CI/CD Configuration
1. **Fail Fast**: Use shorter timeouts and strict consecutive limits
2. **Plain Output**: Use plain or JSON UI modes for log parsing
3. **Check Mode**: Use `--check` to validate formatting without changes
4. **Process Cleanup**: Use `--preflight aggressive` to ensure clean state

## Troubleshooting Configuration

### Common Issues

#### "Configuration Not Applied"
- Verify command-line argument syntax
- Check for conflicting options
- Use `--log-path` to debug configuration parsing

#### "Timeouts Still Occurring"
- Review [Timeout Configuration Guide](timeout-guide.md)
- Check system resources and ALS performance
- Consider increasing timeout values or investigating root causes

#### "Hooks Not Running"  
- Verify hook command syntax and permissions
- Check that commands are in PATH
- Use logging to debug hook execution

### Getting Help

For configuration issues:
1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review [Timeout Configuration](timeout-guide.md) for timeout-specific issues
3. Use `--log-path` for detailed debugging information
4. Create GitHub issue with configuration details and logs

## See Also

- [Troubleshooting Guide](troubleshooting.md) - Solutions to common issues
- [Timeout Configuration](timeout-guide.md) - Detailed timeout tuning guide  
- [API Reference](../api/cli.md) - Technical CLI implementation details
- [Developer Guide](../developer/index.md) - Development and customization

---

*Configuration documentation is updated with each release. For the latest options, run `adafmt --help`.*