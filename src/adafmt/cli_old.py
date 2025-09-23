# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Command-line interface for adafmt."""

from __future__ import annotations


import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Any
from enum import Enum

import typer
from typing_extensions import Annotated

from .als_client import ALSClient
from .file_discovery_new import discover_files
from .file_processor import FileProcessor
from .logging_jsonl import JsonlLogger
from .pattern_formatter import PatternFormatter
from .metrics import MetricsCollector
from .pattern_validator import PatternValidator
from .argument_validator import ArgumentValidator
from .pattern_loader import load_patterns
from .als_initializer import initialize_als_client
from .logging_setup import setup_loggers
from .final_reporter import finalize_and_report
from .stderr_handler import setup_stderr_redirect
from .run_setup import execute_pre_hook, run_preflight_checks
from .default_paths import get_default_paths
from .cleanup_handler import (
    cleanup_handler, setup_cleanup_handlers,
    set_cleanup_client, set_cleanup_ui, set_cleanup_logger,
    set_cleanup_pattern_logger, set_cleanup_restore_stderr
)
from .cli_helpers import APP_VERSION, read_license_text, version_callback
from .tui import make_ui

# Setup signal and cleanup handlers
setup_cleanup_handlers()
# Define enums for choice fields
class PreflightMode(str, Enum):
    off = "off"
    none = "none"
    warn = "warn"
    safe = "safe"
    kill = "kill"
    kill_clean = "kill+clean"
    aggressive = "aggressive"
    fail = "fail"

