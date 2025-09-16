# adafmt Command-Line Guide

This guide explains how to use adafmt effectively, including common use cases, command-line options, and important restrictions.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Common Use Cases](#common-use-cases)
4. [Command-Line Options](#command-line-options)
5. [Invalid Option Combinations](#invalid-option-combinations)
6. [Path Requirements](#path-requirements)
7. [Exit Codes](#exit-codes)
8. [Examples](#examples)

## Quick Start

The simplest way to use adafmt is to format Ada files in specific directories:

```bash
# Format all Ada files in /src and /tests directories (dry-run by default)
adafmt format --project-path /path/to/project.gpr --include-path /src --include-path /tests

# Actually write the changes
adafmt format --project-path /path/to/project.gpr --include-path /src --include-path /tests --write

# Check if files need formatting (useful for CI)
adafmt format --project-path /path/to/project.gpr --include-path /src --check
```

## Basic Usage

```bash
adafmt format --project-path PROJECT_PATH [OPTIONS] [FILES]...
```

**Required:**
- `--project-path PATH`: Absolute path to your GNAT project file (.gpr)

**Input Sources (at least one required):**
- `--include-path PATH`: Directory to search for Ada files (can be repeated)
- `FILES...`: Specific Ada files to format

## Common Use Cases

### 1. Format Entire Project
```bash
adafmt format --project-path /home/user/myproject.gpr \
    --include-path /home/user/src \
    --include-path /home/user/tests \
    --write
```

### 2. Check Formatting in CI/CD
```bash
# Exit with code 1 if any files need formatting
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --check
```

### 3. Format Specific Files
```bash
adafmt format --project-path /project/app.gpr \
    /project/src/main.adb \
    /project/src/utils.ads \
    --write
```

### 4. Preview Changes with Diffs
```bash
# Default behavior shows diffs without making changes
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --diff
```

### 5. Format with Custom Patterns
```bash
# Apply additional formatting patterns after ALS
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --patterns-path /project/my_patterns.json \
    --write
```

### 6. ALS-Only Mode (No Patterns)
```bash
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --no-patterns \
    --write
```

### 7. Patterns-Only Mode (No ALS)
```bash
# Skip ALS formatting, only apply custom patterns
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --no-als \
    --write
```

## Command-Line Options

### File Selection
| Option | Description | Example |
|--------|-------------|---------|
| `--include-path PATH` | Add directory to search (recursive) | `--include-path /src` |
| `--exclude-path PATH` | Exclude directory from search | `--exclude-path /src/generated` |
| `FILES...` | Format specific files | `main.adb utils.ads` |

### Output Modes
| Option | Description | Default |
|--------|-------------|---------|
| `--write` | Apply changes to files | No (dry-run) |
| `--check` | Exit 1 if changes needed | No |
| `--diff` | Show unified diffs | Yes |
| `--no-diff` | Hide diffs | No |

### UI Modes
| Option | Description | When to Use |
|--------|-------------|-------------|
| `--ui auto` | Automatic selection (default) | General use |
| `--ui pretty` | Rich terminal UI with colors | Interactive terminals |
| `--ui plain` | Minimal output | Scripts, CI/CD |
| `--ui off` | Only errors and diffs | Automation |

### Pattern Control
| Option | Description | Default |
|--------|-------------|---------|
| `--patterns-path FILE` | Custom patterns file | `./adafmt_patterns.json` |
| `--no-patterns` | Disable all patterns | Patterns enabled |
| `--no-als` | Skip ALS, patterns only | ALS enabled |
| `--validate-patterns` | Check patterns vs ALS | No validation |

### Advanced Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format-timeout N` | Per-file timeout (seconds) | 60 |
| `--log-path PATH` | JSONL log location | `./adafmt_TIMESTAMP_log.jsonl` |
| `--preflight MODE` | Handle existing ALS | `safe` |

## Invalid Option Combinations

Some command-line options cannot be used together. The table below shows invalid combinations and what happens when you try to use them:

| Cannot Combine | With | Why | Error Message |
|----------------|------|-----|---------------|
| `--no-als` | `--no-patterns` | Nothing would be done | "Cannot use both --no-patterns and --no-als (nothing to do)" |
| `--validate-patterns` | `--no-als` | Validation needs ALS | "Cannot use --validate-patterns with --no-als (validation requires ALS)" |
| `--validate-patterns` | `--no-patterns` | No patterns to validate | "Cannot use --validate-patterns with --no-patterns (no patterns to validate)" |
| `--write` | `--check` | Conflicting output modes | "Cannot use both --write and --check modes" |
| No paths/files | - | Nothing to process | "No files or directories to process. You must provide --include-path or specific files." |

## Path Requirements

All paths provided to adafmt must meet strict requirements for security and compatibility:

### 1. Path Resolution
Both absolute and relative paths are accepted. Relative paths are resolved based on the current working directory.

```bash
# ✅ Both styles work
--include-path /home/user/project/src    # Absolute path
--include-path ./src                      # Relative path (resolved to current directory)
--include-path ../project/src             # Relative path (resolved from current directory)
```

### 2. Cannot Contain Whitespace
```bash
# ❌ Bad - spaces in path
--include-path "/home/user/My Projects/src"

# ✅ Good - use underscores or hyphens
--include-path /home/user/my-projects/src
```

### 3. Allowed Characters Only
Paths may only contain:
- Letters (A-Z, a-z)
- Numbers (0-9)
- Special characters: `?` `&` `=` `.` `_` `:` `/` `-`

```bash
# ❌ Bad - brackets not allowed
--include-path /home/user/project[v2]/src

# ✅ Good
--include-path /home/user/project_v2/src
```

### 4. No Directory Traversal
```bash
# ❌ Bad - contains ..
--include-path /home/user/../other/src

# ✅ Good - use full path
--include-path /home/other/src
```

### 5. No Unicode Beyond Basic Multilingual Plane
```bash
# ❌ Bad - emoji in path
--include-path /home/user/project😀/src

# ✅ Good - ASCII only
--include-path /home/user/project/src
```

## Exit Codes

adafmt uses specific exit codes to indicate results:

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | All operations completed successfully |
| 1 | Changes needed | Used with `--check` when formatting would change files |
| 2 | Error | Invalid options, path validation failure, or processing errors |

## Examples

### Example 1: Typical Development Workflow
```bash
# 1. Check what would change (dry-run with diffs)
adafmt format --project-path /workspace/myapp.gpr \
    --include-path /workspace/src \
    --include-path /workspace/tests

# 2. If changes look good, apply them
adafmt format --project-path /workspace/myapp.gpr \
    --include-path /workspace/src \
    --include-path /workspace/tests \
    --write
```

### Example 2: CI/CD Integration
```bash
#!/bin/bash
# In your CI pipeline

# Check if code is properly formatted
if ! adafmt format --project-path "$PROJECT_ROOT/app.gpr" \
    --include-path "$PROJECT_ROOT/src" \
    --include-path "$PROJECT_ROOT/tests" \
    --check --ui off; then
    echo "ERROR: Code is not properly formatted. Run 'adafmt format --write' locally."
    exit 1
fi
```

### Example 3: Custom Patterns with Validation
```bash
# First, validate that patterns don't conflict with ALS
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --patterns-path /project/team_patterns.json \
    --validate-patterns

# If validation passes, format with patterns
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --patterns-path /project/team_patterns.json \
    --write
```

### Example 4: Debugging Format Issues
```bash
# Use verbose logging to debug
adafmt format --project-path /project/app.gpr \
    --include-path /project/src \
    --log-path /tmp/adafmt_debug.jsonl \
    --ui plain

# Check the log file for details
cat /tmp/adafmt_debug.jsonl | jq '.'
```

## Tips and Best Practices

1. **Start with Dry-Run**: Always run without `--write` first to preview changes
2. **Use Absolute Paths**: All paths must be absolute - use `$PWD` or `$(pwd)` if needed
3. **Check in CI**: Use `--check` mode in CI/CD to enforce formatting
4. **Save Logs**: Use `--log-path` when debugging issues
5. **Validate Patterns**: Always use `--validate-patterns` when creating new pattern files

## Getting Help

```bash
# Show detailed help
adafmt format --help

# Show version
adafmt --version

# Report issues
# https://github.com/abitofhelp/adafmt/issues
```