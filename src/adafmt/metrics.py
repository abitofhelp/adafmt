# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Performance metrics collection for adafmt.

This module provides cumulative metrics tracking across multiple runs,
storing data in a JSONL file with proper file locking for concurrent access.

Metrics tracked:
    - Per-file formatting duration
    - ALS startup time
    - Pattern processing time
    - Overall run statistics
"""

from __future__ import annotations

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager


class MetricsCollector:
    """Collects and persists performance metrics.
    
    The metrics are stored in a cumulative JSONL file where each line
    represents a metric event. File locking ensures safe concurrent access.
    """
    
    def __init__(self, metrics_path: Optional[str] = None) -> None:
        """Initialize the metrics collector.
        
        Args:
            metrics_path: Path to metrics file. If None, uses ~/.adafmt/metrics.jsonl
        """
        if metrics_path:
            self.path = Path(metrics_path)
        else:
            # Default to ~/.adafmt/metrics.jsonl
            self.path = Path.home() / ".adafmt" / "metrics.jsonl"
        
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Timing tracking
        self._timers: Dict[str, float] = {}
        self._run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
    
    @contextmanager
    def _file_lock(self):
        """Context manager for file locking during append operations."""
        # Open in append mode
        with open(self.path, 'a', encoding='utf-8') as f:
            if sys.platform != 'win32':
                # Unix: Use fcntl for file locking
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    yield f
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                # Windows: File locking is implicit with exclusive access
                # Just yield the file handle
                yield f
    
    def _write_metric(self, event: Dict[str, Any]) -> None:
        """Write a metric event to the file with locking.
        
        Args:
            event: Metric event data to write
        """
        # Add common fields
        event['run_id'] = self._run_id
        event['ts'] = datetime.now().isoformat()
        
        # Write with file locking
        with self._file_lock() as f:
            json.dump(event, f, ensure_ascii=False, separators=(',', ':'))
            f.write('\n')
            f.flush()  # Ensure data is written
    
    def start_timer(self, name: str) -> None:
        """Start a named timer.
        
        Args:
            name: Timer name (e.g., 'als_startup', 'file_format')
        """
        self._timers[name] = time.time()
    
    def end_timer(self, name: str, **kwargs) -> float:
        """End a named timer and record the duration.
        
        Args:
            name: Timer name
            **kwargs: Additional fields to include in the metric
            
        Returns:
            Duration in seconds
        """
        if name not in self._timers:
            return 0.0
        
        duration = time.time() - self._timers[name]
        del self._timers[name]
        
        # Write timing metric
        event = {
            'ev': 'timing',
            'name': name,
            'duration_ms': round(duration * 1000, 2),
            **kwargs
        }
        self._write_metric(event)
        
        return duration
    
    def record_file_format(self, file_path: str, als_success: bool, 
                          als_edits: int, patterns_applied: List[str],
                          duration: float, error: Optional[str] = None) -> None:
        """Record metrics for a single file format operation.
        
        Args:
            file_path: Path to the file
            als_success: Whether ALS formatting succeeded
            als_edits: Number of edits from ALS
            patterns_applied: List of pattern names applied
            duration: Total time to format file
            error: Error message if failed
        """
        event = {
            'ev': 'file_format',
            'path': file_path,
            'als_success': als_success,
            'als_edits': als_edits,
            'patterns_applied': patterns_applied,
            'duration_ms': round(duration * 1000, 2),
        }
        if error:
            event['error'] = error
        
        self._write_metric(event)
    
    def record_run_summary(self, total_files: int, als_succeeded: int,
                          als_failed: int, patterns_changed: int,
                          total_duration: float) -> None:
        """Record summary metrics for entire run.
        
        Args:
            total_files: Total number of files processed
            als_succeeded: Files where ALS succeeded
            als_failed: Files where ALS failed
            patterns_changed: Files changed by patterns
            total_duration: Total run time in seconds
        """
        event = {
            'ev': 'run_summary',
            'total_files': total_files,
            'als_succeeded': als_succeeded,
            'als_failed': als_failed,
            'patterns_changed': patterns_changed,
            'duration_ms': round(total_duration * 1000, 2),
            'avg_file_ms': round(total_duration * 1000 / total_files, 2) if total_files > 0 else 0
        }
        self._write_metric(event)
    
    def record_als_startup(self, duration: float, success: bool,
                          project_path: str) -> None:
        """Record ALS startup metrics.
        
        Args:
            duration: Startup time in seconds
            success: Whether startup succeeded
            project_path: Path to project file
        """
        event = {
            'ev': 'als_startup',
            'duration_ms': round(duration * 1000, 2),
            'success': success,
            'project_path': project_path
        }
        self._write_metric(event)
    
    def record_pattern_timeout(self, pattern_name: str, file_path: str,
                              timeout_ms: int) -> None:
        """Record a pattern timeout event.
        
        Args:
            pattern_name: Name of the pattern that timed out
            file_path: File being processed
            timeout_ms: Timeout value in milliseconds
        """
        event = {
            'ev': 'pattern_timeout',
            'pattern_name': pattern_name,
            'path': file_path,
            'timeout_ms': timeout_ms
        }
        self._write_metric(event)