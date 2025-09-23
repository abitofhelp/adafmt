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
from typing import Dict, List, Optional, Tuple, Any

from returns.result import Failure

from .als_client import ALSClient
from .edits import apply_text_edits, unified_diff
from .file_ops import read_text, stat
from .logging_jsonl import JsonlLogger
from .metrics import MetricsCollector
from .pattern_formatter import PatternFormatter, FileApplyResult
from .worker_pool import WorkerPool
from .worker_context import WorkItem
from .thread_safe_metrics import ThreadSafeMetrics
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
        max_consecutive_timeouts: int = 5,
        max_file_size: int = 102400,  # 100KB default
        num_workers: Optional[int] = None
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
            max_file_size: Maximum file size in bytes to process (default 100KB)
            num_workers: Number of parallel workers (None = default)
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
        self.max_file_size = max_file_size
        self.num_workers = num_workers
        
        # UI queue for worker completion messages
        self.ui_queue: Optional[asyncio.Queue] = None
        self.ui_consumer_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.als_changed = 0
        self.als_failed = 0
        self.pattern_files_changed = 0
        self.total_errors = 0
        self.consecutive_timeouts = 0
        
        # Worker pool for parallel processing
        self.worker_pool: Optional[WorkerPool] = None
        self.thread_safe_metrics: Optional[ThreadSafeMetrics] = None
        
        # Determine if parallel processing should be used
        self.use_parallel = (
            num_workers is not None and 
            num_workers > 0 and 
            pattern_formatter is not None and
            pattern_formatter.enabled
        )
        
    async def initialize_worker_pool(self) -> None:
        """Initialize the worker pool for parallel processing."""
        if not self.use_parallel:
            return
            
        # Create thread-safe metrics for workers
        self.thread_safe_metrics = ThreadSafeMetrics()
        
        # Create UI queue for worker completion messages
        self.ui_queue = asyncio.Queue()
        
        # Start UI consumer task
        self.ui_consumer_task = asyncio.create_task(self._ui_consumer())
        
        # Create worker pool
        self.worker_pool = WorkerPool(num_workers=self.num_workers)
        
        # Start the worker pool
        await self.worker_pool.start(
            metrics=self.thread_safe_metrics,
            pattern_formatter=self.pattern_formatter,
            write_enabled=self.write,
            logger=self.logger,
            pattern_logger=self.pattern_logger,
            ui_queue=self.ui_queue
        )
        
        if self.ui:
            self.ui.log_line(f"[parallel] Started {self.worker_pool.num_workers} workers for post-ALS processing")
        else:
            print(f"[parallel] Started {self.worker_pool.num_workers} workers for post-ALS processing")
    
    async def shutdown_worker_pool(self) -> None:
        """Shutdown the worker pool and sync metrics."""
        if not self.worker_pool:
            return
            
        # Wait for all tasks to complete
        await self.worker_pool.wait_for_completion()
        
        # Shutdown workers
        await self.worker_pool.shutdown()
        
        # Signal UI consumer to stop and wait for it
        if self.ui_queue and self.ui_consumer_task:
            await self.ui_queue.put(None)  # Sentinel value
            await self.ui_consumer_task
        
        # Sync worker metrics with main metrics
        if self.thread_safe_metrics:
            snapshot = await self.thread_safe_metrics.get_snapshot()
            self.pattern_files_changed += snapshot['changed']
            self.total_errors += snapshot['errors']
            
        
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
            
        # Get debug logger from ALS client if available
        debug_logger = self.client.debug_logger if self.client and hasattr(self.client, 'debug_logger') else None
        
        # Open the file in ALS
        content_result = read_text(path, encoding="utf-8", errors="ignore")
        if isinstance(content_result, Failure):
            error = content_result.failure()
            if error.not_found:
                raise FileNotFoundError(error.message)
            elif error.permission_error:
                raise PermissionError(error.message)
            else:
                raise IOError(error.message)
        content = content_result.unwrap()
        
        # Log file start
        if debug_logger:
            debug_logger.write({
                'ev': 'als_file_start',
                'path': str(path),
                'size': len(content),  # type: ignore[arg-type]
                'lines': content.count('\n') + 1  # type: ignore[attr-defined]
            })
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
            # Log formatting request
            if debug_logger:
                debug_logger.write({
                    'ev': 'als_format_request',
                    'path': str(path),
                    'method': 'textDocument/formatting',
                    'uri': path.as_uri(),
                    'tab_size': 3,
                    'insert_spaces': True
                })
            
            result = await self.client.request_with_timeout(
                {
                    "method": "textDocument/formatting",
                    "params": {
                        "textDocument": {"uri": path.as_uri()},
                        "options": {"tabSize": 3, "insertSpaces": True}
                    }
                },
                timeout=self.format_timeout
            )
            
            if isinstance(result, Failure):
                error = result.failure()
                if error.timeout:
                    if debug_logger:
                        debug_logger.write({
                            'ev': 'als_format_timeout',
                            'path': str(path),
                            'timeout_seconds': self.format_timeout
                        })
                    raise asyncio.TimeoutError(error.message)
                else:
                    # Handle other ALS errors
                    raise RuntimeError(error.message)
            
            res = result.unwrap()
            
            # Log formatting response
            if debug_logger:
                debug_logger.write({
                    'ev': 'als_format_response',
                    'path': str(path),
                    'has_edits': res is not None and len(res) > 0,
                    'edit_count': len(res) if res else 0
                })
            
            # If we have edits, apply them to get the formatted content for debug log
            if debug_logger:
                if res:
                    formatted_content = apply_text_edits(content, res)  # type: ignore[arg-type]
                    debug_logger.write({
                        'ev': 'als_file_complete',
                        'path': str(path),
                        'changed': True,
                        'original_size': len(content),  # type: ignore[arg-type]
                        'formatted_size': len(formatted_content)
                    })
                else:
                    debug_logger.write({
                        'ev': 'als_file_complete',
                        'path': str(path),
                        'changed': False
                    })
                
        except asyncio.TimeoutError:
            res = None
            if debug_logger:
                debug_logger.write({
                    'ev': 'als_format_timeout',
                    'path': str(path),
                    'timeout_seconds': self.format_timeout
                })
            raise
        finally:
            # Always close the file
            with contextlib.suppress(Exception):
                await self.client._notify("textDocument/didClose", {"textDocument": {"uri": path.as_uri()}})
        
        # Validate response
        if res is not None and not isinstance(res, list):
            raise TypeError(f"ALS returned unexpected type for {path}: {type(res).__name__} instead of list")
        return res  # type: ignore[return-value]
    
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
        stat_result = stat(path)
        if isinstance(stat_result, Failure):
            error = stat_result.failure()
            if error.not_found:
                error_msg = f"File not found: {path}"
                if self.logger:
                    self.logger.write({
                        'ev': 'file_not_found',
                        'path': str(path),
                        'error': error_msg
                    })
                self.total_errors += 1
                return "failed", error_msg
            else:
                if self.logger:
                    self.logger.write({
                        'ev': 'file_stat_error',
                        'path': str(path),
                        'error': error.message
                    })
                self.total_errors += 1
                return "failed", f"stat error: {error.message}"
        
        file_stat = stat_result.unwrap()  # type: ignore[assignment]
        file_size = file_stat.st_size  # type: ignore[attr-defined]
        if file_size > self.max_file_size:
            if self.logger:
                self.logger.write({
                    'ev': 'file_skipped_too_large',
                    'path': str(path),
                    'size_bytes': file_size,
                    'max_bytes': self.max_file_size
                })
            if self.ui:
                self.ui.log_line(f"[formatter] Skipping {path} - file too large ({file_size:,} bytes > 100KB)")
            else:
                print(f"[formatter] Skipping {path} - file too large ({file_size:,} bytes > 100KB)")
            self.total_errors += 1
            return "failed", "file too large"
        
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
            content_result = read_text(path, encoding="utf-8", errors="ignore")
            if isinstance(content_result, Failure):
                error = content_result.failure()
                if error.not_found:
                    raise FileNotFoundError(error.message)
                elif error.permission_error:
                    raise PermissionError(error.message)
                else:
                    raise IOError(error.message)
            original_content = content_result.unwrap()  # type: ignore[assignment]
            formatted_content = original_content  # type: ignore[assignment]
            
            # Apply patterns if available
            pattern_result = None
            if self.pattern_formatter and self.pattern_formatter.enabled:
                try:
                    formatted_content, pattern_result = self.pattern_formatter.apply(
                        path, original_content  # type: ignore[arg-type]
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
                        atomic_write(str(path), formatted_content)  # type: ignore[arg-type]
                    except Exception as e:
                        raise RuntimeError(f"Failed to write file: {e}")
                
                if self.diff:
                    print(unified_diff(str(path), original_content, formatted_content))  # type: ignore[arg-type]
                
                status = "edited"
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
                content_result = read_text(path, encoding="utf-8", errors="ignore")
                if isinstance(content_result, Failure):
                    error = content_result.failure()
                    if error.not_found:
                        raise FileNotFoundError(error.message)
                    elif error.permission_error:
                        raise PermissionError(error.message)
                    else:
                        raise IOError(error.message)
                original_content = content_result.unwrap()
                formatted_content = apply_text_edits(original_content, edits)
                
                # Use worker pool if available, otherwise process inline
                if self.use_parallel and self.worker_pool:
                    # Queue for parallel processing
                    work_item = WorkItem(
                        path=path,
                        content=formatted_content,
                        index=idx,
                        total=total,
                        queue_time=time.time()
                    )
                    await self.worker_pool.submit(work_item)
                    # Worker will handle patterns, writing, and logging
                    status = "formatted"  # Done formatting, queued for save
                else:
                    # Process inline (original behavior)
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
                    
                    status = "edited"
            else:
                # No ALS changes, but still check patterns
                if self.pattern_formatter and self.pattern_formatter.enabled:
                    content_result = read_text(path, encoding="utf-8", errors="ignore")
                    if isinstance(content_result, Failure):
                        error = content_result.failure()
                        if error.not_found:
                            raise FileNotFoundError(error.message)
                        elif error.permission_error:
                            raise PermissionError(error.message)
                        else:
                            raise IOError(error.message)
                    original_content = content_result.unwrap()
                    
                    # Use worker pool if available
                    if self.use_parallel and self.worker_pool:
                        # Queue for parallel processing
                        work_item = WorkItem(
                            path=path,
                            content=original_content,
                            index=idx,
                            total=total,
                            queue_time=time.time()
                        )
                        await self.worker_pool.submit(work_item)
                        status = "formatted"  # Done formatting, queued for save
                    else:
                        # Process inline
                        formatted_content, pattern_result = self.pattern_formatter.apply(
                            path, original_content
                        )
                        if formatted_content != original_content:
                            self.pattern_files_changed += 1
                            if self.write:
                                atomic_write(path, formatted_content)
                            if self.diff:
                                print(unified_diff(str(path), original_content, formatted_content))
                            status = "edited"
                        
        except asyncio.TimeoutError:
            self.consecutive_timeouts += 1
            self.als_failed += 1
            status = "failed"
            note = f"timeout after {self.format_timeout}s"
            if self.max_consecutive_timeouts > 0 and self.consecutive_timeouts >= self.max_consecutive_timeouts:
                raise RuntimeError(
                    f"Too many consecutive timeouts ({self.consecutive_timeouts}) while processing files. "
                    f"Consider increasing --timeout or checking if ALS is responding properly."
                )
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
    
    async def _ui_consumer(self) -> None:
        """Consume completion messages from workers and display them."""
        while True:
            try:
                message = await self.ui_queue.get()
                if message is None:  # Sentinel value to stop
                    break
                    
                if message.get('type') == 'completion':
                    # Build status line for worker completion
                    path = message['path']
                    index = message['index']
                    total = message['total']
                    status = message['status']
                    note = message.get('note')
                    worker_id = message.get('worker_id', 0)
                    
                    # Build the status line similar to queued but with completion status
                    prefix = f"[{index:>4}/{total}]"
                    
                    # Build status line using CLI formatter
                    from .cli import _build_status_line
                    line = _build_status_line(
                        index, total, path, status, note,
                        self.no_als, self.pattern_formatter
                    )
                    
                    # Add worker info
                    line += f" | Worker: {worker_id}"
                    
                    # Display the line
                    if self.ui:
                        self.ui.log_line(line)
                    else:
                        # Use CLI's colored print function
                        from .cli import _print_colored_line
                        _print_colored_line(line)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.write({
                        'ev': 'ui_consumer_error',
                        'error': str(e)
                    })