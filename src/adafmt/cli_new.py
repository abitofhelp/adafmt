# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Modern CLI interface using multi-command architecture with functional error handling.

This module implements the new CLI design with:
- Proper separation of concerns via command processors
- Functional error handling using Result types
- Decorator pattern for automatic exception handling
- Dependency injection principle compliance
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Optional, List

import typer
from typing_extensions import Annotated

from returns.io import IOFailure, IOResult, IOSuccess, impure_safe
from returns.future import future_safe
from returns.result import Failure, Result

from .commands.format_command import FormatCommandProcessor, FormatArgs
from .commands.rename_command import RenameCommandProcessor, RenameArgs
from .core.base_command import CommandProcessor
from .errors import AdafmtError, ConfigError
from .cli_helpers import APP_VERSION, read_license_text, version_callback


# Create the main Typer app
app = typer.Typer(
    name="adafmt",
    help="Ada Language Formatter - Modern CLI with functional error handling",
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_enable=False,
)


@app.callback(invoke_without_command=False)
def main_callback(
    version: Annotated[Optional[bool], typer.Option("--version", "-v", callback=version_callback, help="Show version and exit")] = None
) -> None:
    """Print header for all commands."""
    print("=" * 80)
    print(f"Ada Formatter  {APP_VERSION}")
    print("=" * 80)


def _execute_command_sync(command_processor: CommandProcessor, args: Any) -> IOResult[int, Exception]:
    """Execute command processor synchronously.
    
    Args:
        command_processor: The command processor to execute
        args: Command arguments
        
    Returns:
        IOResult[int, Exception]: Exit code wrapped in IOResult
    """
    # Run async command in sync context
    async def run_command():
        return await _execute_command_async(command_processor, args)
    
    # Run the coroutine and get the IOResult from @future_safe
    return asyncio.run(run_command())


@future_safe
async def _execute_command_async(command_processor: CommandProcessor, args: Any) -> int:
    """Execute command processor asynchronously with automatic exception handling.
    
    Args:
        command_processor: The command processor to execute
        args: Command arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
        
    Note:
        @future_safe automatically converts exceptions to IOResult[int, Exception]
    """
    # Execute the command using the template method pattern
    result = await command_processor.execute(args)
    
    if isinstance(result, Failure):
        error = result.failure()
        print(f"Error: {error}", file=sys.stderr)
        return 1
    
    return result.unwrap()


def _handle_command_result(result: Result[int, Exception] | IOResult[int, Exception]) -> int:
    """Handle command execution result with proper error mapping.
    
    Args:
        result: Result from command execution
        
    Returns:
        int: Exit code
    """
    # Handle IOResult from @impure_safe decorators
    if isinstance(result, IOFailure):
        error = result.failure()
        
        # Map different error types to appropriate exit codes
        if isinstance(error, AdafmtError):
            print(f"Error: {error.message}", file=sys.stderr)
            return 1
        elif isinstance(error, ConfigError):
            print(f"Configuration error: {error.message}", file=sys.stderr)
            return 2
        else:
            print(f"Unexpected error: {error}", file=sys.stderr)
            return 3
    elif isinstance(result, IOSuccess):
        # Extract the exit code using unsafe_perform_io
        from returns.unsafe import unsafe_perform_io
        return unsafe_perform_io(result.unwrap())
    
    # Handle regular Result types (legacy/fallback)
    elif isinstance(result, Failure):
        error = result.failure()
        
        # Map different error types to appropriate exit codes
        if isinstance(error, AdafmtError):
            print(f"Error: {error.message}", file=sys.stderr)
            return 1
        elif isinstance(error, ConfigError):
            print(f"Configuration error: {error.message}", file=sys.stderr)
            return 2
        else:
            print(f"Unexpected error: {error}", file=sys.stderr)
            return 3
    
    # Must be Success type
    return result.unwrap()  # type: ignore[return-value]


