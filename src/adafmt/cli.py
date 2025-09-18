# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Command-line interface for adafmt using Typer.

This module provides the main entry point for the adafmt tool, which formats
Ada source code using the Ada Language Server (ALS). It supports various UI
modes, Alire integration, and comprehensive error handling with retry logic.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import io
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from enum import Enum

# Python 3.9+: importlib.resources.files
try:
    from importlib.resources import files as pkg_files
except ImportError:
    pkg_files = None

import typer
from typing_extensions import Annotated
from tabulate import tabulate

from .als_client import ALSClient, ALSProtocolError
from .file_discovery_new import discover_files
from .file_processor import FileProcessor
from .logging_jsonl import JsonlLogger
from .pattern_formatter import PatternFormatter, PatternLogger
from .metrics import MetricsCollector
from .metrics_reporter import MetricsReporter
from .pattern_validator import PatternValidator
from .argument_validator import ArgumentValidator
from .pattern_loader import load_patterns
from .als_initializer import initialize_als_client
from .logging_setup import setup_loggers
from .tui import make_ui
from .utils import preflight, run_hook

# Version is dynamically read from package metadata
try:
    from importlib.metadata import version
    APP_VERSION = version("adafmt")
except Exception:
    # Fallback for development/editable installs
    APP_VERSION = "0.0.0"

# Global cleanup state
_cleanup_client: Optional[ALSClient] = None
_cleanup_ui = None
_cleanup_logger: Optional[JsonlLogger] = None
_cleanup_pattern_logger: Optional[JsonlLogger] = None
_cleanup_restore_stderr = None


class _Tee(io.TextIOBase):
    """Redirect output to multiple streams."""
    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]
    
    def write(self, s):
        wrote = 0
        for st in self._streams:
            try:
                wrote = st.write(s)
                st.flush()
            except Exception:
                pass
        return wrote
    
    def flush(self):
        for st in self._streams:
            with contextlib.suppress(Exception):
                st.flush()

def _cleanup_handler(signum=None, frame=None):
    """Clean up resources on exit or signal."""
    try:
        if _cleanup_client:
            # Force sync shutdown of ALS client
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_cleanup_client.shutdown())
                else:
                    asyncio.run(_cleanup_client.shutdown())
            except Exception:
                # Force kill the process if graceful shutdown fails
                if hasattr(_cleanup_client, '_proc') and _cleanup_client._proc:
                    try:
                        _cleanup_client._proc.terminate()
                    except Exception:
                        pass
        
        if _cleanup_ui:
            with contextlib.suppress(Exception):
                _cleanup_ui.close()
        
        if _cleanup_logger:
            with contextlib.suppress(Exception):
                _cleanup_logger.close()
        
        if _cleanup_pattern_logger:
            with contextlib.suppress(Exception):
                _cleanup_pattern_logger.close()
                
        if _cleanup_restore_stderr:
            with contextlib.suppress(Exception):
                _cleanup_restore_stderr()
                
    except Exception:
        pass  # Don't let cleanup errors crash the cleanup
        
    if signum:
        sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, _cleanup_handler)
signal.signal(signal.SIGTERM, _cleanup_handler)

# Also register atexit for normal exit
atexit.register(_cleanup_handler)

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
def main_callback():
    """Print header for all commands."""
    print(f"Ada Formatter  {APP_VERSION}")
    print("=" * 80)


def _read_license_text() -> str:
    """Read the LICENSE file from package data or filesystem."""
    # 1) Prefer a bundled copy inside the package: adafmt/LICENSE
    if pkg_files:
        try:
            return pkg_files("adafmt").joinpath("LICENSE").read_text(encoding="utf-8")
        except Exception:
            pass

    # 2) Fallbacks for dev runs from a source checkout
    here = Path(__file__).resolve()
    for candidate in (
        here.parent / "LICENSE",
        here.parent.parent / "LICENSE",
        here.parent.parent.parent / "LICENSE",  # src/adafmt -> src -> repo root
        Path.cwd() / "LICENSE",
    ):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError("LICENSE not found. Bundle it as package data or run from repo root.")


