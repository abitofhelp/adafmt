# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for worker pool implementation."""

import asyncio
import os
import signal
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

from adafmt.worker_pool import WorkerPool, SignalHandler
from adafmt.worker_context import WorkItem
from adafmt.thread_safe_metrics import ThreadSafeMetrics
from adafmt.pattern_formatter import PatternFormatter


class TestWorkerPool:
    """Test WorkerPool class."""
    
    def test_initialization_default_workers(self):
        """Test worker pool initializes with default worker count."""
        pool = WorkerPool()
        assert pool.num_workers == 1  # Default is now 1 based on benchmarks
        assert pool.queue.maxsize == 10
        assert not pool._running
    
    def test_initialization_custom_workers(self):
        """Test worker pool with custom worker count."""
        pool = WorkerPool(num_workers=3, queue_size=5)
        assert pool.num_workers == 3
        assert pool.queue.maxsize == 5
    
    def test_initialization_explicit_none(self):
        """Test worker pool with None defaults to 1."""
        pool = WorkerPool(num_workers=None)
        assert pool.num_workers == 1  # Default is 1 when None is passed
    
    @pytest.mark.asyncio
    async def test_start_creates_workers(self):
        """Test starting pool creates worker tasks."""
        pool = WorkerPool(num_workers=3)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        assert pool._running
        assert len(pool.workers) == 3
        assert all(isinstance(w, asyncio.Task) for w in pool.workers)
        assert pool.context is not None
        assert pool.context.metrics == metrics
        
        # Cleanup
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_start_twice_raises_error(self):
        """Test starting already running pool raises error."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        with pytest.raises(RuntimeError, match="already running"):
            await pool.start(metrics, None, False)
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_submit_item(self):
        """Test submitting work item to pool."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        item = WorkItem(
            path=Path("test.adb"),
            content="test content",
            index=1,
            total=1,
            queue_time=0.0
        )
        
        await pool.submit(item)
        
        # Check item in queue
        assert pool.queue.qsize() == 1
        queued_item = await pool.queue.get()
        assert queued_item == item
        assert queued_item.queue_time > 0  # Time was set
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_submit_without_start_raises(self):
        """Test submitting to non-started pool raises error."""
        pool = WorkerPool()
        item = WorkItem(Path("test.adb"), "content", 1, 1, 0.0)
        
        with pytest.raises(RuntimeError, match="not started"):
            await pool.submit(item)
    
    @pytest.mark.asyncio
    async def test_shutdown_stops_workers(self):
        """Test shutdown stops all workers."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        assert pool._running
        
        await pool.shutdown()
        
        assert not pool._running
        assert len(pool.workers) == 0
        assert pool.context.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout(self):
        """Test shutdown with timeout cancels workers."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        # Mock worker that never completes
        async def stuck_worker(worker_id):
            await asyncio.sleep(100)
        
        pool._worker = stuck_worker
        await pool.start(metrics, None, False)
        
        # Shutdown with short timeout
        await pool.shutdown(timeout=0.1)
        
        assert not pool._running
        assert all(w.cancelled() for w in pool.workers if w.done())
    
    @pytest.mark.asyncio
    async def test_process_item_with_patterns(self, tmp_path):
        """Test processing item with pattern formatter."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        # Mock pattern formatter
        formatter = Mock()  # Remove spec to allow all attributes
        formatter.enabled = True
        formatter.apply = Mock(return_value=(
            "formatted content",  # The formatted text
            Mock(
                applied_names=['rule1', 'rule2'],
                replacements_sum=2
            )
        ))
        
        # Create test file
        test_file = tmp_path / "test.adb"
        test_file.write_text("original content")
        
        await pool.start(
            metrics=metrics,
            pattern_formatter=formatter,
            write_enabled=True,
            logger=Mock()
        )
        
        item = WorkItem(
            path=test_file,
            content="original content",
            index=1,
            total=1,
            queue_time=time.time()
        )
        
        # Process directly
        await pool._process_item(item, worker_id=1)
        
        # Verify pattern formatter called
        formatter.apply.assert_called_once_with(
            test_file,
            "original content"
        )
        
        # Verify file written
        assert test_file.read_text() == "formatted content"
        
        # Verify metrics
        assert await metrics.get_changed() == 1
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_item_no_change(self, tmp_path):
        """Test processing item with no changes."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        test_file = tmp_path / "test.adb"
        test_file.write_text("original content")
        
        await pool.start(
            metrics=metrics,
            pattern_formatter=None,  # No patterns
            write_enabled=True
        )
        
        item = WorkItem(
            path=test_file,
            content="original content",
            index=1,
            total=1,
            queue_time=time.time()
        )
        
        await pool._process_item(item, worker_id=1)
        
        # File should not be rewritten
        assert test_file.read_text() == "original content"
        snapshot = await metrics.get_snapshot()
        assert snapshot['unchanged'] == 1
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_item_error_handling(self):
        """Test error handling during item processing."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        # Mock pattern formatter that raises
        formatter = Mock()
        formatter.enabled = True
        formatter.apply = Mock(side_effect=ValueError("Pattern error"))
        
        await pool.start(
            metrics=metrics,
            pattern_formatter=formatter,
            write_enabled=False
        )
        
        item = WorkItem(
            path=Path("test.adb"),
            content="content",
            index=1,
            total=1,
            queue_time=time.time()
        )
        
        # Process should handle error gracefully
        await pool._process_item(item, worker_id=1)
        
        assert await metrics.get_errors() == 1
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_worker_processes_queue(self):
        """Test worker processes items from queue."""
        pool = WorkerPool(num_workers=1)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        # Submit items
        items = []
        for i in range(3):
            item = WorkItem(
                path=Path(f"test{i}.adb"),
                content=f"content{i}",
                index=i+1,
                total=3,
                queue_time=time.time()
            )
            items.append(item)
            await pool.submit(item)
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # All items should be processed
        assert pool.queue.empty()
        assert await metrics.get_total_processed() == 3
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_queue_full_blocks(self):
        """Test submitting to full queue blocks."""
        pool = WorkerPool(num_workers=0, queue_size=2)  # No workers
        metrics = ThreadSafeMetrics()
        
        # Start with no workers to prevent processing
        pool._worker = AsyncMock()  # Mock to prevent actual workers
        await pool.start(metrics, None, False)
        pool.workers.clear()  # Remove any started workers
        
        # Fill queue
        item1 = WorkItem(Path("test1.adb"), "content", 1, 3, 0.0)
        item2 = WorkItem(Path("test2.adb"), "content", 2, 3, 0.0)
        item3 = WorkItem(Path("test3.adb"), "content", 3, 3, 0.0)
        
        await pool.submit(item1)
        await pool.submit(item2)
        
        # Third submit should block
        submit_task = asyncio.create_task(pool.submit(item3))
        await asyncio.sleep(0.05)
        
        assert not submit_task.done()  # Still blocked
        assert pool.queue.full()
        
        # Cancel to clean up
        submit_task.cancel()
        try:
            await submit_task
        except asyncio.CancelledError:
            pass
        
        await pool.shutdown()


class TestSignalHandler:
    """Test SignalHandler class."""
    
    def test_signal_handler_context(self):
        """Test signal handler as context manager."""
        pool = WorkerPool()
        
        # Get current handlers (may be pytest's handlers)
        current_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        current_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        # Restore them immediately
        signal.signal(signal.SIGTERM, current_sigterm)
        signal.signal(signal.SIGINT, current_sigint)
        
        try:
            with SignalHandler(pool) as handler:
                # Handlers should be replaced with our handler
                our_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
                signal.signal(signal.SIGTERM, our_sigterm)  # Restore
                
                # Our handler should be the SignalHandler's method
                assert our_sigterm == handler._handle_signal
            
            # Original handlers should be restored after context exit
            restored_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, restored_sigterm)
            
            # The restored handler should match what was there before
            assert restored_sigterm == current_sigterm
            
        finally:
            # Ensure original handlers are restored
            signal.signal(signal.SIGTERM, current_sigterm)
            signal.signal(signal.SIGINT, current_sigint)
    
    @pytest.mark.asyncio
    async def test_signal_triggers_shutdown(self):
        """Test signal triggers worker pool shutdown."""
        pool = WorkerPool()
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        with SignalHandler(pool) as handler:
            # Simulate signal
            handler._handle_signal(signal.SIGTERM, None)
            
            # Shutdown event should be set
            assert pool.context.shutdown_event.is_set()
        
        await pool.shutdown()
    
    def test_signal_handler_unix_signals(self):
        """Test handler includes SIGHUP on Unix."""
        pool = WorkerPool()
        
        with SignalHandler(pool) as handler:
            if hasattr(signal, 'SIGHUP'):
                assert signal.SIGHUP in handler._original_handlers
            else:
                # Windows doesn't have SIGHUP
                assert signal.SIGHUP not in handler._original_handlers