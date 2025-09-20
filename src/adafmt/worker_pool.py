# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Worker pool for parallel post-ALS processing."""

import asyncio
import os
import signal
import time
from typing import List, Optional, Callable, Any
from pathlib import Path

from .worker_context import WorkItem, WorkerContext
from .thread_safe_metrics import ThreadSafeMetrics
from .async_file_io import atomic_write_async
from .pattern_formatter import PatternFormatter
from .logging_jsonl import JsonlLogger
from .worker_pool_monitor import WorkerHealthMonitor, QueueMonitor
from .edits import unified_diff
from .retry_handler import RetryHandler


class WorkerPool:
    """Manages a pool of async workers for parallel file processing.
    
    This pool processes files after ALS formatting, applying patterns
    and writing results to disk in parallel.
    """
    
    def __init__(
        self,
        num_workers: Optional[int] = None,
        queue_size: int = 10  # Reduced from 100 to prevent memory bloat
    ):
        """Initialize worker pool.
        
        Args:
            num_workers: Number of worker tasks (default: 1)
            queue_size: Maximum items in queue (default: 10)
        """
        if num_workers is None:
            # Default to 1 worker based on benchmark results
            num_workers = 1
        
        self.num_workers = num_workers
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.workers: List[asyncio.Task] = []
        self.context: Optional[WorkerContext] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._health_monitor: Optional[WorkerHealthMonitor] = None
        self._queue_monitor: Optional[QueueMonitor] = None
        self._pending_tasks = 0
        self._all_tasks_done = asyncio.Event()
    
    async def start(
        self,
        metrics: ThreadSafeMetrics,
        pattern_formatter: Optional[PatternFormatter],
        write_enabled: bool,
        diff_enabled: bool = False,
        logger: Optional[JsonlLogger] = None,
        pattern_logger: Optional[JsonlLogger] = None,
        ui_queue: Optional[asyncio.Queue] = None
    ) -> None:
        """Start the worker pool.
        
        Args:
            metrics: Thread-safe metrics collector
            pattern_formatter: Optional pattern formatter
            write_enabled: Whether to write files to disk
            diff_enabled: Whether to show diffs
            logger: Optional logger for events
            pattern_logger: Optional logger for pattern results
            ui_queue: Optional queue for UI updates
        """
        if self._running:
            raise RuntimeError("Worker pool already running")
        
        # Create UI queue if not provided
        if ui_queue is None:
            ui_queue = asyncio.Queue()
        
        # Create worker context
        self.context = WorkerContext(
            metrics=metrics,
            pattern_formatter=pattern_formatter,
            logger=logger,
            pattern_logger=pattern_logger,
            write_enabled=write_enabled,
            diff_enabled=diff_enabled,
            ui_queue=ui_queue,
            shutdown_event=self._shutdown_event
        )
        
        # Start workers
        self._running = True
        self._all_tasks_done.set()  # Initially no tasks
        worker_dict = {}
        for i in range(self.num_workers):
            worker_id = i + 1
            worker = asyncio.create_task(
                self._worker(worker_id),
                name=f"worker-{worker_id}"
            )
            self.workers.append(worker)
            worker_dict[worker_id] = worker
        
        # Initialize health monitoring
        self._health_monitor = WorkerHealthMonitor(
            context=self.context,
            metrics=metrics,
            health_check_interval=5.0,
            worker_timeout=30.0
        )
        await self._health_monitor.start_monitoring(worker_dict)
        
        # Initialize queue monitoring
        self._queue_monitor = QueueMonitor(
            queue=self.queue,
            metrics=metrics,
            blockage_threshold=60.0
        )
        
        # Log startup
        if logger:
            logger.write({
                'ev': 'worker_pool_started',
                'num_workers': self.num_workers,
                'queue_size': self.queue.maxsize,
                'health_monitoring': True
            })
    
    async def submit(self, item: WorkItem) -> None:
        """Submit a work item to the pool.
        
        Args:
            item: Work item to process
            
        Raises:
            RuntimeError: If pool not started
        """
        if not self._running:
            raise RuntimeError("Worker pool not started")
        
        # Add queue time for metrics
        item.queue_time = time.time()
        self._pending_tasks += 1
        self._all_tasks_done.clear()
        await self.queue.put(item)
    
    async def wait_for_completion(self) -> None:
        """Wait for all submitted tasks to complete."""
        await self._all_tasks_done.wait()
    
    async def shutdown(self, timeout: float = 30.0) -> None:
        """Shutdown the worker pool gracefully.
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        if not self._running:
            return
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop health monitoring
        if self._health_monitor:
            await self._health_monitor.stop_monitoring()
        
        # Add sentinel values to wake up workers
        for _ in range(self.num_workers):
            try:
                await asyncio.wait_for(
                    self.queue.put(None),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                pass
        
        # Wait for workers to complete
        if self.workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.workers, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Cancel remaining workers
                for worker in self.workers:
                    if not worker.done():
                        worker.cancel()
                
                # Wait a bit for cancellation
                await asyncio.gather(*self.workers, return_exceptions=True)
        
        self._running = False
        self.workers.clear()
        
        # Log shutdown
        if self.context and self.context.logger:
            self.context.logger.write({
                'ev': 'worker_pool_shutdown',
                'timeout_used': timeout
            })
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes items from the queue.
        
        Args:
            worker_id: Unique identifier for this worker
        """
        if not self.context:
            return
        
        metrics = self.context.metrics
        
        try:
            while not self.context.should_shutdown():
                try:
                    # Get item with timeout to check shutdown periodically
                    item = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                    
                    if item is None:  # Sentinel value
                        break
                    
                    # Notify queue monitor of dequeue
                    if self._queue_monitor:
                        self._queue_monitor.record_dequeue()
                    
                    # Process the item
                    try:
                        await self._process_item(item, worker_id)
                    finally:
                        self._pending_tasks -= 1
                        if self._pending_tasks == 0:
                            self._all_tasks_done.set()
                    
                except asyncio.TimeoutError:
                    # Check shutdown and continue
                    continue
                except asyncio.CancelledError:
                    # Clean shutdown
                    break
                except Exception as e:
                    # Log unexpected error but continue
                    await self.context.report_error(
                        Path("worker"),
                        e,
                        worker_id
                    )
        
        finally:
            # Update worker metrics for shutdown
            await metrics.update_worker_metrics(worker_id)
    
    async def _process_item(
        self,
        item: WorkItem,
        worker_id: int
    ) -> None:
        """Process a single work item.
        
        Args:
            item: Work item to process
            worker_id: Worker processing this item
        """
        if not self.context:
            return
        
        start_time = time.time()
        queue_wait = start_time - item.queue_time
        
        try:
            # Track queue wait time
            await self.context.metrics.add_timing('queue_wait', queue_wait)
            
            # Apply patterns if formatter available
            formatted_content = item.content
            patterns_applied = 0
            total_replacements = 0
            
            if self.context.pattern_formatter and self.context.pattern_formatter.enabled:
                pattern_start = time.time()
                
                formatted_content, result = self.context.pattern_formatter.apply(
                    item.path,
                    item.content
                )
                
                if formatted_content != item.content:
                    patterns_applied = len(result.applied_names)
                    total_replacements = result.replacements_sum
                
                pattern_time = time.time() - pattern_start
                await self.context.metrics.add_timing('pattern', pattern_time)
                
                # Log pattern results
                if patterns_applied > 0:
                    await self.context.log_pattern_result(
                        item.path,
                        patterns_applied,
                        total_replacements,
                        pattern_time,
                        worker_id
                    )
            
            # Check if content changed
            changed = formatted_content != item.content
            
            # Write file if enabled and changed
            write_time = 0.0
            if self.context.write_enabled and changed:
                write_start = time.time()
                
                # Retry handler callback
                def on_retry(attempt: int, error: Exception) -> None:
                    if self.context.logger:
                        self.context.logger.write({
                            'ev': 'file_write_retry',
                            'path': str(item.path),
                            'attempt': attempt,
                            'error': str(error),
                            'worker_id': worker_id
                        })
                
                # Write with retry logic
                _, attempts = await RetryHandler.retry_async(
                    atomic_write_async,
                    item.path,
                    formatted_content,
                    mode=0o644,
                    max_attempts=3,
                    on_retry=on_retry
                )
                
                write_time = time.time() - write_start
                await self.context.metrics.add_timing('io', write_time)
                
                # Log if retries were needed
                if attempts > 1 and self.context.logger:
                    self.context.logger.write({
                        'ev': 'file_write_succeeded_with_retries',
                        'path': str(item.path),
                        'attempts': attempts,
                        'worker_id': worker_id
                    })
            
            # Show diff if enabled
            if self.context.diff_enabled and changed:
                diff = unified_diff(
                    item.content,
                    formatted_content,
                    str(item.path)
                )
                # Could send diff to UI queue if needed
            
            # Update metrics
            if changed:
                await self.context.metrics.increment_changed()
                status = "amended"
            else:
                await self.context.metrics.increment_unchanged()
                status = "unchanged"
            
            # Report completion
            await self.context.report_completion(
                path=item.path,
                index=item.index,
                total=item.total,
                status=status,
                note=f"Patterns: {patterns_applied}" if patterns_applied > 0 else None,
                worker_id=worker_id
            )
            
            # Update worker metrics
            total_time = time.time() - start_time
            await self.context.metrics.update_worker_metrics(
                worker_id=worker_id,
                files_processed=1,
                time_delta=total_time,
                pattern_time=pattern_time if self.context.pattern_formatter else 0.0,
                io_time=write_time
            )
            await self.context.metrics.add_timing('total', total_time)
            
        except Exception as e:
            # Report error
            await self.context.report_error(item.path, e, worker_id)
            await self.context.metrics.increment_errors()
            await self.context.metrics.update_worker_metrics(
                worker_id=worker_id,
                errors=1
            )
            
            # Report failed completion
            await self.context.report_completion(
                path=item.path,
                index=item.index,
                total=item.total,
                status="failed",
                note=str(e),
                worker_id=worker_id
            )


class SignalHandler:
    """Handles OS signals for graceful shutdown."""
    
    def __init__(self, worker_pool: WorkerPool):
        """Initialize signal handler.
        
        Args:
            worker_pool: Worker pool to shutdown on signal
        """
        self.worker_pool = worker_pool
        self._original_handlers = {}
        
    def __enter__(self):
        """Install signal handlers."""
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM,
            self._handle_signal
        )
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT,
            self._handle_signal
        )
        
        # SIGHUP only exists on Unix
        if hasattr(signal, 'SIGHUP'):
            self._original_handlers[signal.SIGHUP] = signal.signal(
                signal.SIGHUP,
                self._handle_signal
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
    
    def _handle_signal(self, signum, frame):
        """Handle signal by triggering shutdown."""
        if self.worker_pool.context:
            self.worker_pool.context.shutdown_event.set()
        
        # Log signal
        if self.worker_pool.context and self.worker_pool.context.logger:
            self.worker_pool.context.logger.write({
                'ev': 'signal_received',
                'signal': signal.Signals(signum).name
            })