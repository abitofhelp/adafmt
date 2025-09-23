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

from returns.io import IOResult, impure_safe
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


@impure_safe
def _execute_command_sync(command_processor: CommandProcessor, args: Any) -> int:
    """Execute command processor synchronously with automatic exception handling.
    
    Args:
        command_processor: The command processor to execute
        args: Command arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
        
    Note:
        @impure_safe automatically converts exceptions to IOResult[int, Exception]
    """
    # Run async command in sync context
    # _execute_command_async is decorated with @future_safe, so we need to await it
    async def run_command():
        return await _execute_command_async(command_processor, args)
    
    # Run the coroutine and get the IOResult
    result = asyncio.run(run_command())
    
    # Handle the IOResult returned by @future_safe
    return _handle_command_result(result)


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
    if isinstance(result, Failure):
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
    als_stale_minutes: Annotated[int, typer.Option("--als-stale-minutes", help="Age threshold in minutes for considering ALS processes stale")] = 30,
    check: Annotated[bool, typer.Option("--check", help="Exit with code 1 if any files need formatting")] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Show unified diffs of changes")] = False,
    exclude_path: Annotated[Optional[List[Path]], typer.Option("--exclude-path", help="Directory to exclude from search (can be used multiple times)")] = None,
    format_timeout: Annotated[int, typer.Option("--format-timeout", help="Timeout per file formatting in seconds")] = 60,
    include_path: Annotated[Optional[List[Path]], typer.Option("--include-path", help="Directory to search for Ada files (can be used multiple times)")] = None,
    init_timeout: Annotated[int, typer.Option("--init-timeout", help="Timeout for ALS initialization in seconds")] = 180,
    write: Annotated[bool, typer.Option("--write", help="Apply changes to files")] = False,
    # Missing parameters that integration tests expect
    preflight: Annotated[str, typer.Option("--preflight", help="ALS preflight mode (off, warn, safe, kill, aggressive, fail)")] = "check",
    als_ready_timeout: Annotated[int, typer.Option("--als-ready-timeout", help="Timeout for ALS readiness in seconds")] = 30,
    max_attempts: Annotated[int, typer.Option("--max-attempts", help="Maximum retry attempts")] = 3,
    log_path: Annotated[Optional[Path], typer.Option("--log-path", help="Path to log file")] = None,
    stderr_path: Annotated[Optional[Path], typer.Option("--stderr-path", help="Path to stderr log file")] = None,
    no_patterns: Annotated[bool, typer.Option("--no-patterns", help="Disable pattern processing")] = False,
    files: Annotated[Optional[List[str]], typer.Argument(help="Specific Ada files to format")] = None,
) -> None:
    """Format Ada source code using the Ada Language Server (ALS)."""
    
    # Create arguments object
    args = FormatArgs(
        project_path=project_path,
        als_stale_minutes=als_stale_minutes,
        check=check,
        diff=diff,
        exclude_path=exclude_path or [],
        format_timeout=format_timeout,
        include_path=include_path or [],
        init_timeout=init_timeout,
        write=write,
        files=[Path(f) for f in files] if files else [],
        preflight=preflight,
        als_ready_timeout=als_ready_timeout,
        max_attempts=max_attempts,
        log_path=log_path,
        stderr_path=stderr_path,
        no_patterns=no_patterns,
    )
    
    # Create command processor
    processor = FormatCommandProcessor()
    
    # Execute command with functional error handling
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
    result = _execute_command_sync(processor, args)
    exit_code = _handle_command_result(result)
    
    if exit_code != 0:
        raise typer.Exit(exit_code)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()