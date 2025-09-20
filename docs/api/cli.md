# cli Module

**Version:** 1.0.1
**Date:** 2025-09-20T00:23:54.445021Z
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `cli` module provides the main command-line interface for adafmt using the Typer framework.

## Overview

This module implements a modern, user-friendly CLI with:
- Rich help text and command documentation
- Plain text TTY output with color support
- Comprehensive error handling
- Progress tracking and reporting
- Hook system for extensibility

## Functions

### main()

```python
def main(
    project_path: Path = typer.Option(...),
    include_paths: Optional[List[Path]] = typer.Option(None),
    exclude_paths: Optional[List[Path]] = typer.Option(None),
    check: bool = typer.Option(False),
    write: bool = typer.Option(False),
    diff: bool = typer.Option(False),
    log_level: str = typer.Option("info"),
    log_path: Optional[Path] = typer.Option(None),
    fail_on_error: bool = typer.Option(True),
    workers: int = typer.Option(1),
    version: bool = typer.Option(False)
) -> None:
    """Format Ada source files using the Ada Language Server.

    This is the main entry point for the adafmt command-line tool.
    It discovers Ada files, connects to ALS, and applies formatting.

    Args:
        project_path: Path to GNAT project file (.gpr)
        include_paths: Directories to search for Ada files
        exclude_paths: Directories to exclude from search
        check: Check mode - exit with error if files need formatting
        write: Write formatted files back to disk
        diff: Show unified diff of changes
        log_level: Logging verbosity (debug/info/warning/error)
        log_path: Path for JSONL log file
        fail_on_error: Exit with error code on any formatting failure
        workers: Number of concurrent workers (currently limited to 1)
        version: Show version and exit

    Returns:
        None (exits with appropriate code)

    Exit Codes:
        0: Success - all files formatted
        1: Check mode - files need formatting
        2: Error - formatting failed

    Example:
        $ adafmt --project-path project.gpr --include-path src/ --write
        $ adafmt --project-path project.gpr --check --no-diff
    """
```

### run_formatting()

```python
async def run_formatting(
    config: FormattingConfig,
    ui: UserInterface,
    logger: JsonlLogger
) -> FormattingResult:
    """Execute the main formatting workflow.

    This function orchestrates the entire formatting process:
    1. Discover Ada files
    2. Start ALS client
    3. Format each file
    4. Apply edits if requested
    5. Report results

    Args:
        config: Formatting configuration
        ui: User interface instance
        logger: Logger for debugging

    Returns:
        FormattingResult with statistics and exit code

    Raises:
        ALSStartupError: If ALS fails to start
        Exception: For unexpected errors
    """
```

## Configuration

### FormattingConfig

```python
@dataclass
class FormattingConfig:
    """Configuration for formatting operation.

    Attributes:
        project_path: Path to GNAT project file
        include_paths: Directories to include
        exclude_paths: Directories to exclude
        check: Enable check mode
        write: Enable write mode
        diff: Show diffs
        fail_on_error: Strict error handling
    """
```

### Output Format

The CLI uses a plain text TTY output format that:
- Displays color-coded status indicators (changed, unchanged, failed)
- Shows progress during processing
- Provides comprehensive metrics at completion
- Respects NO_COLOR environment variable
- Works in all terminal types

#### Metrics Display Modes

- **Default (both ALS and patterns)**: Shows both ALS METRICS and PATTERN METRICS sections
- **ALS-only mode (`--no-patterns`)**: Shows only ALS METRICS section
- **Patterns-only mode (`--no-als`)**: Shows only PATTERN METRICS section

Note: Pattern metrics differ between combined and patterns-only modes because ALS fixes many issues first in combined mode.

## User Interface

### Terminal Detection

The output adapts to terminal capabilities:
1. TTY detection: `sys.stdout.isatty()`
2. NO_COLOR environment variable
3. Terminal type and capabilities

```python
def detect_terminal_capabilities():
    """Detect terminal capabilities for color support."""
    if not sys.stdout.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    return True
```

