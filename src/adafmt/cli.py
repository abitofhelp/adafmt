# =============================================================================
# adafmt - Ada Language Formatter
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# Licensed under the MIT License. See LICENSE file in the project root.
# =============================================================================

"""Command-line interface for adafmt using Typer.

This module provides the main entry point for the adafmt tool, which formats
Ada source code using the Ada Language Server (ALS). It supports various UI
modes, Alire integration, and comprehensive error handling with retry logic.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import signal
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from enum import Enum

import typer
from typing_extensions import Annotated

from .als_client import ALSClient, ALSProtocolError, build_als_command
from .file_discovery import collect_files
from .logging_jsonl import JsonlLogger
from .tui import make_ui
from .utils import preflight, run_hook

# Version is dynamically read from package metadata
try:
    from importlib.metadata import version
    APP_VERSION = version("adafmt")
except Exception:
    # Fallback for development/editable installs
    APP_VERSION = "1.0.0"

# Global cleanup state
_cleanup_client: Optional[ALSClient] = None
_cleanup_ui = None
_cleanup_logger: Optional[JsonlLogger] = None
_cleanup_restore_stderr = None

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
            except:
                # Force kill the process if graceful shutdown fails
                if hasattr(_cleanup_client, '_proc') and _cleanup_client._proc:
                    try:
                        _cleanup_client._proc.terminate()
                    except:
                        pass
        
        if _cleanup_ui:
            with contextlib.suppress(Exception):
                _cleanup_ui.close()
        
        if _cleanup_logger:
            with contextlib.suppress(Exception):
                _cleanup_logger.close()
                
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
import atexit
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
    using_default_log: bool = False,
    using_default_stderr: bool = False) -> int:
    """Run the main formatting logic asynchronously."""
    run_start_time = time.time()
    
    proj = project_path
    includes = include_paths if include_paths else [proj.parent]
    excludes = exclude_paths
    
    # UI
    ui = make_ui(ui_mode) if ui_mode != "off" else None
    global _cleanup_ui
    _cleanup_ui = ui
    # --- Redirect stderr to the configured stderr file (suppress terminal output) ---
    class _Tee(io.TextIOBase):
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
        mode = "WRITE MODE" if write else "DRY RUN"
        ui.set_header("Ada Formatter", version=APP_VERSION, mode=mode)

    # logger - always create a logger (log_path is always set now)
    logger = JsonlLogger(log_path)
    logger.start_fresh()  # Create empty file, ensuring it exists
    global _cleanup_logger
    _cleanup_logger = logger

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


    # Initialize Ada Language Server client with configuration
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
    
    # Echo launch context for debugging
    launch_msg = f"[als] cwd={client._launch_cwd} cmd={client._launch_cmd}"
    if ui:
        ui.log_line(launch_msg)
    else:
        print(launch_msg)
    
    # Display log paths early so users know where to find them
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
    
    # Exit early if no files found
    if not file_paths:
        if ui:
            ui.log_line("[warning] No Ada files found in the specified paths")
            ui.close()
        else:
            print("[warning] No Ada files found in the specified paths")
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
        
        while attempts < max_attempts:
            try:
                edits = await format_once(path)
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
            
            except asyncio.TimeoutError as e:
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

        done += 1
        prefix = f"[{idx:>4}/{total}]"
        line = f"{prefix} [{status:<7}] {path}"
        if status == "failed":
            line += f"  (details in the stderr log)"
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
                als_log=client.als_log_path or "~/.als/ada_ls_log.*.log (default location)",
                stderr_log=f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path) if stderr_path else "Not configured"
            )
        else:
            # Color [failed ] in bright red if present and we're in a terminal
            if "[failed ]" in line and sys.stdout.isatty():
                start_idx = line.find("[failed ]")
                end_idx = start_idx + len("[failed ]")
                # Print with ANSI color codes for bright red
                colored_line = line[:start_idx] + "\033[91m\033[1m[failed ]\033[0m" + line[end_idx:]
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
            als_log=client.als_log_path or "~/.als/ada_ls_log.*.log (default location)",
            stderr_log=f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path) if stderr_path else "Not configured"
        )
        
        # Only show warnings if there were false positives
        if false_positives > 0:
            ui.log_line("")
            ui.log_line(f"Warning: GNATFORMAT reported {false_positives} false positive(s) (files compile OK)")
        
        # Add prompt
        ui.log_line("")
        ui.log_line("Press any key to exit...")
        
        # Wait for keypress while UI is still active
        ui.wait_for_key()
        
        ui.close()

    # Print log paths to stdout after UI closes so they're copyable
    if ui and (log_path or client.als_log_path or stderr_path):
        print("\nLog files:")
        if log_path:
            log_display = f"./{log_path} (default location)" if using_default_log else str(log_path)
            print(f"  Log:     {log_display}")
        else:
            print(f"  Log:     Not configured")
        
        # Stderr
        if stderr_path:
            stderr_display = f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path)
            print(f"  Stderr:  {stderr_display}")
        else:
            print(f"  Stderr:  Not configured")
        
        # ALS Log
        als_log_display = client.als_log_path or "~/.als/ada_ls_log.*.log (default location)"
        print(f"  ALS Log: {als_log_display}")

    # Shutdown ALS after UI updates
    with contextlib.suppress(Exception):
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


@app.command()
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
    ui: Annotated[UIMode, typer.Option("--ui", help="UI mode")] = UIMode.auto,
    warmup_seconds: Annotated[int, typer.Option("--warmup-seconds", help="Time to let ALS warm up in seconds")] = 10,

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
    # Convert paths to absolute
    project_path = Path(_abs(str(project_path)))
    include_paths = [Path(_abs(str(p))) for p in (include_path or [])]
    exclude_paths = [Path(_abs(str(p))) for p in (exclude_path or [])]
    
    
    # Generate default filenames with timestamp if not provided
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
        ui_mode=ui.value,
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
        using_default_log=using_default_log,
        using_default_stderr=using_default_stderr))
    
    raise typer.Exit(exit_code)


def main() -> None:
    """Entry point for the CLI."""
    app()

if __name__ == "__main__":
    main()