def _version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"adafmt version {APP_VERSION}")
        raise typer.Exit()



def _abs(p: str) -> str:
    """Convert a path string to an absolute path."""
    return str(Path(p).expanduser().resolve())


def _write_stderr_error(path: Path, error_type: str, error_msg: str, details: Optional[dict] = None) -> None:
    """Write detailed error information to stderr with timestamp.
    
    Args:
        path: The file that failed
        error_type: Type of error (e.g., "ALS_SYNTAX_ERROR", "TIMEOUT", etc.)
        error_msg: The error message
        details: Optional additional details as a dictionary
    """
    # Only write to stderr if it has been properly redirected to a file
    # This prevents error details from appearing in the UI output
    if hasattr(sys.stderr, '_streams') and sys.stderr._streams:
        timestamp = datetime.now().isoformat()
        stderr_msg = f"{timestamp} | ERROR | {error_type} | {path}\n"
        stderr_msg += f"{timestamp} | ERROR | Message: {error_msg}\n"
        
        if details:
            for key, value in details.items():
                stderr_msg += f"{timestamp} | ERROR | {key}: {value}\n"
        
        stderr_msg += f"{timestamp} | ERROR | {'=' * 60}\n"
        sys.stderr.write(stderr_msg)
        sys.stderr.flush()



