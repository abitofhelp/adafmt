# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""File processing logic for the Ada formatter."""

import asyncio
import contextlib
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from .als_client import ALSClient
from .edits import apply_text_edits, unified_diff
from .logging_jsonl import JsonlLogger
from .metrics import MetricsCollector
from .pattern_formatter import PatternFormatter, FileApplyResult
# UI is a protocol/interface, imported as TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .tui import UI
from .utils import atomic_write


class FileProcessor:
    """Handles processing of individual Ada files."""
    
    def __init__(
        self,
        *,
        client: Optional[ALSClient] = None,
        pattern_formatter: Optional[PatternFormatter] = None,
        logger: Optional[JsonlLogger] = None,
        pattern_logger: Optional[JsonlLogger] = None,
        ui: Optional['UI'] = None,
        metrics: Optional[MetricsCollector] = None,
        no_als: bool = False,
        write: bool = False,
        diff: bool = False,
        format_timeout: int = 60,
        max_consecutive_timeouts: int = 5
    ):
        """Initialize the file processor.
        
        Args:
            client: ALS client instance for formatting
            pattern_formatter: Pattern formatter instance
            logger: Main JSON logger
            pattern_logger: Pattern-specific logger
            ui: UI instance for interactive mode
            metrics: Metrics collector instance
            no_als: If True, skip ALS formatting
            write: If True, write changes to files
            diff: If True, show diffs
            format_timeout: Timeout for formatting operations
            max_consecutive_timeouts: Max consecutive timeouts before aborting
        """
        self.client = client
        self.pattern_formatter = pattern_formatter
        self.logger = logger
        self.pattern_logger = pattern_logger
        self.ui = ui
        self.metrics = metrics
        self.no_als = no_als
        self.write = write
        self.diff = diff
        self.format_timeout = format_timeout
        self.max_consecutive_timeouts = max_consecutive_timeouts
        
        # Statistics
        self.als_changed = 0
        self.als_failed = 0
        self.pattern_files_changed = 0
        self.total_errors = 0
        self.consecutive_timeouts = 0
        
    async def format_file_with_als(self, path: Path) -> List[Dict[str, Any]]:
        """Format a single Ada file using ALS.
        
        Args:
            path: Path to the file to format
            
        Returns:
            List of edits from ALS
            
        Raises:
            Various exceptions on formatting errors
        """
        if not self.client:
            return []
            
        # Open the file in ALS
        content = path.read_text(encoding="utf-8", errors="ignore")
        await self.client._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": path.as_uri(),
                "languageId": "ada",
                "version": 1,
                "text": content
            }
        })
        
        # Request formatting
        try:
            res = await self.client.request_with_timeout(
                {
                    "method": "textDocument/formatting",
                    "params": {
                        "textDocument": {"uri": path.as_uri()},
                        "options": {"tabSize": 3, "insertSpaces": True}
                    }
                },
                timeout=self.format_timeout
            )
        except asyncio.TimeoutError:
            res = None
            raise
        finally:
            # Always close the file
            with contextlib.suppress(Exception):
                await self.client._notify("textDocument/didClose", {"textDocument": {"uri": path.as_uri()}})
        
        # Validate response
        if res is not None and not isinstance(res, list):
            raise TypeError(f"ALS returned unexpected type: {type(res).__name__} instead of list")
        return res
    
    async def process_file(
        self,
        path: Path,
        idx: int,
        total: int,
        run_start_time: float
    ) -> Tuple[str, Optional[str]]:
        """Process a single file.
        
        Args:
            path: Path to the file
            idx: 1-based index of this file
            total: Total number of files
            run_start_time: Start time of the overall run
            
        Returns:
            Tuple of (status, note) where status is one of:
            - "changed": File was modified
            - "failed": Processing failed
            - "ok": File unchanged
        """
        file_start_time = time.time()
        
        # Check file size limit
        try:
            file_size = path.stat().st_size
            if file_size > 102400:  # 100KB
                if self.logger:
                    self.logger.write({
                        'ev': 'file_skipped_too_large',
                        'path': str(path),
                        'size_bytes': file_size,
                        'max_bytes': 102400
                    })
                if self.ui:
                    self.ui.log_line(f"[formatter] Skipping {path} - file too large ({file_size:,} bytes > 100KB)")
                else:
                    print(f"[formatter] Skipping {path} - file too large ({file_size:,} bytes > 100KB)")
                self.total_errors += 1
                return "failed", "file too large"
        except Exception as e:
            if self.logger:
                self.logger.write({
                    'ev': 'file_stat_error',
                    'path': str(path),
                    'error': str(e)
                })
            self.total_errors += 1
            return "failed", f"stat error: {e}"
        
        # Process with patterns only if --no-als
        if self.no_als:
            return await self._process_patterns_only(path, idx, total, file_start_time, run_start_time)
        
        # Process with ALS and optionally patterns
        return await self._process_with_als(path, idx, total, file_start_time, run_start_time)
    
    async def _process_patterns_only(
        self,
        path: Path,
        idx: int,
        total: int,
        file_start_time: float,
        run_start_time: float
    ) -> Tuple[str, Optional[str]]:
        """Process file with patterns only (no ALS)."""
        try:
            original_content = path.read_text(encoding="utf-8", errors="ignore")
            formatted_content = original_content
            
            # Apply patterns if available
            pattern_result = None
            if self.pattern_formatter and self.pattern_formatter.enabled:
                try:
                    formatted_content, pattern_result = self.pattern_formatter.apply(
                        path, original_content
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.write({
                            'ev': 'pattern_error',
                            'path': str(path),
                            'error': str(e)
                        })
                    raise RuntimeError(f"Pattern error: {e}")
            
            # Check if content changed
            if formatted_content != original_content:
                self.pattern_files_changed += 1
                
                if self.write:
                    try:
                        atomic_write(path, formatted_content)
                    except Exception as e:
                        raise RuntimeError(f"Failed to write file: {e}")
                
                if self.diff:
                    print(unified_diff(str(path), original_content, formatted_content))
                
                status = "changed"
            else:
                status = "ok"
            
            # Record metrics and log
            self._record_file_metrics(
                path, file_start_time, False, 0, pattern_result, status, None
            )
            
            return status, None
            
        except Exception as e:
            self.total_errors += 1
            if self.logger:
                self.logger.write({
                    'ev': 'processing_error',
                    'path': str(path),
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            return "failed", str(e)
    
    async def _process_with_als(
        self,
        path: Path,
        idx: int,
        total: int,
        file_start_time: float,
        run_start_time: float
    ) -> Tuple[str, Optional[str]]:
        """Process file with ALS and optionally patterns."""
        edits = []
        status = "ok"
        note = None
        pattern_result = None
        
        try:
            # Get ALS edits
            edits = await self.format_file_with_als(path)
            
            if edits:
                self.als_changed += 1
                # Apply edits to get formatted content
                original_content = path.read_text(encoding="utf-8", errors="ignore")
                formatted_content = apply_text_edits(original_content, edits)
                
                # Apply patterns if enabled
                if self.pattern_formatter and self.pattern_formatter.enabled:
                    try:
                        formatted_content, pattern_result = self.pattern_formatter.apply(
                            path, formatted_content
                        )
                    except Exception as e:
                        if self.logger:
                            self.logger.write({
                                'ev': 'pattern_error',
                                'path': str(path),
                                'error': str(e)
                            })
                        note = f"pattern error: {e}"
                
                # Write changes if requested
                if self.write:
                    try:
                        atomic_write(path, formatted_content)
                    except Exception as e:
                        raise RuntimeError(f"Failed to write file: {e}")
                
                # Show diff if requested
                if self.diff:
                    print(unified_diff(str(path), original_content, formatted_content))
                
                status = "changed"
            else:
                # No ALS changes, but still check patterns
                if self.pattern_formatter and self.pattern_formatter.enabled:
                    original_content = path.read_text(encoding="utf-8", errors="ignore")
                    formatted_content, pattern_result = self.pattern_formatter.apply(
                        path, original_content
                    )
                    if formatted_content != original_content:
                        self.pattern_files_changed += 1
                        if self.write:
                            atomic_write(path, formatted_content)
                        if self.diff:
                            print(unified_diff(str(path), original_content, formatted_content))
                        status = "changed"
                        
        except asyncio.TimeoutError:
            self.consecutive_timeouts += 1
            self.als_failed += 1
            status = "failed"
            note = f"timeout after {self.format_timeout}s"
            if self.max_consecutive_timeouts > 0 and self.consecutive_timeouts >= self.max_consecutive_timeouts:
                raise RuntimeError("Too many consecutive timeouts")
        except Exception as e:
            self.als_failed += 1
            status = "failed"
            note = str(e)
        else:
            self.consecutive_timeouts = 0
        
        # Record metrics and log
        self._record_file_metrics(
            path, file_start_time, True, len(edits) if edits else 0, pattern_result, status, note
        )
        
        return status, note
    
    def _record_file_metrics(
        self,
        path: Path,
        file_start_time: float,
        als_used: bool,
        als_edits: int,
        pattern_result: Optional[FileApplyResult],
        status: str,
        note: Optional[str]
    ) -> None:
        """Record metrics and logs for a processed file."""
        file_duration = time.time() - file_start_time
        
        # Pattern logger
        if self.pattern_logger:
            self.pattern_logger.write({
                'ev': 'file',
                'path': str(path),
                'als_ok': status != "failed",
                'als_edits': als_edits,
                'patterns_applied': pattern_result.applied_names if pattern_result else [],
                'replacements': pattern_result.replacements_sum if pattern_result else 0
            })
        
        # Metrics
        if self.metrics:
            self.metrics.record_file_format(
                file_path=str(path),
                als_success=status != "failed" if als_used else None,
                als_edits=als_edits if als_used else None,
                patterns_applied=pattern_result.applied_names if pattern_result else [],
                duration=file_duration,
                error=note if status == "failed" else None
            )
        
        # Main logger
        if self.logger:
            self.logger.write({
                "path": str(path),
                "status": status,
                "note": note,
                "als_edits": als_edits if als_used else None,
                "patterns_applied": pattern_result.applied_names if pattern_result else [],
                "patterns_replacements": pattern_result.replacements_sum if pattern_result else 0
            })