@app.command("license", help="Show the project's license text (BSD-3-Clause).")
def license_command() -> None:
    """Show the BSD-3-Clause license text."""
    try:
        license_text = read_license_text()
        typer.echo(license_text, color=False)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="format")
def format_command(
    project_path: Annotated[Path, typer.Option("--project-path", help="Path to your GNAT project file (.gpr)")],
    als_ready_timeout: Annotated[int, typer.Option("--als-ready-timeout", help="Maximum seconds to wait for ALS to become ready")] = 10,
    als_stale_minutes: Annotated[int, typer.Option("--als-stale-minutes", help="Age threshold in minutes for considering ALS processes stale")] = 30,
    check: Annotated[bool, typer.Option("--check", help="Exit with code 1 if any files need formatting")] = False,
    debug_als: Annotated[bool, typer.Option("--debug-als", help="Enable ALS debugging (uses default path if --debug-als-path not set)")] = False,
    debug_als_path: Annotated[Optional[Path], typer.Option("--debug-als-path", help="Write ALS debug output to this path")] = None,
    debug_patterns: Annotated[bool, typer.Option("--debug-patterns", help="Enable pattern debugging (uses default path if --debug-patterns-path not set)")] = False,
    debug_patterns_path: Annotated[Optional[Path], typer.Option("--debug-patterns-path", help="Write pattern debug output to this path")] = None,
    diff: Annotated[bool, typer.Option("--diff", help="Show unified diffs of changes")] = False,
    exclude_path: Annotated[Optional[List[Path]], typer.Option("--exclude-path", help="Directory to exclude from search (can be used multiple times)")] = None,
    format_timeout: Annotated[int, typer.Option("--format-timeout", help="Timeout per file formatting in seconds")] = 60,
    hook_timeout: Annotated[int, typer.Option("--hook-timeout", help="Timeout for hook commands in seconds")] = 5,
    include_path: Annotated[Optional[List[Path]], typer.Option("--include-path", help="Directory to search for Ada files (can be used multiple times)")] = None,
    init_timeout: Annotated[int, typer.Option("--init-timeout", help="Timeout for ALS initialization in seconds")] = 180,
    log_path: Annotated[Optional[Path], typer.Option("--log-path", help="Override JSONL log location (default: ./adafmt_<timestamp>_log.jsonl)")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", help="Retry attempts for transient errors")] = 2,
    max_consecutive_timeouts: Annotated[int, typer.Option("--max-consecutive-timeouts", help="Abort after this many timeouts in a row (0 = no limit)")] = 5,
    max_file_size: Annotated[int, typer.Option("--max-file-size", help="Skip files larger than this size in bytes (default: 102400 = 100KB)")] = 102400,
    metrics_path: Annotated[Optional[Path], typer.Option("--metrics-path", help="Path to cumulative metrics file (default: ~/.adafmt/metrics.jsonl)")] = None,
    no_als: Annotated[bool, typer.Option("--no-als", help="Disable ALS formatting (patterns only)")] = False,
    no_patterns: Annotated[bool, typer.Option("--no-patterns", help="Disable pattern processing")] = False,
    num_workers: Annotated[Optional[int], typer.Option("--num-workers", help="Number of parallel workers for post-ALS processing (default: 1)")] = None,
    patterns_max_bytes: Annotated[int, typer.Option("--patterns-max-bytes", help="Skip patterns for files larger than this (bytes)")] = 10485760,
    patterns_path: Annotated[Optional[Path], typer.Option("--patterns-path", help="Path to patterns JSON file (default: ./adafmt_patterns.json)")] = None,
    patterns_timeout_ms: Annotated[int, typer.Option("--patterns-timeout-ms", help="Timeout per pattern in milliseconds")] = 100,
    post_hook: Annotated[Optional[str], typer.Option("--post-hook", help="Command to run after formatting; non-zero exit is logged.")] = None,
    pre_hook: Annotated[Optional[str], typer.Option("--pre-hook", help="Command to run before formatting; non-zero exit aborts.")] = None,
    preflight: Annotated[str, typer.Option("--preflight", help="Handle existing ALS processes and .als-alire locks")] = "safe",
    stderr_path: Annotated[Optional[Path], typer.Option("--stderr-path", help="Override stderr capture location (default: ./adafmt_<timestamp>_stderr.log)")] = None,
    validate_patterns: Annotated[bool, typer.Option("--validate-patterns", help="Validate that applied patterns are acceptable to ALS")] = False,
    write: Annotated[bool, typer.Option("--write", help="Apply changes to files")] = False,
    files: Annotated[Optional[List[str]], typer.Argument(help="Specific Ada files to format")] = None,
) -> None:
    """Format Ada source code using the Ada Language Server (ALS)."""
    
    # Create arguments object
    args = FormatArgs(
        project_path=project_path,
        als_ready_timeout=als_ready_timeout,
        als_stale_minutes=als_stale_minutes,
        check=check,
        debug_als=debug_als,
        debug_als_path=debug_als_path,
        debug_patterns=debug_patterns,
        debug_patterns_path=debug_patterns_path,
        diff=diff,
        exclude_path=exclude_path or [],
        format_timeout=format_timeout,
        hook_timeout=hook_timeout,
        include_path=include_path or [],
        init_timeout=init_timeout,
        log_path=log_path,
        max_attempts=max_attempts,
        max_consecutive_timeouts=max_consecutive_timeouts,
        max_file_size=max_file_size,
        metrics_path=metrics_path,
        no_als=no_als,
        no_patterns=no_patterns,
        num_workers=num_workers,
        patterns_max_bytes=patterns_max_bytes,
        patterns_path=patterns_path,
        patterns_timeout_ms=patterns_timeout_ms,
        post_hook=post_hook,
        pre_hook=pre_hook,
        preflight=preflight,
        stderr_path=stderr_path,
        validate_patterns=validate_patterns,
        write=write,
        files=[Path(f) for f in files] if files else [],
    )
    
    # Create command processor
    processor = FormatCommandProcessor()
    
    # Execute command with functional error handling
    # _execute_command_sync returns IOResult[int, Exception] due to @impure_safe
    result = _execute_command_sync(processor, args)
    exit_code = _handle_command_result(result)
    
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command(name="rename")
def rename_command(
    project_path: Annotated[Path, typer.Option("--project-path", help="Path to your GNAT project file (.gpr)")],
    old_name: Annotated[str, typer.Option("--old-name", help="Current identifier name")],
    new_name: Annotated[str, typer.Option("--new-name", help="New identifier name")],
    include_path: Annotated[Optional[List[Path]], typer.Option("--include-path", help="Directory to search for Ada files (can be used multiple times)")] = None,
    exclude_path: Annotated[Optional[List[Path]], typer.Option("--exclude-path", help="Directory to exclude from search (can be used multiple times)")] = None,
    check: Annotated[bool, typer.Option("--check", help="Preview changes without applying them")] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Show unified diffs of changes")] = False,
    files: Annotated[Optional[List[str]], typer.Argument(help="Specific Ada files to process")] = None,
) -> None:
    """Rename Ada identifiers across multiple files."""
    
    # Create arguments object
    args = RenameArgs(
        project_path=project_path,
        old_name=old_name,
        new_name=new_name,
        include_path=include_path or [],
        exclude_path=exclude_path or [],
        check=check,
        diff=diff,
        files=[Path(f) for f in files] if files else [],
    )
    
    # Create command processor
    processor = RenameCommandProcessor()
    
    # Execute command with functional error handling
    # _execute_command_sync returns IOResult[int, Exception] due to @impure_safe
    result = _execute_command_sync(processor, args)
    exit_code = _handle_command_result(result)
    
    if exit_code != 0:
        raise typer.Exit(exit_code)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()