app = typer.Typer(
    name="adafmt",
    help="Ada Language Formatter - Format Ada source code using the Ada Language Server (ALS).",
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

async def _handle_pattern_validation(
    validate_patterns: bool, pattern_formatter: Optional[PatternFormatter],
    pattern_logger: JsonlLogger, client: Optional[ALSClient],
    file_paths: List[Path], format_timeout: int, ui: Optional[Any]
) -> Optional[int]:
    """Handle pattern validation mode if requested."""
    if not validate_patterns:
        return None
        
    if not pattern_formatter or not pattern_formatter.enabled:
        if ui:
            ui.log_line("[error] No patterns loaded for validation")
            ui.close()
        else:
            print("[error] No patterns loaded for validation")
        if client:
            await client.shutdown()
        return 1
    
    # Use PatternValidator for validation
    validator = PatternValidator(client, pattern_formatter, pattern_logger, ui)  # type: ignore[arg-type]
    error_count, validation_errors = await validator.validate_patterns(file_paths, format_timeout)
    # Log validation results
    pattern_logger.write({
        'ev': 'validation_complete',
        'errors': validation_errors[:100],  # Limit to first 100 errors in log
        'total_files': len(file_paths),
        'files_with_errors': error_count})
    if client:
        await client.shutdown()
    return 1 if error_count > 0 else 0

def _build_status_line(
    idx: int, total: int, path: Path, status: str,
    note: Optional[str], no_als: bool,
    pattern_formatter: Optional[PatternFormatter]
) -> str:
    """Build status line for file processing output."""
    prefix = f"[{idx:>4}/{total}]"
    # Left-align status with icon, pad to 11 chars total
    if status == "found":
        status_display = "✓ found     "
    elif status == "formatted":
        status_display = "~ formatted "
    elif status == "amended":
        status_display = "Δ amended   "
    elif status == "unchanged":
        status_display = "= unchanged "
    elif status == "failed":
        status_display = "✗ failed    "
    else:
        # Fallback - left align with padding
        status_display = f"{status:<11}"
    
    line = f"{prefix} [{status_display}] {path}"
    
    # Add ALS info if not in patterns-only mode
    if not no_als and status in ["formatted", "amended"]:
        line += " | ALS: ✓"
    
    # Add pattern info if patterns were applied
    if pattern_formatter and pattern_formatter.enabled:
        pattern_result = pattern_formatter.files_touched.get(str(path))
        if pattern_result:
            patterns_applied = len(pattern_result.applied_names)  # type: ignore[attr-defined]
            replacements = pattern_result.replacements_sum  # type: ignore[attr-defined]
            if patterns_applied > 0:
                line += f" | Patterns: applied={patterns_applied} ({replacements})"
        elif status == "queued":
            line += " | Patterns: queued"
    
    if status == "failed":
        line += "  (details in the stderr log)"
    elif note:
        line += f"  ({note})"
        
    return line

def _print_colored_line(line: str) -> None:
    """Print status line with terminal colors."""
    if sys.stdout.isatty():
        # Check if line contains failed status with the cross mark
        if "[✗ failed" in line and "]" in line:
            # Find the exact failed status bracket
            start_idx = line.find("[✗ failed")
            # Find the closing bracket after the start
            end_idx = line.find("]", start_idx) + 1
            failed_text = line[start_idx:end_idx]
            # Color the entire status bracket in bright red
            colored_line = line[:start_idx] + "\033[91m" + failed_text + "\033[0m" + line[end_idx:]
        else:
            # All other statuses in light gray
            # Using 256-color palette: 253 (very light gray)
            colored_line = "\033[38;5;253m" + line + "\033[0m"
        print(colored_line)
    else:
        print(line)

async def _process_files(
    file_paths: List[Path], file_processor: FileProcessor,
    run_start_time: float, ui: Optional[Any],
    pattern_formatter: Optional[PatternFormatter], no_als: bool,
    log_path: Optional[Path], stderr_path: Optional[Path],
    pattern_log_path: Path, using_default_log: bool,
    using_default_stderr: bool, using_default_patterns: bool,
    client: Optional[ALSClient]
) -> None:
    """Process all files and report progress."""
    total = len(file_paths)
    
    # Initialize worker pool if using parallel processing
    await file_processor.initialize_worker_pool()
    
    for idx, path in enumerate(file_paths, start=1):
        # Show "found" status
        found_line = _build_status_line(
            idx, total, path, "found", None, no_als, pattern_formatter)
        if ui:
            ui.log_line(found_line)
        else:
            _print_colored_line(found_line)
        
        # Process the file
        file_start_time = time.time()
        status, note = await file_processor.process_file(path, idx, total, run_start_time)
        # Build status line
        line = _build_status_line(
            idx, total, path, status, note, no_als, pattern_formatter)
        if ui:
            ui.log_line(line)
            ui.set_progress(idx, len(file_paths))
            # Update footer stats
            current_time = time.time()
            elapsed = current_time - run_start_time
            # Get current stats from processor
            total_changed = file_processor.als_changed + file_processor.pattern_files_changed
            total_failed = file_processor.als_failed
            total_done = idx
            total_unchanged = total_done - total_changed - total_failed
            rate = total_done / elapsed if elapsed > 0 else 0
            
            ui.update_footer_stats(
                total=len(file_paths), changed=total_changed,
                unchanged=total_unchanged, failed=total_failed,
                elapsed=elapsed, rate=rate,
                jsonl_log=f"./{log_path} (default location)" if using_default_log else str(log_path) if log_path else "Not configured",
                als_log=((client.als_log_path if client else None) or "~/.als/ada_ls_log.*.log (default location)") if not no_als else "N/A (ALS disabled)",
                stderr_log=f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path) if stderr_path else "Not configured",
                pattern_log=f"./{pattern_log_path} (default location)" if using_default_patterns else str(pattern_log_path)
            )
        else:
            _print_colored_line(line)


