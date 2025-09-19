# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Thread-safe metrics collection for parallel workers."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class WorkerMetrics:
    """Metrics for a single worker."""
    worker_id: int
    files_processed: int = 0
    errors: int = 0
    total_time: float = 0.0
    pattern_time: float = 0.0
    io_time: float = 0.0
    last_activity: float = field(default_factory=time.time)


class ThreadSafeMetrics:
    """Thread-safe metrics collector for parallel processing.
    
    All methods are async and use asyncio.Lock for synchronization.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._lock = asyncio.Lock()
        self._changed = 0
        self._unchanged = 0
        self._errors = 0
        self._skipped = 0
        self._total_time = 0.0
        self._pattern_time = 0.0
        self._io_time = 0.0
        self._queue_wait_time = 0.0
        self._worker_metrics: Dict[int, WorkerMetrics] = {}
        self._error_messages: List[str] = []
        self._start_time = time.time()
    
    async def increment_changed(self) -> None:
        """Increment changed file count."""
        async with self._lock:
            self._changed += 1
    
    async def increment_unchanged(self) -> None:
        """Increment unchanged file count."""
        async with self._lock:
            self._unchanged += 1
    
    async def increment_errors(self) -> None:
        """Increment error count."""
        async with self._lock:
            self._errors += 1
    
    async def increment_skipped(self) -> None:
        """Increment skipped file count."""
        async with self._lock:
            self._skipped += 1
    
    async def add_timing(self, category: str, seconds: float) -> None:
        """Add timing for a category.
        
        Args:
            category: One of 'total', 'pattern', 'io', 'queue_wait'
            seconds: Time in seconds
        """
        async with self._lock:
            if category == 'total':
                self._total_time += seconds
            elif category == 'pattern':
                self._pattern_time += seconds
            elif category == 'io':
                self._io_time += seconds
            elif category == 'queue_wait':
                self._queue_wait_time += seconds
    
    async def add_error_message(self, message: str) -> None:
        """Add an error message to the list.
        
        Args:
            message: Error message to record
        """
        async with self._lock:
            # Limit error messages to prevent unbounded growth
            if len(self._error_messages) < 100:
                self._error_messages.append(message)
    
    async def update_worker_metrics(
        self,
        worker_id: int,
        files_processed: int = 0,
        errors: int = 0,
        time_delta: float = 0.0,
        pattern_time: float = 0.0,
        io_time: float = 0.0
    ) -> None:
        """Update metrics for a specific worker.
        
        Args:
            worker_id: Worker identifier
            files_processed: Number of files to add
            errors: Number of errors to add
            time_delta: Time to add to total
            pattern_time: Pattern processing time to add
            io_time: I/O time to add
        """
        async with self._lock:
            if worker_id not in self._worker_metrics:
                self._worker_metrics[worker_id] = WorkerMetrics(worker_id)
            
            metrics = self._worker_metrics[worker_id]
            metrics.files_processed += files_processed
            metrics.errors += errors
            metrics.total_time += time_delta
            metrics.pattern_time += pattern_time
            metrics.io_time += io_time
            metrics.last_activity = time.time()
    
    async def get_snapshot(self) -> Dict:
        """Get a read-only snapshot of all metrics.
        
        Returns:
            Dictionary with all current metrics
        """
        async with self._lock:
            return {
                'changed': self._changed,
                'unchanged': self._unchanged,
                'errors': self._errors,
                'skipped': self._skipped,
                'total_time': self._total_time,
                'pattern_time': self._pattern_time,
                'io_time': self._io_time,
                'queue_wait_time': self._queue_wait_time,
                'elapsed_time': time.time() - self._start_time,
                'worker_metrics': {
                    wid: {
                        'files_processed': m.files_processed,
                        'errors': m.errors,
                        'total_time': m.total_time,
                        'pattern_time': m.pattern_time,
                        'io_time': m.io_time,
                        'idle_time': time.time() - m.last_activity
                    }
                    for wid, m in self._worker_metrics.items()
                },
                'error_messages': self._error_messages[:],  # Copy
            }
    
    async def get_changed(self) -> int:
        """Get changed file count."""
        async with self._lock:
            return self._changed
    
    async def get_errors(self) -> int:
        """Get error count."""
        async with self._lock:
            return self._errors
    
    async def get_total_processed(self) -> int:
        """Get total processed file count."""
        async with self._lock:
            return self._changed + self._unchanged + self._errors + self._skipped
    
    async def get_worker_health(self) -> Dict[int, bool]:
        """Get worker health status.
        
        Returns:
            Dict mapping worker_id to health status (True if healthy)
        """
        async with self._lock:
            current_time = time.time()
            return {
                wid: (current_time - m.last_activity) < 30.0  # 30s timeout
                for wid, m in self._worker_metrics.items()
            }