### Progress Reporting

Progress is reported using a plain text format:

```
[discovery] Starting file discovery...
[discovery] Found 51 Ada files to format
[formatter] Starting to format files...
[   1/51] [changed] src/main.adb | ALS: ✓ edits=5
[   2/51] [  ok   ] src/utils.ads | ALS: ✓ edits=0
[   3/51] [failed ] src/broken.adb | ALS: ✓ edits=0 (details in stderr log)
```

Status indicators:
- `[changed]` - File was modified (yellow)
- `[  ok   ]` - File unchanged (green)
- `[failed ]` - Processing failed (red)

## Error Handling

### Error Categories

1. **Startup Errors**: ALS process failures
2. **File Errors**: Permission, I/O issues
3. **Protocol Errors**: LSP communication failures
4. **Validation Errors**: Invalid project files

### Error Recovery

```python
try:
    edits = await client.format_file(file_path)
except ALSProtocolError as e:
    if config.fail_on_error:
        raise
    else:
        ui.report_error(file_path, str(e))
        continue
```

## Hook System

### Available Hooks

1. **pre-format**: Before formatting each file
2. **post-format**: After formatting each file
3. **pre-write**: Before writing changes
4. **error**: On formatting errors

### Hook Configuration

```yaml
# .adafmt.yaml
hooks:
  pre-format: "echo 'Formatting {file}'"
  post-format: "git add {file}"
  error: "notify-send 'Format failed: {error}'"
```

### Hook Execution

```python
def run_hook(name: str, context: Dict[str, Any]) -> None:
    """Execute a configured hook command.

    Args:
        name: Hook name (pre-format, post-format, etc.)
        context: Variables available to the hook

    Example:
        run_hook("pre-format", {"file": "src/main.adb"})
    """
```

## Logging

### Log Levels

- **DEBUG**: Detailed protocol messages
- **INFO**: Progress and results
- **WARNING**: Recoverable issues
- **ERROR**: Failures and exceptions

### Log Output

JSONL format for structured analysis:
```json
{"timestamp": "2025-01-14T10:23:45.123Z", "level": "INFO", "event": "format_start", "file": "src/main.adb"}
{"timestamp": "2025-01-14T10:23:45.234Z", "level": "DEBUG", "event": "als_request", "method": "textDocument/formatting"}
{"timestamp": "2025-01-14T10:23:45.345Z", "level": "INFO", "event": "format_complete", "file": "src/main.adb", "edits": 5}
```

## Performance

### Optimization Strategies

1. **Batch Processing**: Group files to minimize ALS restarts
2. **Early Exit**: Stop on first error in check mode
3. **Parallel Discovery**: Concurrent file system traversal
4. **Memory Efficiency**: Stream large files

### Benchmarking

Enable timing information:
```bash
adafmt --project-path project.gpr --log-level debug
```

## Integration

### Git Integration

Pre-commit hook example:
```bash
#!/bin/bash
adafmt --project-path project.gpr --check || {
    echo "Ada files need formatting. Run: adafmt --write"
    exit 1
}
```

### CI/CD Integration

GitHub Actions:
```yaml
- name: Check Ada formatting
  run: |
    pip install adafmt
    adafmt --project-path project.gpr --check
```

### Editor Integration

VS Code task:
```json
{
    "label": "Format Ada",
    "type": "shell",
    "command": "adafmt",
    "args": ["--project-path", "${workspaceFolder}/project.gpr", "--write"],
    "problemMatcher": []
}
```

## Best Practices

1. **Use Check Mode in CI**: Ensure consistent formatting
2. **Enable Logging for Debugging**: `--log-path debug.jsonl`
3. **Exclude Generated Files**: Use `--exclude-path`
4. **Check Terminal Support**: Colors work automatically
5. **Handle Errors Gracefully**: Consider `--no-fail-on-error`

## See Also

- [CLI Design Philosophy](../DEVELOPER_GUIDE.md#cli-design)
- [User Interface Module](./tui.md)
- [Configuration Guide](../README.md#configuration)