async def run_formatter(
    project_path: Path,
    include_paths: List[Path],
    exclude_paths: List[Path],
    write: bool,
    diff: bool,
    check: bool,
    preflight_mode: str,
    als_stale_minutes: int,
    pre_hook: Optional[str],
    post_hook: Optional[str],
    init_timeout: int,
    warmup_seconds: int,
    format_timeout: int,
    max_attempts: int,
    log_path: Optional[Path],
    stderr_path: Optional[Path],
    files: List[str],
    max_consecutive_timeouts: int,
    patterns_path: Optional[Path],
    no_patterns: bool,
    patterns_timeout_ms: int,
    patterns_max_bytes: int,
    hook_timeout: float,
    validate_patterns: bool = False,
    metrics_path: Optional[Path] = None,
    no_als: bool = False,
    using_default_log: bool = False,
    using_default_stderr: bool = False,
    using_default_patterns: bool = False) -> int:
    """Run the main formatting logic asynchronously."""
    # Import path validator (imported here to avoid circular imports)
    from .path_validator import validate_path
    
    run_start_time = time.time()
    
    proj = project_path
    includes = include_paths  # No fallback - already validated in format_command
    excludes = exclude_paths
    
    # UI - always use plain TTY UI
    ui = make_ui("plain")
    global _cleanup_ui
    _cleanup_ui = ui
    # --- Redirect stderr to the configured stderr file (suppress terminal output) ---
    _orig_stderr = sys.stderr
    _tee_fp = None
    def _restore_stderr():
        nonlocal _tee_fp, _orig_stderr
        try:
            sys.stderr = _orig_stderr
        except Exception:
            pass
        if _tee_fp:
            with contextlib.suppress(Exception):
                _tee_fp.flush()
                _tee_fp.close()
            _tee_fp = None

    try:
        if stderr_path:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            _tee_fp = open(stderr_path, "w", encoding="utf-8")
            _tee_fp.write(f"{datetime.now().isoformat()} | INFO  | ADAFMT STDERR START\n")
            _tee_fp.flush()
            sys.stderr = _Tee(_tee_fp)  # Only write to file, not to terminal
    except Exception:
        sys.stderr = _orig_stderr

    global _cleanup_restore_stderr
    _cleanup_restore_stderr = _restore_stderr

    
    # Discover files to process
    file_paths = discover_files(files, includes, excludes, ui)
    if ui:
        if validate_patterns:
            mode = "VALIDATE PATTERNS"
        elif write:
            mode = "WRITE MODE"
        else:
            mode = "DRY RUN"
        ui.set_header("Ada Formatter", version=APP_VERSION, mode=mode)

    # Setup loggers
    logger, pattern_logger, pattern_log_path = setup_loggers(log_path)
    global _cleanup_logger, _cleanup_pattern_logger
    _cleanup_logger = logger
    _cleanup_pattern_logger = pattern_logger
    
    # Initialize metrics collector
    metrics = MetricsCollector(str(metrics_path) if metrics_path else None)
    metrics_start_time = time.time()

    # Hooks
    if pre_hook:
        ok = run_hook(pre_hook, "pre", logger=(ui.log_line if ui else print), timeout=hook_timeout, dry_run=False)
        if not ok:
            if ui:
                ui.log_line("[error] pre-hook failed; aborting.")
            else:
                print("[error] pre-hook failed; aborting.")
            return 1

    # Preflight
    project_root = proj.parent
    if preflight_mode not in ("off", "none"):
        pf_result = preflight(
            mode=preflight_mode.replace("+", ""),  # Handle kill+clean
            als_stale_minutes=als_stale_minutes,
            lock_ttl_minutes=10,  # default
            search_paths=[project_root],
            logger=(ui.log_line if ui else print),
            dry_run=False,
        )
        if pf_result != 0:
            return int(pf_result)


    # Initialize Ada Language Server client
    client = await initialize_als_client(
        proj, no_als, stderr_path, init_timeout, 
        warmup_seconds, metrics, ui
    )
    if client:
        global _cleanup_client
        _cleanup_client = client
    
    # Log discovered files
    if ui:
        ui.log_line(f"[discovery] Found {len(file_paths)} Ada files to format")
    else:
        print(f"[discovery] Found {len(file_paths)} Ada files to format")
    
    # Load pattern formatter
    try:
        pattern_formatter, patterns_path = load_patterns(
            patterns_path, no_patterns, using_default_patterns,
            pattern_logger, ui, client
        )
    except SystemExit as e:
        if client:
            await client.shutdown()
        return e.code
    
    # Log pattern run_start event
    pattern_logger.write({
        'ev': 'run_start',
        'patterns_path': str(patterns_path) if patterns_path else None,
        'patterns_loaded': pattern_formatter.loaded_count if pattern_formatter else 0,
        'mode': 'VALIDATE' if validate_patterns else ('WRITE' if write else 'DRY'),
        'timeout_ms': patterns_timeout_ms,
        'max_bytes': patterns_max_bytes,
        'validate_patterns': validate_patterns
    })
    
    # Validation mode - verify patterns don't break ALS formatting
    if validate_patterns:
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
        validator = PatternValidator(client, pattern_formatter, pattern_logger, ui)
        error_count, validation_errors = await validator.validate_patterns(file_paths, format_timeout)
        
        # Log validation results
        pattern_logger.write({
            'ev': 'validation_complete',
            'errors': validation_errors[:100],  # Limit to first 100 errors in log
            'total_files': len(file_paths),
            'files_with_errors': error_count
        })
        
        if client:
            await client.shutdown()
        
        return 1 if error_count > 0 else 0
    
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
        client=client,
        pattern_formatter=pattern_formatter,
        logger=logger,
        pattern_logger=pattern_logger,
        ui=ui,
        metrics=metrics,
        no_als=no_als,
        write=write,
        diff=diff,
        format_timeout=format_timeout,
        max_consecutive_timeouts=max_consecutive_timeouts
    )
    
    # Process each file
    total = len(file_paths)
    
    for idx, path in enumerate(file_paths, start=1):
        # Log first file to debug hanging
        if idx == 1:
            if ui:
                ui.log_line(f"[formatter] Processing first file: {path}")
            else:
                print(f"[formatter] Processing first file: {path}")
        
        # Process the file
        file_start_time = time.time()
        status, note = await file_processor.process_file(path, idx, total, run_start_time)
        
        # Update UI/console with progress
        prefix = f"[{idx:>4}/{total}]"
        
        # Build status line
        line = f"{prefix} [{status:^7}] {path}"
        
        # Add ALS info if not in patterns-only mode
        if not no_als and status == "changed":
            line += " | ALS: ✓"
        
        # Add pattern info if patterns were applied
        if pattern_formatter and pattern_formatter.enabled:
            pattern_result = pattern_formatter.files_touched.get(str(path))
            if pattern_result:
                patterns_applied = len(pattern_result.applied_names)
                replacements = pattern_result.replacements_sum
                if patterns_applied > 0:
                    line += f" | Patterns: applied={patterns_applied} ({replacements})"
        
        if status == "failed":
            line += "  (details in the stderr log)"
        elif note:
            line += f"  ({note})"
            
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
                total=len(file_paths),
                changed=total_changed,
                unchanged=total_unchanged,
                failed=total_failed,
                elapsed=elapsed,
                rate=rate,
                jsonl_log=f"./{log_path} (default location)" if using_default_log else str(log_path) if log_path else "Not configured",
                als_log=((client.als_log_path if client else None) or "~/.als/ada_ls_log.*.log (default location)") if not no_als else "N/A (ALS disabled)",
                stderr_log=f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path) if stderr_path else "Not configured",
                pattern_log=f"./{pattern_log_path} (default location)" if using_default_patterns else str(pattern_log_path)
            )
        else:
            # Apply colors in terminal
            if sys.stdout.isatty():
                colored_line = line
                # Color [failed ] in bright red
                if "[failed ]" in line:
                    start_idx = line.find("[failed ]")
                    end_idx = start_idx + len("[failed ]")
                    colored_line = line[:start_idx] + "\033[91m\033[1m[failed ]\033[0m" + line[end_idx:]
                # Color [changed] in bright yellow
                elif "[changed]" in line:
                    start_idx = line.find("[changed]")
                    end_idx = start_idx + len("[changed]")
                    colored_line = line[:start_idx] + "\033[93m\033[1m[changed]\033[0m" + line[end_idx:]
                print(colored_line)
            else:
                print(line)
    
    # Get final statistics from processor
    als_changed = file_processor.als_changed
    als_failed = file_processor.als_failed
    pattern_files_changed = file_processor.pattern_files_changed
    total_errors = file_processor.total_errors
    false_positives = 0  # TODO: Track false positives in FileProcessor
    # Calculate statistics
    end_time = time.time()
    elapsed_seconds = max(0.1, end_time - run_start_time)
    
    # Calculate final metrics
    total_processed = len(file_paths)
    total_changed = als_changed + pattern_files_changed
    total_failed = als_failed
    als_unchanged = total_processed - als_changed - als_failed if client else 0
    total_unchanged = len(file_paths) - total_changed - total_failed
    
    rate = len(file_paths) / elapsed_seconds if len(file_paths) > 0 else 0

    # Update final UI state before shutdown
    if ui:
        ui.set_progress(len(file_paths), len(file_paths))
        # Final footer update
        ui.update_footer_stats(
            total=len(file_paths),
            changed=total_changed,
            unchanged=total_unchanged,
            failed=total_failed,
            elapsed=elapsed_seconds,
            rate=rate,
            jsonl_log=f"./{log_path} (default location)" if using_default_log else str(log_path) if log_path else "Not configured",
            als_log=((client.als_log_path if client else None) or "~/.als/ada_ls_log.*.log (default location)") if not no_als else "N/A (ALS disabled)",
            stderr_log=f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path) if stderr_path else "Not configured",
            pattern_log=f"./{pattern_log_path} (default location)" if using_default_patterns else str(pattern_log_path)
        )
        
        # Only show warnings if there were false positives
        if false_positives > 0:
            ui.log_line("")
            ui.log_line(f"Warning: GNATFORMAT reported {false_positives} false positive(s) (files compile OK)")
        
        # Only wait for key in curses-based UIs (not PlainUI)
        ui_type_name = type(ui).__name__
        if ui_type_name not in ('PlainUI', 'NoneType'):
            # Only wait for key in curses-based UIs
            ui.log_line("")
            ui.log_line("Press any key to exit...")
            
            # Wait for keypress while UI is still active
            ui.wait_for_key()
        
        ui.close()
    
    # Get timestamps from start and end
    from datetime import datetime, timezone
    adafmt_start_time = datetime.fromtimestamp(run_start_time, tz=timezone.utc)
    adafmt_end_time = datetime.fromtimestamp(end_time, tz=timezone.utc)
    
    # Estimate ALS and pattern processing times
    # ALS processing includes warmup + file processing
    als_start_time = adafmt_start_time
    # Pattern processing happens during file processing, estimate based on timing
    pattern_start_time = datetime.fromtimestamp(run_start_time + (warmup_seconds if client else 0), tz=timezone.utc)
    pattern_end_time = adafmt_end_time
    
    # Calculate pattern processing time
    pattern_elapsed = 0
    if pattern_formatter and pattern_formatter.enabled:
        # Rough estimate: patterns take about 10% of total processing time
        pattern_elapsed = elapsed_seconds * 0.1
    
    als_elapsed = elapsed_seconds - pattern_elapsed
    
    # Create metrics reporter and print summary
    reporter = MetricsReporter()
    reporter.print_summary(
        # File counts
        file_paths=file_paths,
        als_changed=als_changed,
        als_failed=als_failed,
        als_unchanged=als_unchanged,
        # Timing info
        run_start_time=run_start_time,
        run_end_time=end_time,
        pattern_elapsed=pattern_elapsed,
        # Timestamps
        adafmt_start_time=adafmt_start_time,
        adafmt_end_time=adafmt_end_time,
        als_start_time=als_start_time,
        pattern_start_time=pattern_start_time,
        pattern_end_time=pattern_end_time,
        # Components
        client=client,
        pattern_formatter=pattern_formatter,
        # Log paths
        log_path=log_path,
        stderr_path=stderr_path,
        pattern_log_path=pattern_log_path,
        using_default_log=using_default_log,
        using_default_stderr=using_default_stderr,
        using_default_patterns=using_default_patterns,
        no_als=no_als,
        ui=ui
    )

    # Log pattern run_end event
    pattern_logger.write({
        'ev': 'run_end',
        'files_total': len(file_paths),
        'files_als_ok': len(file_paths) - als_failed,
        'patterns_loaded': pattern_formatter.loaded_count if pattern_formatter else 0,
        'patterns_summary': pattern_formatter.get_summary() if pattern_formatter else {}
    })
    
    # Record run summary metrics
    total_duration = time.time() - metrics_start_time
    metrics.record_run_summary(
        total_files=len(file_paths),
        als_succeeded=len(file_paths) - als_failed,
        als_failed=als_failed,
        patterns_changed=pattern_files_changed,
        total_duration=total_duration
    )
    
    # Shutdown ALS after UI updates
    with contextlib.suppress(Exception):
        if client:
                await client.shutdown()

    # Close logger to ensure all data is written
    if logger:
        logger.close()

    # Post-hook (do not fail the overall run if it fails)
    if post_hook:
        run_hook(post_hook, "post", logger=(ui.log_line if ui else print) if ui else print, timeout=hook_timeout, dry_run=False)

    if check and total_changed:
        _restore_stderr()
        return 1
    _restore_stderr()
    return 0


