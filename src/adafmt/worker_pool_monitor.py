# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Worker pool health monitoring and recovery."""

import asyncio
import time
from typing import Optional, Dict, Any
import logging

from .worker_context import WorkerContext
from .thread_safe_metrics import ThreadSafeMetrics


class WorkerHealthMonitor:
    """Monitors worker pool health and handles recovery."""
    
    def __init__(
        self,
        context: WorkerContext,
        metrics: ThreadSafeMetrics,
        health_check_interval: float = 5.0,
        worker_timeout: float = 30.0,
        max_restart_attempts: int = 3
    ):
        """Initialize the health monitor.
        
        Args:
            context: Shared worker context
            metrics: Thread-safe metrics collector
            health_check_interval: Seconds between health checks
            worker_timeout: Seconds before considering worker unhealthy
            max_restart_attempts: Max attempts to restart unhealthy worker
        """
        self.context = context
        self.metrics = metrics
        self.health_check_interval = health_check_interval
        self.worker_timeout = worker_timeout
        self.max_restart_attempts = max_restart_attempts
        self._monitor_task: Optional[asyncio.Task] = None
        self._restart_counts: Dict[int, int] = {}
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self, workers: Dict[int, asyncio.Task]) -> None:
        """Start monitoring worker health.
        
        Args:
            workers: Dictionary of worker_id -> task
        """
        if self._monitor_task and not self._monitor_task.done():
            return
        
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(workers)
        )
    
    async def stop_monitoring(self) -> None:
        """Stop the health monitor."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, workers: Dict[int, asyncio.Task]) -> None:
        """Main monitoring loop.
        
        Args:
            workers: Dictionary of worker_id -> task
        """
        while not self.context.should_shutdown():
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check worker health
                health = await self.metrics.get_worker_health(
                    timeout_seconds=self.worker_timeout
                )
                
                # Check each worker
                for worker_id, is_healthy in health.items():
                    if not is_healthy and worker_id in workers:
                        await self._handle_unhealthy_worker(
                            worker_id, workers
                        )
                
                # Check for crashed workers
                for worker_id, task in list(workers.items()):
                    if task.done():
                        try:
                            # Get the exception if any
                            task.result()
                        except Exception as e:
                            self.logger.error(
                                f"Worker {worker_id} crashed: {e}"
                            )
                            await self._handle_crashed_worker(
                                worker_id, workers, e
                            )
            
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                await self.metrics.record_error(
                    worker_id=0,
                    error=f"Health monitor error: {e}"
                )
    
    async def _handle_unhealthy_worker(
        self,
        worker_id: int,
        workers: Dict[int, asyncio.Task]
    ) -> None:
        """Handle an unhealthy worker.
        
        Args:
            worker_id: ID of unhealthy worker
            workers: Dictionary of worker_id -> task
        """
        self.logger.warning(f"Worker {worker_id} is unhealthy")
        
        # Cancel the worker
        if worker_id in workers:
            workers[worker_id].cancel()
            
        # Record the issue
        await self.metrics.record_error(
            worker_id=worker_id,
            error=f"Worker timeout (>{self.worker_timeout}s)"
        )
    
    async def _handle_crashed_worker(
        self,
        worker_id: int,
        workers: Dict[int, asyncio.Task],
        error: Exception
    ) -> None:
        """Handle a crashed worker.
        
        Args:
            worker_id: ID of crashed worker
            workers: Dictionary of worker_id -> task
            error: The exception that caused the crash
        """
        restart_count = self._restart_counts.get(worker_id, 0)
        
        if restart_count >= self.max_restart_attempts:
            self.logger.error(
                f"Worker {worker_id} exceeded max restarts ({self.max_restart_attempts})"
            )
            # Remove from workers dict
            workers.pop(worker_id, None)
            return
        
        self.logger.info(
            f"Attempting to restart worker {worker_id} "
            f"(attempt {restart_count + 1}/{self.max_restart_attempts})"
        )
        
        # Increment restart count
        self._restart_counts[worker_id] = restart_count + 1
        
        # Note: Actual worker restart would be handled by the pool
        # This just tracks the attempts and removes failed workers


class QueueMonitor:
    """Monitors queue health and detects blockages."""
    
    def __init__(
        self,
        queue: asyncio.Queue,
        metrics: ThreadSafeMetrics,
        blockage_threshold: float = 60.0
    ):
        """Initialize queue monitor.
        
        Args:
            queue: The queue to monitor
            metrics: Thread-safe metrics
            blockage_threshold: Seconds before considering queue blocked
        """
        self.queue = queue
        self.metrics = metrics
        self.blockage_threshold = blockage_threshold
        self._last_dequeue_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    async def check_queue_health(self) -> bool:
        """Check if queue is healthy.
        
        Returns:
            True if healthy, False if blocked
        """
        if self.queue.empty():
            return True
        
        # Check how long since last dequeue
        time_since_dequeue = time.time() - self._last_dequeue_time
        
        if time_since_dequeue > self.blockage_threshold:
            self.logger.warning(
                f"Queue appears blocked: {self.queue.qsize()} items, "
                f"no dequeue for {time_since_dequeue:.1f}s"
            )
            return False
        
        return True
    
    def record_dequeue(self) -> None:
        """Record that a dequeue occurred."""
        self._last_dequeue_time = time.time()