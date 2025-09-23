# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Metrics reporting functionality for the Ada formatter."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any
from tabulate import tabulate  # type: ignore[import-untyped]

from .utils import to_iso8601_basic

from .als_client import ALSClient
from .pattern_formatter import PatternFormatter


class MetricsReporter:
    """Handles formatting and display of metrics after processing."""
    
    def __init__(self):
        """Initialize the metrics reporter."""
        pass
    
    def print_summary(
        self,
        *,
        # File counts
        file_paths: List[Path],
        als_changed: int,
        als_failed: int,
        als_unchanged: int,
        # Timing info
        run_start_time: float,
        run_end_time: float,
        pattern_elapsed: float,
        # Timestamps
        adafmt_start_time: datetime,
        adafmt_end_time: datetime,
        als_start_time: Optional[datetime] = None,
        pattern_start_time: Optional[datetime] = None,
        pattern_end_time: Optional[datetime] = None,
        # Components
        client: Optional[ALSClient] = None,
        pattern_formatter: Optional[PatternFormatter] = None,
        # Log paths
        log_path: Optional[Path] = None,
        stderr_path: Optional[Path] = None,
        pattern_log_path: Optional[Path] = None,
        using_default_log: bool = False,
        using_default_stderr: bool = False,
        using_default_patterns: bool = False,
        no_als: bool = False,
        ui: Any = None,
        # Debug log paths
        debug_pattern_log_path: Optional[Path] = None,
        debug_als_log_path: Optional[Path] = None,
        using_default_debug_patterns: bool = False,
        using_default_debug_als: bool = False
    ) -> None:
        """Print the complete metrics summary.
        
        Args:
            file_paths: List of files processed
            als_changed: Number of files changed by ALS
            als_failed: Number of files that failed ALS processing
            als_unchanged: Number of files unchanged by ALS
            run_start_time: Start time in seconds since epoch
            run_end_time: End time in seconds since epoch
            pattern_elapsed: Time spent on pattern processing
            adafmt_start_time: Overall start timestamp
            adafmt_end_time: Overall end timestamp
            als_start_time: ALS processing start timestamp
            pattern_start_time: Pattern processing start timestamp
            pattern_end_time: Pattern processing end timestamp
            client: ALS client instance
            pattern_formatter: Pattern formatter instance
            log_path: Main log file path
            stderr_path: Stderr log file path
            pattern_log_path: Pattern log file path
            using_default_log: Whether using default log location
            using_default_stderr: Whether using default stderr location
            using_default_patterns: Whether using default pattern log location
            no_als: Whether ALS is disabled
            ui: UI instance
        """
        elapsed_seconds = max(0.1, run_end_time - run_start_time)
        als_elapsed = elapsed_seconds - pattern_elapsed
        rate = len(file_paths) / elapsed_seconds if len(file_paths) > 0 else 0
        
        # Print separator
        print("\n" + "=" * 80)
        
        # ALS Metrics
        if client and als_start_time is not None:
            self._print_als_metrics(
                file_paths, als_changed, als_unchanged, als_failed,
                als_start_time, adafmt_end_time, als_elapsed, rate
            )
        
        # Pattern Metrics
        if pattern_formatter and pattern_formatter.enabled and pattern_start_time is not None and pattern_end_time is not None:
            self._print_pattern_metrics(
                file_paths, pattern_formatter, client,
                pattern_start_time, pattern_end_time, pattern_elapsed
            )
        
        # Overall Run Summary
        self._print_run_summary(adafmt_start_time, adafmt_end_time, elapsed_seconds)
        
        # Log Files
        self._print_log_files(
            log_path, stderr_path, pattern_log_path,
            client, no_als, ui,
            using_default_log, using_default_stderr, using_default_patterns,
            debug_pattern_log_path, debug_als_log_path,
            using_default_debug_patterns, using_default_debug_als
        )
        
        # Final separator
        print("=" * 80)
    
    def _print_als_metrics(
        self,
        file_paths: List[Path],
        als_changed: int,
        als_unchanged: int,
        als_failed: int,
        als_start_time: datetime,
        adafmt_end_time: datetime,
        als_elapsed: float,
        rate: float
    ) -> None:
        """Print ALS metrics section."""
        print("ALS METRICS")
        total = len(file_paths)
        pct_changed = (als_changed * 100 // total) if total > 0 else 0
        pct_unchanged = (als_unchanged * 100 // total) if total > 0 else 0
        pct_failed = (als_failed * 100 // total) if total > 0 else 0
        
        # File statistics table
        file_stats = [
            ["Files", total, "100%"],
            ["Changed", als_changed, f"{pct_changed}%"],
            ["Unchanged", als_unchanged, f"{pct_unchanged}%"],
            ["Failed", als_failed, f"{pct_failed}%"]
        ]
        
        # Print table with 2-space indent
        table_str = tabulate(file_stats, tablefmt="plain", colalign=("left", "right", "right"))
        for line in table_str.split('\n'):
            print(f"  {line}")
        
        # Show Started timestamp
        print(f"  Started    {to_iso8601_basic(als_start_time)}")
        
        # Timing table
        timing_data = [
            ["Completed", to_iso8601_basic(adafmt_end_time)],
            ["Elapsed", f"{als_elapsed:.1f}s"],
            ["Rate", f"{rate:.1f} files/s"]
        ]
        table_str = tabulate(timing_data, tablefmt="plain")
        for line in table_str.split('\n'):
            print(f"  {line}")
    
    def _print_pattern_metrics(
        self,
        file_paths: List[Path],
        pattern_formatter: PatternFormatter,
        client: Optional[ALSClient],
        pattern_start_time: datetime,
        pattern_end_time: datetime,
        pattern_elapsed: float
    ) -> None:
        """Print pattern metrics section."""
        pattern_summary = pattern_formatter.get_summary()
        
        # Add newline only if ALS metrics were shown
        if client:
            print("\nPATTERN METRICS")
        else:
            print("PATTERN METRICS")
        
        # Always show Files row at the top
        total = len(file_paths)
        print(f"  Files      {total:>6}  100%")
        
        if pattern_summary:
            print()  # blank line after Files
            
            # Build pattern data table
            pattern_data = []
            total_files = 0
            total_replacements = 0
            total_failures = 0
            
            for name, pattern_stats in sorted(pattern_summary.items()):
                files_touched = pattern_stats['files_touched']
                replacements = pattern_stats['replacements']
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
            table_str = tabulate(pattern_data, headers=headers, tablefmt="simple", 
                                colalign=("left", "right", "right", "right"))
            for line in table_str.split('\n'):
                print(f"  {line}")
        else:
            print()  # blank line after Files
            print("  No patterns were applied to any files")
        
        # Leave blank line before timing info
        print()
        
        # Show Started timestamp
        print(f"  Started              {to_iso8601_basic(pattern_start_time)}")
        
        # Pattern timing table
        pattern_timing_data = [
            ["Completed", to_iso8601_basic(pattern_end_time)],
            ["Elapsed", f"{pattern_elapsed:.1f}s"]
        ]
        
        if pattern_elapsed > 0:
            # Primary rate: same as ALS (total files scanned)
            scan_rate = len(file_paths) / pattern_elapsed
            pattern_timing_data.append(["Rate (scanned)", f"{scan_rate:.1f} files/s"])
            
            # Additional pattern-specific rates
            if pattern_summary and total_files > 0:
                applied_rate = total_files / pattern_elapsed
                pattern_timing_data.append(["Rate (applied)", f"{applied_rate:.1f} patterns/s"])
            if pattern_summary and total_replacements > 0:
                replacements_rate = total_replacements / pattern_elapsed
                pattern_timing_data.append(["Rate (replacements)", f"{replacements_rate:.1f} replacements/s"])
        
        table_str = tabulate(pattern_timing_data, tablefmt="plain")
        for line in table_str.split('\n'):
            print(f"  {line}")
    
    def _print_run_summary(
        self,
        adafmt_start_time: datetime,
        adafmt_end_time: datetime,
        elapsed_seconds: float
    ) -> None:
        """Print overall run summary."""
        print()
        print("ADAFMT RUN")
        completion_data = [
            ["Started", to_iso8601_basic(adafmt_start_time)],
            ["Completed", to_iso8601_basic(adafmt_end_time)],
            ["Total Elapsed", f"{elapsed_seconds:.1f}s"]
        ]
        table_str = tabulate(completion_data, tablefmt="plain")
        for line in table_str.split('\n'):
            print(f"  {line}")
    
    def _print_log_files(
        self,
        log_path: Optional[Path],
        stderr_path: Optional[Path],
        pattern_log_path: Optional[Path],
        client: Optional[ALSClient],
        no_als: bool,
        ui: Any,
        using_default_log: bool,
        using_default_stderr: bool,
        using_default_patterns: bool,
        debug_pattern_log_path: Optional[Path] = None,
        debug_als_log_path: Optional[Path] = None,
        using_default_debug_patterns: bool = False,
        using_default_debug_als: bool = False
    ) -> None:
        """Print log file locations."""
        # Always print log files section
        print("\nLOG FILES")
        
        # Build log files table in the specified order
        log_files = []
        
        # 1. Adafmt Log
        if log_path:
            log_display = f"./{log_path} (default location)" if using_default_log else str(log_path)
            log_files.append(["Adafmt", log_display])
        else:
            log_files.append(["Adafmt", "Not configured"])
        
        # 2. ALS Log
        if not no_als:
            als_log_display = (client.als_log_path if client else None) or "~/.als/ada_ls_log.*.log (default location)"
            log_files.append(["ALS", als_log_display])
        
        # 3. Debug ALS Log (if present)
        if debug_als_log_path:
            if using_default_debug_als:
                debug_als_display = f"./{debug_als_log_path.name} (default location)"
            else:
                debug_als_display = str(debug_als_log_path)
            log_files.append(["Debug ALS", debug_als_display])
        
        # 4. Debug Pattern Log (if present)
        if debug_pattern_log_path:
            if using_default_debug_patterns:
                debug_patterns_display = f"./{debug_pattern_log_path.name} (default location)"
            else:
                debug_patterns_display = str(debug_pattern_log_path)
            log_files.append(["Debug Patterns", debug_patterns_display])
        
        # 5. Patterns Log
        pattern_log_display = f"./{pattern_log_path} (default location)" if using_default_patterns else str(pattern_log_path)
        log_files.append(["Patterns", pattern_log_display])
        
        # 6. Performance Log
        log_files.append(["Performance", "~/.adafmt/metrics.jsonl (default location)"])
        
        # 7. Stderr Log
        if stderr_path:
            stderr_display = f"./{stderr_path} (default location)" if using_default_stderr else str(stderr_path)
            log_files.append(["Stderr", stderr_display])
        else:
            log_files.append(["Stderr", "Not configured"])
        
        table_str = tabulate(log_files, tablefmt="plain", colalign=("left", "left"))
        for line in table_str.split('\n'):
            print(f"  {line}")