@app.command("license", help="Show the project's license text (BSD-3-Clause).")
def license_command():
    """Show the BSD-3-Clause license text."""
    try:
        license_text = _read_license_text()
        typer.echo(license_text, color=False)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="format")
def format_command(
    project_path: Annotated[Path, typer.Option("--project-path", help="Path to your GNAT project file (.gpr)")],
    version: Annotated[Optional[bool], typer.Option("--version", "-v", callback=_version_callback, help="Show version and exit")] = None,
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
    # UI option disabled - always uses plain UI for better scrollback
    # The graphical UI has been removed in favor of plain text output
    # ui: Annotated[UIMode, typer.Option("--ui", help="UI mode")] = UIMode.auto,
    warmup_seconds: Annotated[int, typer.Option("--warmup-seconds", help="Time to let ALS warm up in seconds")] = 10,
    patterns_path: Annotated[Optional[Path], typer.Option("--patterns-path", help="Path to patterns JSON file (default: ./adafmt_patterns.json)")] = None,
    no_patterns: Annotated[bool, typer.Option("--no-patterns", help="Disable pattern processing")] = False,
    patterns_timeout_ms: Annotated[int, typer.Option("--patterns-timeout-ms", help="Timeout per pattern in milliseconds")] = 100,
    patterns_max_bytes: Annotated[int, typer.Option("--patterns-max-bytes", help="Skip patterns for files larger than this (bytes)")] = 10485760,
    validate_patterns: Annotated[bool, typer.Option("--validate-patterns", help="Validate that applied patterns are acceptable to ALS")] = False,
    metrics_path: Annotated[Optional[Path], typer.Option("--metrics-path", help="Path to cumulative metrics file (default: ~/.adafmt/metrics.jsonl)")] = None,
    no_als: Annotated[bool, typer.Option("--no-als", help="Disable ALS formatting (patterns only)")] = False,
    max_consecutive_timeouts: Annotated[int, typer.Option("--max-consecutive-timeouts", help="Abort after this many timeouts in a row (0 = no limit)")] = 5,
    write: Annotated[bool, typer.Option("--write", help="Apply changes to files")] = False,
    files: Annotated[Optional[List[str]], typer.Argument(help="Specific Ada files to format")] = None,
) -> None:
    """Format Ada source code using the Ada Language Server (ALS).
    
    Examples:
        adafmt --project-path /path/to/project.gpr --include-path /path/to/src
        adafmt --project-path project.gpr --write --check
        adafmt --project-path project.gpr --ui plain --log-path debug.jsonl
    """
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
    
    # Validate paths
    path_valid, path_errors = ArgumentValidator.validate_paths(
        project_path=project_path,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        patterns_path=patterns_path,
        files=files,
        log_path=log_path,
        stderr_path=stderr_path,
        metrics_path=metrics_path,
        no_patterns=no_patterns
    )
    
    if not path_valid:
        for error in path_errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2)
    
    # Validate options
    options_valid, option_errors = ArgumentValidator.validate_options(
        no_patterns=no_patterns,
        no_als=no_als,
        validate_patterns=validate_patterns,
        write=write,
        diff=diff,
        check=check
    )
    
    if not options_valid:
        for error in option_errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2)
    
    # Generate default filenames with timestamp if not provided (ISO 8601 format)
    from datetime import timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    # Track if using default paths
    using_default_log = False
    using_default_stderr = False
    
    # Set default log path if not provided (check env var first)
    if log_path is None:
        env_log_path = os.getenv("ADAFMT_LOG_FILE_PATH")
        if env_log_path:
            log_path = Path(env_log_path)
        else:
            log_path = Path(f"./adafmt_{timestamp}_log.jsonl")
            using_default_log = True
    
    # Set default stderr path if not provided  
    if stderr_path is None:
        stderr_path = Path(f"./adafmt_{timestamp}_stderr.log")
        using_default_stderr = True
    
    # Run the async formatter
    exit_code = asyncio.run(run_formatter(
        project_path=project_path,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        write=write,
        diff=diff,
        check=check,
        preflight_mode=preflight.value,
        als_stale_minutes=als_stale_minutes,
        pre_hook=pre_hook,
        post_hook=post_hook,
        init_timeout=init_timeout,
        warmup_seconds=warmup_seconds,
        format_timeout=format_timeout,
        max_attempts=max_attempts,
        log_path=log_path,
        stderr_path=stderr_path,
        files=files or [],
        max_consecutive_timeouts=max_consecutive_timeouts,
        patterns_path=patterns_path,
        no_patterns=no_patterns,
        patterns_timeout_ms=patterns_timeout_ms,
        patterns_max_bytes=patterns_max_bytes,
        hook_timeout=hook_timeout,
        validate_patterns=validate_patterns,
        metrics_path=metrics_path,
        no_als=no_als,
        using_default_log=using_default_log,
        using_default_stderr=using_default_stderr,
        using_default_patterns=True))
    
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
        _cleanup_handler()
        sys.exit(1)

if __name__ == "__main__":
    main()