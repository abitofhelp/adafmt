# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Final reporting and cleanup for the Ada formatter."""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Any

from .metrics_reporter import MetricsReporter
from .file_processor import FileProcessor
from .pattern_formatter import PatternFormatter
from .als_client import ALSClient
from .logging_jsonl import JsonlLogger


async def finalize_and_report(
    file_processor: FileProcessor,
    file_paths: List[Path],
    run_start_time: float,
    als_ready_timeout: int,
    log_path: Path,
    stderr_path: Optional[Path],
    pattern_log_path: Path,
    using_default_log: bool,
    using_default_stderr: bool,
    using_default_patterns: bool,
    pattern_logger: JsonlLogger,
    client: Optional[ALSClient],
    pattern_formatter: Optional[PatternFormatter],
    ui: Optional[Any],
    no_als: bool,
    check: bool,
    post_hook: Optional[str],
    hook_timeout: float,
    debug_pattern_log_path: Optional[Path] = None,
    debug_als_log_path: Optional[Path] = None,
    using_default_debug_patterns: bool = False,
    using_default_debug_als: bool = False
) -> int:
    """
    Handle final metrics calculation, reporting, and cleanup.
    
    Returns:
        Exit code (0 for success, 1 if changes found in check mode)
    """
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
    adafmt_start_time = datetime.fromtimestamp(run_start_time, tz=timezone.utc)
    adafmt_end_time = datetime.fromtimestamp(end_time, tz=timezone.utc)
    
    # Estimate ALS and pattern processing times
    # ALS processing includes warmup + file processing
    als_start_time = adafmt_start_time
    # Pattern processing happens during file processing, estimate based on timing
    pattern_start_time = datetime.fromtimestamp(run_start_time + (als_ready_timeout if client else 0), tz=timezone.utc)
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
        # Debug log paths
        debug_pattern_log_path=debug_pattern_log_path,
        debug_als_log_path=debug_als_log_path,
        using_default_debug_patterns=using_default_debug_patterns,
        using_default_debug_als=using_default_debug_als
    )
    
    # Log pattern run_end event
    # Calculate total patterns applied from files_touched
    total_patterns_applied = sum(pattern_formatter.files_touched.values()) if pattern_formatter else 0
    pattern_logger.write({
        'ev': 'run_end',
        'patterns_applied': total_patterns_applied,
        'files_with_patterns': pattern_files_changed,
        'elapsed_seconds': pattern_elapsed
    })
    
    # Shutdown ALS client
    if client:
        await client.shutdown()
    
    # Run post-hook if provided
    if post_hook:
        from .utils import run_hook
        run_hook(post_hook, "post", logger=(ui.log_line if ui else print) if ui else print, timeout=hook_timeout, dry_run=False)

    if check and total_changed:
        return 1
    return 0