async def _setup_formatter_environment(
    stderr_path: Optional[Path], log_path: Path, preflight_mode: str,
    als_stale_minutes: int, pre_hook: Optional[str], hook_timeout: float,
    project_path: Path, no_als: bool, init_timeout: int,
    als_ready_timeout: int, validate_patterns: bool, write: bool,
    debug_patterns_path: Optional[Path] = None, debug_als_path: Optional[Path] = None
) -> Tuple[Any, Any, Any, Any, JsonlLogger, JsonlLogger, Path, Optional[JsonlLogger], Optional[Path], Optional[JsonlLogger], Optional[Path], MetricsCollector, Optional[ALSClient]]:
    """Set up the formatter environment including UI, loggers, and ALS client."""
    # UI - always use plain TTY UI
    ui = make_ui("plain")
    set_cleanup_ui(ui)
    
    # Setup stderr redirection
    _orig_stderr, _tee_fp, _restore_stderr = setup_stderr_redirect(stderr_path)
    set_cleanup_restore_stderr(_restore_stderr)
    
    # Setup UI mode display
    if ui:
        if validate_patterns:
            mode = "VALIDATE PATTERNS"
        elif write:
            mode = "WRITE MODE"
        else:
            mode = "DRY RUN"
        ui.set_header("Ada Formatter", version=APP_VERSION, mode=mode)

    # Setup loggers
    logger, pattern_logger, pattern_log_path, debug_pattern_logger, debug_pattern_log_path, debug_als_logger, debug_als_log_path = setup_loggers(log_path, debug_patterns_path, debug_als_path)
    set_cleanup_logger(logger)
    set_cleanup_pattern_logger(pattern_logger)
    
    # Initialize metrics collector
    metrics = MetricsCollector(None)  # metrics_path will be set later if provided
    
    # Execute pre-hook
    if not execute_pre_hook(pre_hook, hook_timeout, ui):
        raise SystemExit(1)
    
    # Run preflight checks
    pf_result = run_preflight_checks(project_path, preflight_mode, als_stale_minutes, ui)
    if pf_result != 0:
        raise SystemExit(int(pf_result))

    # Initialize Ada Language Server client
    client = await initialize_als_client(
        project_path, no_als, stderr_path, init_timeout, 
        als_ready_timeout, metrics, ui, debug_als_logger)
    if client:
        set_cleanup_client(client)
        
    return ui, _orig_stderr, _tee_fp, _restore_stderr, logger, pattern_logger, pattern_log_path, debug_pattern_logger, debug_pattern_log_path, debug_als_logger, debug_als_log_path, metrics, client

