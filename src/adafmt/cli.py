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
from .file_discovery import collect_files
from .logging_jsonl import JsonlLogger
from .pattern_formatter import PatternFormatter, PatternLogger
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
class UIMode(str, Enum):
    off = "off"
    auto = "auto"
    pretty = "pretty"
    basic = "basic"
    plain = "plain"


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


def _is_ada_file(path: Path) -> bool:
    """Check if a path points to an Ada source file."""
    return path.suffix.lower() in (".ads", ".adb", ".ada")


async def run_formatter(
    project_path: Path,
    include_paths: List[Path],
    exclude_paths: List[Path],
    write: bool,
    diff: bool,
    check: bool,
    ui_mode: str,
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
    validate_patterns: bool = False,
    no_als: bool = False,
    using_default_log: bool = False,
    using_default_stderr: bool = False,
    using_default_patterns: bool = False) -> int:
    """Run the main formatting logic asynchronously."""
    run_start_time = time.time()
    
    proj = project_path
    includes = include_paths  # No fallback - already validated in format_command
    excludes = exclude_paths
    
    # UI
    ui = make_ui(ui_mode) if ui_mode != "off" else None
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

    
    # resolve files
    if files:
        # User specified specific files
        file_paths: List[Path] = [Path(p) for p in files if _is_ada_file(Path(p))]
    else:
        # Discover files in include paths
        if ui:
            ui.log_line("[discovery] Starting file discovery...")
        else:
            print("[discovery] Starting file discovery...")
        
        file_paths: List[Path] = [Path(p) for p in collect_files(includes, excludes)]
        file_paths = [p for p in file_paths if _is_ada_file(p)]
        
        if ui:
            ui.log_line("[discovery] File discovery completed")
        else:
            print("[discovery] File discovery completed")
    if ui:
        if validate_patterns:
            mode = "VALIDATE PATTERNS"
        elif write:
            mode = "WRITE MODE"
        else:
            mode = "DRY RUN"
        ui.set_header("Ada Formatter", version=APP_VERSION, mode=mode)

    # logger - always create a logger (log_path is always set now)
    logger = JsonlLogger(log_path)
    logger.start_fresh()  # Create empty file, ensuring it exists
    global _cleanup_logger
    _cleanup_logger = logger
    
    # pattern logger - create pattern log file
    # Try to extract timestamp from log filename, or use current time
    try:
        timestamp = log_path.name.split('_')[1].split('.')[0]  # Extract timestamp from main log filename
    except (IndexError, AttributeError):
        from datetime import datetime as dt
        timestamp = dt.now().strftime('%Y%m%dT%H%M%SZ')
    pattern_log_path = log_path.parent / f"adafmt_{timestamp}_patterns.log"
    pattern_logger = JsonlLogger(pattern_log_path)
    pattern_logger.start_fresh()
    global _cleanup_pattern_logger
    _cleanup_pattern_logger = pattern_logger

    # Hooks
    if pre_hook:
        ok = run_hook(pre_hook, "pre", logger=(ui.log_line if ui else print), dry_run=False)
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


    # Initialize Ada Language Server client with configuration (unless --no-als)
    client = None
    if not no_als:
        client = ALSClient(
            project_file=proj, 
            stderr_file_path=stderr_path,
            init_timeout=init_timeout,  # Fix: Pass init_timeout
            logger=ui.log_line if ui else print
        )
        await client.start()
        global _cleanup_client
        _cleanup_client = client
        
        # Add warmup delay after start
        if warmup_seconds > 0:
            if ui:
                ui.log_line(f"[als] Warming up for {warmup_seconds} seconds...")
            else:
                print(f"[als] Warming up for {warmup_seconds} seconds...")
            await asyncio.sleep(warmup_seconds)
    else:
        if ui:
            ui.log_line("[als] ALS formatting disabled (--no-als)")
        else:
            print("[als] ALS formatting disabled (--no-als)")
    
    # Echo launch context for debugging
    if client:
        launch_msg = f"[als] cwd={client._launch_cwd} cmd={client._launch_cmd}"
        if ui:
            ui.log_line(launch_msg)
        else:
            print(launch_msg)
    
    # Display log paths early so users know where to find them
    if client:
        if ui:
            ui.log_line(f"[als] ALS log: {client.als_log_path or '~/.als/ada_ls_log.*.log (default location)'}")
            ui.log_line(f"[als] Stderr log: {client._stderr_log_path}")
        else:
            print(f"[als] ALS log: {client.als_log_path or '~/.als/ada_ls_log.*.log (default location)'}")
            print(f"[als] Stderr log: {client._stderr_log_path}")
    
    # Log discovered files
    if ui:
        ui.log_line(f"[discovery] Found {len(file_paths)} Ada files to format")
    else:
        print(f"[discovery] Found {len(file_paths)} Ada files to format")
    
    # Load pattern formatter
    pattern_formatter = None
    if not no_patterns:
        if patterns_path is None:
            patterns_path = Path("./adafmt_patterns.json")
            using_default_patterns = True
        
        # Check if patterns file exists when explicitly provided
        if not using_default_patterns and not patterns_path.exists():
            if ui:
                ui.log_line(f"[error] Patterns file not found: {patterns_path}")
                ui.close()
            else:
                print(f"[error] Patterns file not found: {patterns_path}")
            if client:
                    await client.shutdown()
            return 2
        
        # For default path, it's OK if it doesn't exist
        if patterns_path.exists():
            if ui:
                ui.log_line(f"[patterns] Loading patterns from: {patterns_path}")
            
            try:
                pattern_formatter = PatternFormatter.load_from_json(
                    patterns_path,
                    logger=PatternLogger(pattern_logger),
                    ui=ui
                )
                
                # Check if patterns file is empty (no patterns loaded)
                if pattern_formatter.loaded_count == 0:
                    if ui:
                        ui.log_line("[patterns] Warning: Pattern file is empty, only ALS formatting will be performed")
                    else:
                        print("[patterns] Warning: Pattern file is empty, only ALS formatting will be performed")
                    pattern_formatter = None  # Same as --no-patterns
                else:
                    if ui:
                        ui.log_line(f"[patterns] Loaded {pattern_formatter.loaded_count} patterns")
                        
            except Exception:
                raise
        else:
            # Default patterns file doesn't exist - that's OK, continue without patterns
            if ui:
                ui.log_line("[patterns] No patterns file found, only ALS formatting will be performed")
            else:
                print("[patterns] No patterns file found, only ALS formatting will be performed")
    else:
        if ui:
            ui.log_line("[patterns] Pattern processing disabled (--no-patterns)")
        else:
            print("[patterns] Pattern processing disabled (--no-patterns)")
    
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
        
        if ui:
            ui.log_line("[validate] Starting pattern validation...")
        else:
            print("[validate] Starting pattern validation...")
        
        validation_errors = []
        
        for idx, path in enumerate(file_paths, 1):
            try:
                # Read original content
                original_content = path.read_text(encoding="utf-8", errors="ignore")
                
                # Apply patterns
                pattern_content, pattern_result = pattern_formatter.apply(
                    path,
                    original_content,
                    timeout_ms=patterns_timeout_ms,
                    logger=PatternLogger(pattern_logger),
                    ui=ui
                )
                
                # Skip if no patterns were applied
                if not pattern_result or len(pattern_result.applied_names) == 0:
                    continue
                
                # Run pattern result through ALS
                await client._notify("textDocument/didOpen", {
                    "textDocument": {
                        "uri": path.as_uri(),
                        "languageId": "ada",
                        "version": 1,
                        "text": pattern_content,
                    }
                })
                
                try:
                    edits = await client.request_with_timeout({
                        "method": "textDocument/formatting",
                        "params": {
                            "textDocument": {"uri": path.as_uri()},
                            "options": {"tabSize": 3, "insertSpaces": True},
                        }
                    }, timeout=format_timeout)
                    
                    if edits:
                        # ALS wants to make changes to pattern output
                        validation_errors.append({
                            'path': str(path),
                            'patterns_applied': pattern_result.applied_names,
                            'als_edits': len(edits),
                            'message': f"Patterns break ALS formatting (ALS wants {len(edits)} edits)"
                        })
                        
                        if ui:
                            ui.log_line(f"[{idx:>4}/{len(file_paths)}] [ERROR] {path} - patterns conflict with ALS")
                        else:
                            print(f"[{idx:>4}/{len(file_paths)}] [ERROR] {path} - patterns conflict with ALS")
                    else:
                        if ui:
                            ui.log_line(f"[{idx:>4}/{len(file_paths)}] [  OK  ] {path}")
                        else:
                            print(f"[{idx:>4}/{len(file_paths)}] [  OK  ] {path}")
                    
                finally:
                    await client._notify("textDocument/didClose", {
                        "textDocument": {"uri": path.as_uri()}
                    })
                    
            except Exception as e:
                validation_errors.append({
                    'path': str(path),
                    'error': str(e),
                    'message': f"Validation error: {e}"
                })
                if ui:
                    ui.log_line(f"[{idx:>4}/{len(file_paths)}] [ERROR] {path} - {e}")
                else:
                    print(f"[{idx:>4}/{len(file_paths)}] [ERROR] {path} - {e}")
        
        # Report validation results
        if validation_errors:
            if ui:
                ui.log_line(f"\n[validate] Found {len(validation_errors)} pattern conflicts:")
                for err in validation_errors:
                    ui.log_line(f"  - {err['path']}: {err['message']}")
            else:
                print(f"\n[validate] Found {len(validation_errors)} pattern conflicts:")
                for err in validation_errors:
                    print(f"  - {err['path']}: {err['message']}")
            
            # Log validation results
            pattern_logger.write({
                'ev': 'validation_complete',
                'errors': validation_errors,
                'total_files': len(file_paths),
                'files_with_errors': len(validation_errors)
            })
            
            if client:
                await client.shutdown()
            return 1
        else:
            if ui:
                ui.log_line(f"\n[validate] All patterns validated successfully ({len(file_paths)} files)")
            else:
                print(f"\n[validate] All patterns validated successfully ({len(file_paths)} files)")
            
            pattern_logger.write({
                'ev': 'validation_complete',
                'errors': [],
                'total_files': len(file_paths),
                'files_with_errors': 0
            })
            
            if client:
                await client.shutdown()
            return 0
    
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
    
    changed = 0
    failed = 0
    done = 0
    false_positives = 0
    
    async def format_once(path: Path) -> Optional[List[dict]]:
        """Format a single Ada file using ALS."""
        # If ALS is disabled, return None (no edits)
        if not client:
            return None
            
        # Open
        await client._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": path.as_uri(),
                "languageId": "ada",
                "version": 1,
                "text": path.read_text(encoding="utf-8", errors="ignore"),
            }
        })
        try:
            res = await client.request_with_timeout({
                "method": "textDocument/formatting",
                "params": {
                    "textDocument": {"uri": path.as_uri()},
                    "options": {"tabSize": 3, "insertSpaces": True},
                },
            }, timeout=format_timeout)
        finally:
            with contextlib.suppress(Exception):
                await client._notify("textDocument/didClose", {"textDocument": {"uri": path.as_uri()}})
        
        # Validate response
        if res is not None and not isinstance(res, list):
            raise TypeError(f"ALS returned unexpected type: {type(res).__name__} instead of list")
        return res

    total = len(file_paths)
    consecutive_timeouts = 0
    for idx, path in enumerate(file_paths, start=1):
        # Log first file to debug hanging
        if idx == 1:
            if ui:
                ui.log_line(f"[formatter] Processing first file: {path}")
            else:
                print(f"[formatter] Processing first file: {path}")
        
        # progress
        if ui:
            ui.set_progress(done, len(file_paths))

        status = "ok"
        note = ""
        attempts = 0
        edits = None
        pattern_result = None
        
        while attempts < max_attempts:
            try:
                edits = await format_once(path)
                
                # If no edits from ALS but patterns are enabled, we still need to process
                if not edits and pattern_formatter and pattern_formatter.enabled:
                    try:
                        original_content = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception as e:
                        raise TypeError(f"Failed to read file {path}: {e}") from e
                    
                    # Check file size limit
                    file_size = len(original_content.encode('utf-8'))
                    if file_size > patterns_max_bytes:
                        # Skip patterns for large files
                        pattern_logger.write({
                            'ev': 'file_skipped_large',
                            'path': str(path),
                            'size_bytes': file_size,
                            'max_bytes': patterns_max_bytes
                        })
                        if ui:
                            ui.log_line(f"[patterns] Skipping {path} - file too large ({file_size} bytes)")
                    else:
                        # Apply patterns to original content
                        formatted_content, pattern_result = pattern_formatter.apply(
                            path,
                            original_content,
                            timeout_ms=patterns_timeout_ms,
                            logger=PatternLogger(pattern_logger),
                            ui=ui
                        )
                        
                        # Check if patterns made changes
                        if formatted_content != original_content:
                            status = "changed"
                            changed += 1
                            
                            from .edits import unified_diff
                            from .utils import atomic_write
                            
                            if write:
                                # Write to file
                                atomic_write(str(path), formatted_content)
                            elif diff:
                                # Show diff in dry-run mode
                                diff_output = unified_diff(
                                    original_content,
                                    formatted_content,
                                    str(path)
                                )
                                if diff_output and not ui:
                                    print(diff_output)
                
                if edits:
                    status = "changed"
                    changed += 1
                    # Apply edits to get formatted content
                    try:
                        original_content = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception as e:
                        raise TypeError(f"Failed to read file {path}: {e}") from e
                    
                    from .edits import apply_text_edits, unified_diff
                    from .utils import atomic_write
                    formatted_content = apply_text_edits(original_content, edits)
                    
                    # Apply patterns if enabled and ALS succeeded
                    pattern_result = None
                    if pattern_formatter and pattern_formatter.enabled:
                        # Check file size limit
                        file_size = len(formatted_content.encode('utf-8'))
                        if file_size > patterns_max_bytes:
                            # Skip patterns for large files
                            pattern_logger.write({
                                'ev': 'file_skipped_large',
                                'path': str(path),
                                'size_bytes': file_size,
                                'max_bytes': patterns_max_bytes
                            })
                            if ui:
                                ui.log_line(f"[patterns] Skipping {path} - file too large ({file_size} bytes)")
                        else:
                            # Apply patterns
                            formatted_content, pattern_result = pattern_formatter.apply(
                                path,
                                formatted_content,
                                timeout_ms=patterns_timeout_ms,
                                logger=PatternLogger(pattern_logger),
                                ui=ui
                            )
                    
                    if write:
                        # Write to file
                        atomic_write(str(path), formatted_content)
                    elif diff:
                        # Show diff in dry-run mode
                        diff_output = unified_diff(
                            original_content,
                            formatted_content,
                            str(path)
                        )
                        if diff_output and not ui:
                            print(diff_output)
                consecutive_timeouts = 0
                break  # Success, exit retry loop
            
            except asyncio.TimeoutError:
                attempts += 1
                consecutive_timeouts += 1
                if attempts >= max_attempts:
                    status = "failed"
                    # note = "TimeoutError: ALS did not respond in time"  # Details in stderr log
                    failed += 1
                    if logger:
                        logger.write({
                            "path": str(path),
                            "status": status,
                            "note": note,
                            "error": "TimeoutError",
                            "format_timeout": format_timeout,
                            "attempts": attempts,
                        })
                    _write_stderr_error(
                        path=path,
                        error_type="TIMEOUT",
                        error_msg="TimeoutError: ALS did not respond in time",
                        details={
                            "attempts": attempts,
                            "format_timeout_s": format_timeout,
                            "action": "ALS unresponsive to formatting request",
                            "suggestion": "Try lower timeout or increase --init-timeout; check ALS log",
                        },
                    )
                    # Break or abort on too many consecutive timeouts
                    if max_consecutive_timeouts and consecutive_timeouts >= max_consecutive_timeouts:
                        _write_stderr_error(
                            path=path,
                            error_type="TIMEOUT_BARRIER",
                            error_msg=f"Aborting after {consecutive_timeouts} consecutive timeouts",
                            details={"action": "Investigate ALS; try --preflight aggressive, increase --init-timeout"},
                        )
                        raise RuntimeError("Too many consecutive timeouts")
                    break
                # Controlled restart before retry
                with contextlib.suppress(Exception):
                    await client.restart()
                continue
            
            except ALSProtocolError as e:
                # Handle syntax errors
                if getattr(e.payload, "code", None) == -32803 or "-32803" in str(e) or "Syntactically invalid code" in str(e):
                    # Log the error details
                    error_msg = ""
                    if hasattr(e, 'payload') and isinstance(e.payload, dict):
                        error_msg = e.payload.get('message', str(e.payload))
                        if 'data' in e.payload:
                            error_msg += f" - {e.payload['data']}"
                    else:
                        error_msg = str(e)
                    
                    if logger:
                        logger.write({
                            "path": str(path),
                            "als_error": "Syntax error detected by ALS",
                            "error_details": error_msg,
                            "error_code": -32803,
                        })
                    
                    # Write detailed error to stderr
                    _write_stderr_error(
                        path=path,
                        error_type="ALS_SYNTAX_ERROR",
                        error_msg=error_msg,
                        details={
                            "error_code": "-32803",
                            "description": "ALS reported syntactically invalid code"
                        }
                    )
                    
                    # Try to compile to verify
                    compile_success = False
                    compiler_msg = ""
                    
                    if path.suffix.lower() in (".adb", ".ada"):
                        try:
                            import subprocess
                            compile_cwd = client._launch_cwd if hasattr(client, '_launch_cwd') else None
                            
                            compile_cmd = ["gcc", "-c", "-gnatc", str(path)]
                            
                            if proj and proj.exists():
                                compile_cmd.extend(["-P", str(proj)])
                            
                            result = subprocess.run(
                                compile_cmd,
                                cwd=compile_cwd,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            compile_success = (result.returncode == 0)
                            if compile_success:
                                compiler_msg = "Compiler OK, GNATFORMAT false positive"
                            else:
                                compiler_msg = "Compiler also reports errors"
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            compile_success = False
                            compiler_msg = "Could not verify with compiler"
                    else:
                        compiler_msg = "Spec file - not compiled"
                    
                    if compile_success:
                        # False positive from GNATFORMAT!
                        status = "ok"
                        note = "GNATFORMAT false positive - file compiles OK!"
                        false_positives += 1
                        if logger:
                            logger.write({
                                "path": str(path),
                                "warning": "GNATFORMAT reported syntax error but file compiles successfully",
                                "als_error": str(e),
                            })
                        warning_msg = f"[warning] {path.name}: GNATFORMAT syntax error but compiles OK"
                        if ui:
                            ui.log_line(warning_msg)
                        else:
                            print(f"\033[93m{warning_msg}\033[0m")  # Yellow color
                    else:
                        # Real syntax error
                        status = "failed"
                        # note = f"syntax error: {error_msg}" if error_msg else f"invalid syntax (GNATFORMAT) - {compiler_msg}"  # Details in stderr log
                        failed += 1
                        
                        # Write detailed error to stderr for real syntax errors
                        error_message = f"syntax error: {error_msg}" if error_msg else f"invalid syntax (GNATFORMAT) - {compiler_msg}"
                        _write_stderr_error(
                            path=path,
                            error_type="SYNTAX_ERROR_CONFIRMED",
                            error_msg=error_message,
                            details={
                                "als_error": error_msg,
                                "compiler_verification": compiler_msg,
                                "action": "Manual fix required - file has syntax errors"
                            }
                        )
                    break  # No retry for syntax errors
                # other protocol errors: attempt restart
                attempts += 1
                if attempts >= max_attempts:
                    status = "failed"
                    # note = f"ALS error: {getattr(e, 'message', repr(e))}"  # Details in stderr log
                    failed += 1
                    
                    # Write detailed error to stderr
                    _write_stderr_error(
                        path=path,
                        error_type="ALS_PROTOCOL_ERROR",
                        error_msg=f"ALS error: {getattr(e, 'message', repr(e))}",
                        details={
                            "error_class": e.__class__.__name__,
                            "attempts": attempts,
                            "action": "ALS communication failed after retries"
                        }
                    )
                    break
                with contextlib.suppress(Exception):
                    await client.restart()
            except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
                attempts += 1
                if attempts >= max_attempts:
                    status = "failed"
                    # note = f"disconnected: {e.__class__.__name__}"  # Details in stderr log
                    failed += 1
                    
                    # Write detailed error to stderr
                    _write_stderr_error(
                        path=path,
                        error_type="CONNECTION_ERROR",
                        error_msg=f"disconnected: {e.__class__.__name__}",
                        details={
                            "error_class": e.__class__.__name__,
                            "attempts": attempts,
                            "action": "ALS connection lost, unable to recover"
                        }
                    )
                    break
                with contextlib.suppress(Exception):
                    await client.restart()
            except Exception as e:
                attempts += 1
                if attempts >= max_attempts:
                    status = "failed"
                    # note = f"{type(e).__name__}: {str(e)}"  # Details in stderr log
                    failed += 1
                    if logger:
                        logger.write({
                            "path": str(path),
                            "error": type(e).__name__,
                            "error_message": str(e),
                            "traceback": "See log for details"
                        })
                    
                    # Write detailed error to stderr
                    _write_stderr_error(
                        path=path,
                        error_type="UNEXPECTED_ERROR",
                        error_msg=f"{type(e).__name__}: {str(e)}",
                        details={
                            "error_class": type(e).__name__,
                            "attempts": attempts,
                            "action": "Unexpected error during formatting",
                            "suggestion": "Check ALS logs for more details"
                        }
                    )
                    break
                with contextlib.suppress(Exception):
                    await client.restart()

        # Log file event to pattern log
        pattern_logger.write({
            'ev': 'file',
            'path': str(path),
            'als_ok': status != "failed",
            'als_edits': len(edits) if edits else 0,
            'patterns_applied': pattern_result.applied_names if pattern_result else [],
            'replacements': pattern_result.replacements_sum if pattern_result else 0
        })
        
        done += 1
        prefix = f"[{idx:>4}/{total}]"
        
        # Add debug output every 50 files
        if idx % 50 == 0:
            pass  # Debug output removed
        
        # Build pattern info for status line (only show if patterns were applied)
        pattern_info = ""
        if pattern_formatter and pattern_formatter.enabled and pattern_result:
            patterns_applied = len(pattern_result.applied_names)
            replacements = pattern_result.replacements_sum
            if patterns_applied > 0:
                pattern_info = f" | Patterns: applied={patterns_applied} ({replacements})"
        
        line = f"{prefix} [{status:^7}] {path}"
        if no_als:
            # In patterns-only mode, don't show ALS status
            pass
        elif edits:
            line += f" | ALS: ✓ edits={len(edits)}"
        else:
            line += " | ALS: ✓ edits=0"
        line += pattern_info
        
        if status == "failed":
            line += "  (details in the stderr log)"
        elif note:
            line += f"  ({note})"
        if ui:
            ui.log_line(line)
            ui.set_progress(done, len(file_paths))
            # Update the 4-line footer
            current_time = time.time()
            elapsed = current_time - run_start_time
            rate = done / elapsed if elapsed > 0 else 0
            ui.update_footer_stats(
                total=len(file_paths),
                changed=changed,
                unchanged=done - changed - failed,
                failed=failed,
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
                # Color [failed ] in bright red (with padding)
                if "[failed ]" in line:
                    start_idx = line.find("[failed ]")
                    end_idx = start_idx + len("[failed ]")
                    colored_line = line[:start_idx] + "\033[91m\033[1m[failed ]\033[0m" + line[end_idx:]
                # Color [changed] in bright yellow (with padding)
                elif "[changed]" in line:
                    start_idx = line.find("[changed]")
                    end_idx = start_idx + len("[changed]")
                    colored_line = line[:start_idx] + "\033[93m\033[1m[changed]\033[0m" + line[end_idx:]
                print(colored_line)
            else:
                print(line)

        if logger:
            logger.write({
                "path": str(path),
                "status": status,
                "note": note,
            })

    # Calculate statistics
    end_time = time.time()
    elapsed_seconds = max(0.1, end_time - run_start_time)
    unchanged = len(file_paths) - changed - failed
    rate = len(file_paths) / elapsed_seconds if len(file_paths) > 0 else 0

    # Update final UI state before shutdown
    if ui:
        ui.set_progress(len(file_paths), len(file_paths))
        # Final footer update
        ui.update_footer_stats(
            total=len(file_paths),
            changed=changed,
            unchanged=unchanged,
            failed=failed,
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
    pattern_start_time = datetime.fromtimestamp(run_start_time + warmup_seconds, tz=timezone.utc)
    pattern_end_time = adafmt_end_time
    
    # Calculate pattern processing time
    pattern_elapsed = 0
    if pattern_formatter and pattern_formatter.enabled:
        # Rough estimate: patterns take about 10% of total processing time
        pattern_elapsed = elapsed_seconds * 0.1
    
    als_elapsed = elapsed_seconds - pattern_elapsed
    
    # Print formatted metrics
    print("\n" + "=" * 80)
    # ALS Metrics
    print("ALS METRICS")
    total = len(file_paths)
    pct_changed = (changed * 100 // total) if total > 0 else 0
    pct_unchanged = (unchanged * 100 // total) if total > 0 else 0
    pct_failed = (failed * 100 // total) if total > 0 else 0
    
    # File statistics table
    file_stats = [
        ["Files", total, "100%"],
        ["Changed", changed, f"{pct_changed}%"],
        ["Unchanged", unchanged, f"{pct_unchanged}%"],
        ["Failed", failed, f"{pct_failed}%"]
    ]
    
    # Print table with 2-space indent
    table_str = tabulate(file_stats, tablefmt="plain", colalign=("left", "right", "right"))
    for line in table_str.split('\n'):
        print(f"  {line}")
    
    # Show Started timestamp before other timing info (no blank line)
    print(f"  Started    {als_start_time.strftime('%Y%m%dT%H%M%SZ')}")
    
    # Timing table (without Started since it's shown above)
    timing_data = [
        ["Completed", adafmt_end_time.strftime('%Y%m%dT%H%M%SZ')],
        ["Elapsed", f"{als_elapsed:.1f}s"],
        ["Rate", f"{rate:.1f} files/s"]
    ]
    table_str = tabulate(timing_data, tablefmt="plain")
    for line in table_str.split('\n'):
        print(f"  {line}")
    
    # Pattern Metrics if enabled
    if pattern_formatter and pattern_formatter.enabled:
        pattern_summary = pattern_formatter.get_summary()
        print("\nPATTERN METRICS")
        
        if pattern_summary:
            # Build pattern data table
            pattern_data = []
            total_files = 0
            total_replacements = 0
            total_failures = 0
            
            for name, metrics in sorted(pattern_summary.items()):
                files_touched = metrics['files_touched']
                replacements = metrics['replacements']
                failures = 0  # Pattern failures aren't tracked yet
                
                pattern_data.append([name, files_touched, replacements, failures])
                total_files += files_touched
                total_replacements += replacements
                total_failures += failures
            
            # Add separator and totals
            pattern_data.append(["--------", "-------", "--------", "------"])
            pattern_data.append(["Totals", total_files, total_replacements, total_failures])
            
            # Print table with consistent alignment
            headers = ["Pattern", "Applied", "Replaced", "Failed"]
            table_str = tabulate(pattern_data, headers=headers, tablefmt="simple", colalign=("left", "right", "right", "right"))
            for line in table_str.split('\n'):
                print(f"  {line}")
        else:
            print("  No patterns were applied to any files")
        
        # Leave blank line before timing info
        print()
        
        # Show Started timestamp before other timing info (aligned with table)
        print(f"  Started              {pattern_start_time.strftime('%Y%m%dT%H%M%SZ')}")
        
        # Pattern timing table (without Started since it's shown above)
        pattern_timing_data = [
            ["Completed", pattern_end_time.strftime('%Y%m%dT%H%M%SZ')],
            ["Elapsed", f"{pattern_elapsed:.1f}s"]
        ]
        
        if pattern_elapsed > 0:
            # Primary rate: same as ALS (total files scanned)
            scan_rate = len(file_paths) / pattern_elapsed
            pattern_timing_data.append(["Rate (scanned)", f"{scan_rate:.1f} files/s"])
            
            # Additional pattern-specific rates  
            if pattern_summary:
                if 'total_files' in locals() and total_files > 0:  # Pattern applications
                    applied_rate = total_files / pattern_elapsed
                    pattern_timing_data.append(["Rate (applied)", f"{applied_rate:.1f} patterns/s"])
                if 'total_replacements' in locals() and total_replacements > 0:  # Replacements
                    replacements_rate = total_replacements / pattern_elapsed
                    pattern_timing_data.append(["Rate (replacements)", f"{replacements_rate:.1f} replacements/s"])
        
        table_str = tabulate(pattern_timing_data, tablefmt="plain")
        for line in table_str.split('\n'):
            print(f"  {line}")
    
    # Final summary
    print()
    print("ADAFMT RUN")
    completion_data = [
        ["Started", adafmt_start_time.strftime('%Y%m%dT%H%M%SZ')],
        ["Completed", adafmt_end_time.strftime('%Y%m%dT%H%M%SZ')],
        ["Total Elapsed", f"{elapsed_seconds:.1f}s"]
    ]
    table_str = tabulate(completion_data, tablefmt="plain")
    for line in table_str.split('\n'):
        print(f"  {line}")

    # Print log paths to stdout after UI closes so they're copyable
    if ui and (log_path or (client and client.als_log_path) or stderr_path):
        print("\nLOG FILES")
        
        # Build log files table
        log_files = []
        
        # Main Log
        if log_path:
            log_display = f"./{log_path} (default location)" if using_default_log else str(log_path)
            log_files.append(["Main Log", log_display])
        else:
            log_files.append(["Main Log", "Not configured"])
        
        # Pattern Log
        pattern_log_display = f"./{pattern_log_path} (default location)" if using_default_patterns else str(pattern_log_path)
        log_files.append(["Pattern Log", pattern_log_display])
        
        # Stderr
        if stderr_path:
            stderr_display = f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path)
            log_files.append(["Stderr", stderr_display])
        else:
            log_files.append(["Stderr", "Not configured"])
        
        # ALS Log
        if not no_als:
            als_log_display = (client.als_log_path if client else None) or "~/.als/ada_ls_log.*.log (default location)"
            log_files.append(["ALS Log", als_log_display])
        
        # Print table with consistent formatting
        table_str = tabulate(log_files, tablefmt="plain")
        for line in table_str.split('\n'):
            print(f"  {line}")
        print("=" * 80)

    # Log pattern run_end event
    pattern_logger.write({
        'ev': 'run_end',
        'files_total': len(file_paths),
        'files_als_ok': len(file_paths) - failed,
        'patterns_loaded': pattern_formatter.loaded_count if pattern_formatter else 0,
        'patterns_summary': pattern_formatter.get_summary() if pattern_formatter else {}
    })
    
    # Shutdown ALS after UI updates
    with contextlib.suppress(Exception):
        if client:
                await client.shutdown()

    # Close logger to ensure all data is written
    if logger:
        logger.close()

    # Post-hook (do not fail the overall run if it fails)
    if post_hook:
        run_hook(post_hook, "post", logger=(ui.log_line if ui else print) if ui else print, dry_run=False)

    if check and changed:
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
    diff: Annotated[bool, typer.Option("--diff", help="Show unified diffs of changes [default: True]")] = True,
    exclude_path: Annotated[Optional[List[Path]], typer.Option("--exclude-path", help="Directory to exclude from search (can be used multiple times)")] = None,
    format_timeout: Annotated[int, typer.Option("--format-timeout", help="Timeout per file formatting in seconds")] = 60,
    include_path: Annotated[Optional[List[Path]], typer.Option("--include-path", help="Directory to search for Ada files (can be used multiple times)")] = None,
    init_timeout: Annotated[int, typer.Option("--init-timeout", help="Timeout for ALS initialization in seconds")] = 180,
    log_path: Annotated[Optional[Path], typer.Option("--log-path", help="Override JSONL log location (default: ./adafmt_<timestamp>_log.jsonl)")] = None,
    max_attempts: Annotated[int, typer.Option("--max-attempts", help="Retry attempts for transient errors")] = 2,
    post_hook: Annotated[Optional[str], typer.Option("--post-hook", help="Command to run after formatting; non-zero exit is logged. 60s timeout.")] = None,
    pre_hook: Annotated[Optional[str], typer.Option("--pre-hook", help="Command to run before formatting; non-zero exit aborts. 60s timeout.")] = None,
    preflight: Annotated[PreflightMode, typer.Option("--preflight", help="Handle existing ALS processes and .als-alire locks")] = PreflightMode.safe,
    stderr_path: Annotated[Optional[Path], typer.Option("--stderr-path", help="Override stderr capture location (default: ./adafmt_<timestamp>_stderr.log)")] = None,
    # UI option disabled - always uses plain UI for better scrollback
    # The graphical UI has been removed in favor of plain text output
    # ui: Annotated[UIMode, typer.Option("--ui", help="UI mode")] = UIMode.auto,
    warmup_seconds: Annotated[int, typer.Option("--warmup-seconds", help="Time to let ALS warm up in seconds")] = 10,
    patterns_path: Annotated[Optional[Path], typer.Option("--patterns-path", help="Path to patterns JSON file (default: ./adafmt_patterns.json)")] = None,
    no_patterns: Annotated[bool, typer.Option("--no-patterns", help="Disable pattern processing")] = False,
    patterns_timeout_ms: Annotated[int, typer.Option("--patterns-timeout-ms", help="Timeout per pattern in milliseconds")] = 50,
    patterns_max_bytes: Annotated[int, typer.Option("--patterns-max-bytes", help="Skip patterns for files larger than this (bytes)")] = 10485760,
    validate_patterns: Annotated[bool, typer.Option("--validate-patterns", help="Validate that applied patterns are acceptable to ALS")] = False,
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
    # Import path validator
    from .path_validator import validate_path
    
    # Convert project path to absolute and validate
    abs_project_path = _abs(str(project_path))
    validation_error = validate_path(abs_project_path)
    if validation_error:
        typer.echo(f"Error: Invalid project path '{project_path}' (resolved to '{abs_project_path}') - {validation_error}", err=True)
        raise typer.Exit(2)
    project_path = Path(abs_project_path)
    if not project_path.exists():
        typer.echo(f"Error: Project file not found: {project_path}", err=True)
        raise typer.Exit(2)
    if not project_path.is_file():
        typer.echo(f"Error: Project path is not a file: {project_path}", err=True)
        raise typer.Exit(2)
    if not os.access(project_path, os.R_OK):
        typer.echo(f"Error: Project file is not readable: {project_path}", err=True)
        raise typer.Exit(2)
    
    # Validate: Must have include paths or specific files
    if not include_path and not files:
        typer.echo("Error: No files or directories to process. You must provide --include-path or specific files.", err=True)
        typer.echo("Use 'adafmt format --help' for usage information.", err=True)
        raise typer.Exit(2)
    
    # Validate conflicting options
    if no_patterns and no_als:
        typer.echo("Error: Cannot use both --no-patterns and --no-als (nothing to do)", err=True)
        raise typer.Exit(2)
    
    if validate_patterns and no_als:
        typer.echo("Error: Cannot use --validate-patterns with --no-als (validation requires ALS)", err=True)
        raise typer.Exit(2)
        
    if validate_patterns and no_patterns:
        typer.echo("Error: Cannot use --validate-patterns with --no-patterns (no patterns to validate)", err=True)
        raise typer.Exit(2)
    
    # Validate include paths
    include_paths = []
    if include_path:
        for p in include_path:
            # First resolve to absolute path
            abs_path_str = _abs(str(p))
            validation_error = validate_path(abs_path_str)
            if validation_error:
                typer.echo(f"Error: Invalid include path '{p}' (resolved to '{abs_path_str}') - {validation_error}", err=True)
                raise typer.Exit(2)
            abs_path = Path(abs_path_str)
            if not abs_path.exists():
                typer.echo(f"Error: Include path not found: {abs_path}", err=True)
                raise typer.Exit(2)
            if not os.access(abs_path, os.R_OK):
                typer.echo(f"Error: Include path is not readable: {abs_path}", err=True)
                raise typer.Exit(2)
            include_paths.append(abs_path)
    
    # Validate exclude paths
    exclude_paths = []
    if exclude_path:
        for p in exclude_path:
            # First resolve to absolute path
            abs_path_str = _abs(str(p))
            validation_error = validate_path(abs_path_str)
            if validation_error:
                typer.echo(f"Error: Invalid exclude path '{p}' (resolved to '{abs_path_str}') - {validation_error}", err=True)
                raise typer.Exit(2)
            abs_path = Path(abs_path_str)
            if not abs_path.exists():
                typer.echo(f"Error: Exclude path not found: {abs_path}", err=True)
                raise typer.Exit(2)
            exclude_paths.append(abs_path)
    
    # Validate patterns path if provided
    if patterns_path:
        # First resolve to absolute path
        abs_patterns_path = _abs(str(patterns_path))
        validation_error = validate_path(abs_patterns_path)
        if validation_error:
            typer.echo(f"Error: Invalid patterns path '{patterns_path}' (resolved to '{abs_patterns_path}') - {validation_error}", err=True)
            raise typer.Exit(2)
        patterns_path = Path(abs_patterns_path)
        # Will check existence later in run_formatter
    
    # Validate file arguments if provided
    validated_files = []
    if files:
        for f in files:
            # First resolve to absolute path
            abs_file_str = _abs(f)
            validation_error = validate_path(abs_file_str)
            if validation_error:
                typer.echo(f"Error: Invalid file path '{f}' (resolved to '{abs_file_str}') - {validation_error}", err=True)
                raise typer.Exit(2)
            # Check existence
            abs_file = Path(abs_file_str)
            if not abs_file.exists():
                typer.echo(f"Error: File not found: {abs_file}", err=True)
                raise typer.Exit(2)
            if not abs_file.is_file():
                typer.echo(f"Error: Path is not a file: {abs_file}", err=True)
                raise typer.Exit(2)
            # Check if it's an Ada file
            if not _is_ada_file(abs_file):
                typer.echo(f"Error: Not an Ada file (must have .ads, .adb, or .ada extension): {abs_file}", err=True)
                raise typer.Exit(2)
            # Check if readable
            if not os.access(abs_file, os.R_OK):
                typer.echo(f"Error: File is not readable: {abs_file}", err=True)
                raise typer.Exit(2)
            validated_files.append(f)
        files = validated_files
    
    # Validate log path if provided
    if log_path:
        # First resolve to absolute path
        abs_log_path = _abs(str(log_path))
        validation_error = validate_path(abs_log_path)
        if validation_error:
            typer.echo(f"Error: Invalid log path '{log_path}' (resolved to '{abs_log_path}') - {validation_error}", err=True)
            raise typer.Exit(2)
    
    # Validate stderr path if provided
    if stderr_path:
        # First resolve to absolute path
        abs_stderr_path = _abs(str(stderr_path))
        validation_error = validate_path(abs_stderr_path)
        if validation_error:
            typer.echo(f"Error: Invalid stderr path '{stderr_path}' (resolved to '{abs_stderr_path}') - {validation_error}", err=True)
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
        ui_mode="plain",  # Hardcoded to plain UI
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
        validate_patterns=validate_patterns,
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