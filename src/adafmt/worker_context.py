# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Shared context for worker pool operations."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .thread_safe_metrics import ThreadSafeMetrics
from .pattern_formatter import PatternFormatter
from .logging_jsonl import JsonlLogger


@dataclass
class WorkItem:
    """Item queued for worker processing."""
    path: Path
    content: str
    index: int
    total: int
    queue_time: float  # Time when queued (for wait time tracking)


@dataclass
class WorkerContext:
    """Shared context for all workers in the pool.
    
    Provides thread-safe access to shared resources.
    """
    
    # Core components
    metrics: ThreadSafeMetrics
    pattern_formatter: Optional[PatternFormatter]
    logger: Optional[JsonlLogger]
    pattern_logger: Optional[JsonlLogger]
    
    # Configuration
    write_enabled: bool
    diff_enabled: bool
    
    # UI communication
    ui_queue: asyncio.Queue
    
    # Lifecycle management
    shutdown_event: Optional[asyncio.Event] = None
    
    # Default values
    buffer_size: int = 8192
    
    def __post_init__(self):
        """Initialize event if not provided."""
        if self.shutdown_event is None:
            self.shutdown_event = asyncio.Event()
    
    def should_shutdown(self) -> bool:
        """Check if workers should shutdown.
        
        Returns:
            True if shutdown requested
        """
        return self.shutdown_event is not None and self.shutdown_event.is_set()
    
    async def report_completion(
        self,
        path: Path,
        index: int,
        total: int,
        status: str,
        note: Optional[str] = None,
        worker_id: int = 0
    ) -> None:
        """Report file completion to UI.
        
        Args:
            path: File path
            index: File index (1-based)
            total: Total file count
            status: Status (changed, unchanged, failed)
            note: Optional note
            worker_id: Worker identifier
        """
        await self.ui_queue.put({
            'type': 'completion',
            'path': path,
            'index': index,
            'total': total,
            'status': status,
            'note': note,
            'worker_id': worker_id
        })
    
    async def report_error(
        self,
        path: Path,
        error: Exception,
        worker_id: int = 0
    ) -> None:
        """Report error to UI and metrics.
        
        Args:
            path: File path that caused error
            error: Exception that occurred
            worker_id: Worker identifier
        """
        error_msg = f"Worker {worker_id}: {path} - {str(error)}"
        await self.metrics.add_error_message(error_msg)
        
        if self.logger:
            self.logger.write({
                'ev': 'worker_error',
                'worker_id': worker_id,
                'path': str(path),
                'error': str(error),
                'error_type': type(error).__name__
            })
    
    async def log_pattern_result(
        self,
        path: Path,
        patterns_applied: int,
        replacements: int,
        time_taken: float,
        worker_id: int = 0
    ) -> None:
        """Log pattern application result.
        
        Args:
            path: File path
            patterns_applied: Number of patterns that made changes
            replacements: Total replacements made
            time_taken: Time in seconds
            worker_id: Worker identifier
        """
        if self.pattern_logger:
            self.pattern_logger.write({
                'ev': 'pattern_applied',
                'worker_id': worker_id,
                'path': str(path),
                'patterns_applied': patterns_applied,
                'replacements': replacements,
                'time_ms': int(time_taken * 1000)
            })