async def run_formatter(
    project_path: Path, include_paths: List[Path], exclude_paths: List[Path],
    write: bool, diff: bool, check: bool, preflight_mode: str,
    als_stale_minutes: int, pre_hook: Optional[str], post_hook: Optional[str],
    init_timeout: int, als_ready_timeout: int, format_timeout: int,
    max_attempts: int, log_path: Optional[Path], stderr_path: Optional[Path],
    files: List[str], max_consecutive_timeouts: int, patterns_path: Optional[Path],
    no_patterns: bool, patterns_timeout_ms: int, patterns_max_bytes: int,
    hook_timeout: float, validate_patterns: bool = False,
    debug_patterns_path: Optional[Path] = None, debug_als_path: Optional[Path] = None, metrics_path: Optional[Path] = None,
    no_als: bool = False, max_file_size: int = 102400, num_workers: Optional[int] = None,
    using_default_log: bool = False, using_default_stderr: bool = False,
    using_default_patterns: bool = False,
    using_default_debug_patterns: bool = False,
    using_default_debug_als: bool = False) -> int:
    """Run the main formatting logic asynchronously."""
    run_start_time = time.time()
    
    # Set up formatter environment
    try:
        ui, _orig_stderr, _tee_fp, _restore_stderr, logger, pattern_logger, pattern_log_path, debug_pattern_logger, debug_pattern_log_path, debug_als_logger, debug_als_log_path, metrics, client = await _setup_formatter_environment(
            stderr_path, log_path or Path("default.log"), preflight_mode, als_stale_minutes,  # type: ignore[arg-type]
            pre_hook, hook_timeout, project_path, no_als, init_timeout,
            als_ready_timeout, validate_patterns, write, debug_patterns_path, debug_als_path
        )
    except SystemExit as e:
        return e.code or 1  # type: ignore[return-value]
    # Update metrics with the path if provided
    if metrics_path:
        metrics._metrics_path = str(metrics_path)  # type: ignore[attr-defined]
    metrics_start_time = time.time()
    # Discover files to process
    file_paths = discover_files(files, include_paths, exclude_paths, ui)
    # Log discovered files
    if ui:
        ui.log_line(f"[discovery] Found {len(file_paths)} Ada files to format")
    else:
        print(f"[discovery] Found {len(file_paths)} Ada files to format")
    
    # Load pattern formatter
    try:
        pattern_formatter, patterns_path = load_patterns(
            patterns_path, no_patterns, using_default_patterns,
            pattern_logger, ui, client, debug_pattern_logger
        )
    except SystemExit as e:
        if client:
            await client.shutdown()
        return e.code or 1  # type: ignore[return-value]
    
    # Log pattern run_start event
    pattern_logger.write({
        'ev': 'run_start',
        'patterns_path': str(patterns_path) if patterns_path else None,
        'patterns_loaded': pattern_formatter.loaded_count if pattern_formatter else 0,
        'mode': 'VALIDATE' if validate_patterns else ('WRITE' if write else 'DRY'),
        'timeout_ms': patterns_timeout_ms, 'max_bytes': patterns_max_bytes,
        'validate_patterns': validate_patterns})
    
    # Handle pattern validation if requested
    validation_result = await _handle_pattern_validation(
        validate_patterns, pattern_formatter, pattern_logger,
        client, file_paths, format_timeout, ui
    )
    if validation_result is not None:
        return validation_result
    
    # Exit early if no files found
    if not file_paths:
        if ui:
            ui.log_line("[warning] No Ada files found in the specified paths")
            ui.close()
        else:
            print("[warning] No Ada files found in the specified paths")
        if client:
            await client.shutdown()
        return 0
    
    # Log that we're starting formatting
    if ui:
        ui.log_line("[formatter] Starting to format files...")
    else:
        print("[formatter] Starting to format files...")
    
    # Initialize file processor
    file_processor = FileProcessor(
        client=client, pattern_formatter=pattern_formatter,
        logger=logger, pattern_logger=pattern_logger,
        ui=ui, metrics=metrics, no_als=no_als,
        write=write, diff=diff, format_timeout=format_timeout,
        max_consecutive_timeouts=max_consecutive_timeouts,
        max_file_size=max_file_size, num_workers=num_workers)
    
    # Process all files
    await _process_files(
        file_paths, file_processor, run_start_time, ui,
        pattern_formatter, no_als, log_path, stderr_path,
        pattern_log_path, using_default_log, using_default_stderr,
        using_default_patterns, client)
    
    # Shutdown worker pool if used
    await file_processor.shutdown_worker_pool()
    
    # Finalize and generate reports
    exit_code = await finalize_and_report(
        file_processor=file_processor, file_paths=file_paths,
        run_start_time=run_start_time, als_ready_timeout=als_ready_timeout,
        log_path=log_path or Path("default.log"), stderr_path=stderr_path,  # type: ignore[arg-type]
        pattern_log_path=pattern_log_path, using_default_log=using_default_log,
        using_default_stderr=using_default_stderr, using_default_patterns=using_default_patterns,
        pattern_logger=pattern_logger, client=client,
        pattern_formatter=pattern_formatter, ui=ui,
        no_als=no_als, check=check,
        post_hook=post_hook, hook_timeout=hook_timeout,
        debug_pattern_log_path=debug_pattern_log_path,
        debug_als_log_path=debug_als_log_path,
        using_default_debug_patterns=using_default_debug_patterns,
        using_default_debug_als=using_default_debug_als
    )
    
    # Record run summary metrics
    total_duration = time.time() - metrics_start_time
    metrics.record_run_summary(
        total_files=len(file_paths),
        als_succeeded=file_processor.als_changed + (len(file_paths) - file_processor.als_changed - file_processor.als_failed),
        als_failed=file_processor.als_failed,
        patterns_changed=file_processor.pattern_files_changed,
        total_duration=total_duration)
    
    # Close logger to ensure all data is written
    if logger:
        logger.close()
    _restore_stderr()
    return exit_code


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
    log_path: Annotated[Optional[Path], typer.Option("--log-path", help="Override JSONL log location (default: ./adafmt_<timestamp>_log.jsonl)")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", help="Retry attempts for transient errors")] = 2,
    post_hook: Annotated[Optional[str], typer.Option("--post-hook", help="Command to run after formatting; non-zero exit is logged.")] = None,
    pre_hook: Annotated[Optional[str], typer.Option("--pre-hook", help="Command to run before formatting; non-zero exit aborts.")] = None,
    hook_timeout: Annotated[int, typer.Option("--hook-timeout", help="Timeout for hook commands in seconds")] = 5,
    preflight: Annotated[PreflightMode, typer.Option("--preflight", help="Handle existing ALS processes and .als-alire locks")] = PreflightMode.safe,
    stderr_path: Annotated[Optional[Path], typer.Option("--stderr-path", help="Override stderr capture location (default: ./adafmt_<timestamp>_stderr.log)")] = None,
    als_ready_timeout: Annotated[int, typer.Option("--als-ready-timeout", help="Maximum seconds to wait for ALS to become ready")] = 10,
    patterns_path: Annotated[Optional[Path], typer.Option("--patterns-path", help="Path to patterns JSON file (default: ./adafmt_patterns.json)")] = None,
    no_patterns: Annotated[bool, typer.Option("--no-patterns", help="Disable pattern processing")] = False,
    patterns_timeout_ms: Annotated[int, typer.Option("--patterns-timeout-ms", help="Timeout per pattern in milliseconds")] = 100,
    patterns_max_bytes: Annotated[int, typer.Option("--patterns-max-bytes", help="Skip patterns for files larger than this (bytes)")] = 10485760,
    validate_patterns: Annotated[bool, typer.Option("--validate-patterns", help="Validate that applied patterns are acceptable to ALS")] = False,
    debug_patterns: Annotated[bool, typer.Option("--debug-patterns", help="Enable pattern debugging (uses default path if --debug-patterns-path not set)")] = False,
    debug_patterns_path: Annotated[Optional[Path], typer.Option("--debug-patterns-path", help="Write pattern debug output to this path")] = None,
    debug_als: Annotated[bool, typer.Option("--debug-als", help="Enable ALS debugging (uses default path if --debug-als-path not set)")] = False,
    debug_als_path: Annotated[Optional[Path], typer.Option("--debug-als-path", help="Write ALS debug output to this path")] = None,
    metrics_path: Annotated[Optional[Path], typer.Option("--metrics-path", help="Path to cumulative metrics file (default: ~/.adafmt/metrics.jsonl)")] = None,
    no_als: Annotated[bool, typer.Option("--no-als", help="Disable ALS formatting (patterns only)")] = False,
    max_consecutive_timeouts: Annotated[int, typer.Option("--max-consecutive-timeouts", help="Abort after this many timeouts in a row (0 = no limit)")] = 5,
    max_file_size: Annotated[int, typer.Option("--max-file-size", help="Skip files larger than this size in bytes (default: 102400 = 100KB)")] = 102400,
    num_workers: Annotated[Optional[int], typer.Option("--num-workers", help="Number of parallel workers for post-ALS processing (default: 1)")] = None,
    write: Annotated[bool, typer.Option("--write", help="Apply changes to files")] = False,
    files: Annotated[Optional[List[str]], typer.Argument(help="Specific Ada files to format")] = None,
) -> None:
    """Format Ada source code using the Ada Language Server (ALS)."""
    # Validate: Must have include paths or specific files
    if not include_path and not files:
        typer.echo("Error: No files or directories to process. You must provide --include-path or specific files.", err=True)
        typer.echo("Use 'adafmt format --help' for usage information.", err=True)
        raise typer.Exit(2)
    
    # Convert paths to absolute
    project_path = ArgumentValidator.ensure_absolute_path(project_path, "project path")
    include_paths = [ArgumentValidator.ensure_absolute_path(Path(p), f"include path {i+1}") 
                     for i, p in enumerate(include_path)] if include_path else []
    exclude_paths = [ArgumentValidator.ensure_absolute_path(Path(p), f"exclude path {i+1}") 
                     for i, p in enumerate(exclude_path)] if exclude_path else []
    if patterns_path:
        patterns_path = ArgumentValidator.ensure_absolute_path(patterns_path, "patterns path")
    if log_path:
        log_path = ArgumentValidator.ensure_absolute_path(log_path, "log path")
    if stderr_path:
        stderr_path = ArgumentValidator.ensure_absolute_path(stderr_path, "stderr path")
    
    # Process debug flags early for validation
    # Generate timestamp for default paths
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    # Handle debug patterns
    processed_debug_patterns_path = None
    using_default_debug_patterns = False
    if debug_patterns:
        if debug_patterns_path:
            # Custom path provided - expand ~ and ensure parent exists
            processed_debug_patterns_path = debug_patterns_path.expanduser()
            processed_debug_patterns_path.parent.mkdir(parents=True, exist_ok=True)
            using_default_debug_patterns = False
        else:
            # Use default path in current directory
            processed_debug_patterns_path = Path(f"./adafmt_{timestamp}_debug-patterns.jsonl")
            using_default_debug_patterns = True
    elif debug_patterns_path:
        # Error: path provided without enabling debug
        typer.echo("Error: --debug-patterns-path requires --debug-patterns", err=True)
        raise typer.Exit(2)
    
    # Handle debug ALS
    processed_debug_als_path = None
    using_default_debug_als = False
    if debug_als:
        if debug_als_path:
            # Custom path provided - expand ~ and ensure parent exists
            processed_debug_als_path = debug_als_path.expanduser()
            processed_debug_als_path.parent.mkdir(parents=True, exist_ok=True)
            using_default_debug_als = False
        else:
            # Use default path in current directory
            processed_debug_als_path = Path(f"./adafmt_{timestamp}_debug-als.jsonl")
            using_default_debug_als = True
    elif debug_als_path:
        # Error: path provided without enabling debug
        typer.echo("Error: --debug-als-path requires --debug-als", err=True)
        raise typer.Exit(2)
    
    # Validate paths
    path_valid, path_errors = ArgumentValidator.validate_paths(
        project_path=project_path, include_paths=include_paths,
        exclude_paths=exclude_paths, patterns_path=patterns_path,
        files=files, log_path=log_path, stderr_path=stderr_path,
        metrics_path=metrics_path, no_patterns=no_patterns,
        debug_patterns_path=debug_patterns_path, debug_als_path=debug_als_path)
    
    if not path_valid:
        for error in path_errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2)
    
    # Validate options
    options_valid, option_errors = ArgumentValidator.validate_options(
        no_patterns=no_patterns, no_als=no_als,
        validate_patterns=validate_patterns, write=write,
        diff=diff, check=check,
        debug_patterns_path=processed_debug_patterns_path, debug_als_path=processed_debug_als_path)
    
    if not options_valid:
        for error in option_errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2)
    
    # Get default paths if not provided
    log_path, stderr_path, using_default_log, using_default_stderr = get_default_paths(
        log_path, stderr_path)
    
    # Debug paths have already been processed above, using_default_debug_patterns and using_default_debug_als are set
    
    # Run the async formatter
    exit_code = asyncio.run(run_formatter(
        project_path=project_path, include_paths=include_paths,
        exclude_paths=exclude_paths, write=write, diff=diff, check=check,
        preflight_mode=preflight.value, als_stale_minutes=als_stale_minutes,
        pre_hook=pre_hook, post_hook=post_hook, init_timeout=init_timeout,
        als_ready_timeout=als_ready_timeout, format_timeout=format_timeout,
        max_attempts=max_attempts, log_path=log_path, stderr_path=stderr_path,
        files=files or [], max_consecutive_timeouts=max_consecutive_timeouts,
        patterns_path=patterns_path, no_patterns=no_patterns,
        patterns_timeout_ms=patterns_timeout_ms, patterns_max_bytes=patterns_max_bytes,
        hook_timeout=hook_timeout, validate_patterns=validate_patterns,
        debug_patterns_path=processed_debug_patterns_path, debug_als_path=processed_debug_als_path, metrics_path=metrics_path, no_als=no_als,
        max_file_size=max_file_size, num_workers=num_workers,
        using_default_log=using_default_log, using_default_stderr=using_default_stderr,
        using_default_patterns=True, using_default_debug_patterns=using_default_debug_patterns,
        using_default_debug_als=using_default_debug_als))
    
    raise typer.Exit(exit_code)


def main() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except Exception as e:
        print(f"[FATAL ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        # Ensure cleanup runs even on exceptions
        cleanup_handler()
        sys.exit(1)

if __name__ == "__main__":
    main()