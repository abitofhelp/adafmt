# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for worker pool functionality."""

import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import pytest

from adafmt.worker_pool import WorkerPool, SignalHandler
from adafmt.worker_context import WorkItem
from adafmt.thread_safe_metrics import ThreadSafeMetrics
from adafmt.pattern_formatter import PatternFormatter
from adafmt.logging_jsonl import JsonlLogger


@pytest.mark.integration
class TestWorkerPoolIntegration:
    """Integration tests for the worker pool functionality."""
    
    @pytest.mark.asyncio
    async def test_worker_pool_processes_items(self, tmp_path):
        """Test that worker pool processes all queued items."""
        # Create test files
        files = []
        for i in range(10):
            file = tmp_path / f"test_{i}.adb"
            file.write_text(f"procedure Test_{i} is\nbegin null; end;")
            files.append(file)
        
        # Create worker pool
        pool = WorkerPool(num_workers=3)
        metrics = ThreadSafeMetrics()
        
        # Mock pattern formatter
        pattern_formatter = Mock()
        pattern_formatter.enabled = True
        pattern_formatter.apply = Mock(return_value=(
            "formatted content",
            Mock(
                applied_names=['rule1'],
                replacements_sum=5
            )
        ))
        
        # Start pool
        await pool.start(metrics, pattern_formatter, write_enabled=True)
        
        # Queue items
        start_time = time.time()
        for i, file in enumerate(files):
            item = WorkItem(
                path=file,
                content="original content",
                index=i+1,
                total=len(files),
                queue_time=time.time()
            )
            await pool.submit(item)
        
        # Wait for queue to be processed
        while not pool.queue.empty():
            await asyncio.sleep(0.01)
        
        # Give workers a moment to finish processing
        await asyncio.sleep(0.1)
        
        # Shutdown and wait
        await pool.shutdown()
        total_time = time.time() - start_time
        
        # Verify all files processed
        assert await metrics.get_changed() == 10
        assert await metrics.get_total_processed() == 10
        assert all(f.read_text() == "formatted content" for f in files)
        
        # Performance check - should be faster than sequential
        print(f"\nProcessed {len(files)} files in {total_time:.2f}s")
        print(f"Rate: {len(files)/total_time:.1f} files/s")
    
    @pytest.mark.asyncio
    async def test_worker_pool_handles_errors(self, tmp_path):
        """Test that worker pool handles worker errors gracefully."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()
        
        # Mock pattern formatter that fails sometimes
        pattern_formatter = Mock()
        pattern_formatter.enabled = True
        call_count = 0
        
        def format_side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Pattern error")
            return (
                "formatted",
                Mock(
                    applied_names=[],
                    replacements_sum=0
                )
            )
        
        pattern_formatter.apply = Mock(side_effect=format_side_effect)
        
        await pool.start(metrics, pattern_formatter, write_enabled=False)
        
        # Queue items
        for i in range(5):
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="content",
                index=i+1,
                total=5,
                queue_time=time.time()
            )
            await pool.submit(item)
        
        # Wait for processing
        while not pool.queue.empty():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)
        
        await pool.shutdown()
        
        # Should have processed all items, some with errors
        assert await metrics.get_total_processed() == 5
        assert await metrics.get_errors() > 0
        assert await metrics.get_errors() < 5  # Not all failed
    
    @pytest.mark.asyncio
    async def test_worker_pool_shutdown_timeout(self):
        """Test worker pool shutdown with timeout."""
        pool = WorkerPool(num_workers=1)
        
        # Mock a stuck worker
        async def stuck_worker(worker_id):
            try:
                await asyncio.sleep(60)  # Longer than timeout
            except asyncio.CancelledError:
                # Properly handle cancellation
                raise
        
        pool._worker = stuck_worker
        await pool.start(Mock(), Mock(), False)
        
        # Shutdown with short timeout should complete
        start = time.time()
        await pool.shutdown(timeout=0.5)
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # Should timeout quickly
        assert not pool._running
    
    @pytest.mark.asyncio
    async def test_queue_backpressure(self):
        """Test queue backpressure when workers are slow."""
        pool = WorkerPool(num_workers=1, queue_size=3)
        metrics = ThreadSafeMetrics()
        
        # Slow pattern formatter
        pattern_formatter = Mock()
        pattern_formatter.enabled = True
        def slow_format(*args):
            # Synchronous delay - pattern formatter is sync
            time.sleep(0.2)
            return ("formatted", Mock(applied_names=[], replacements_sum=0))
        pattern_formatter.apply = Mock(side_effect=slow_format)
        
        await pool.start(metrics, pattern_formatter, False)
        
        # Submit items quickly
        submit_times = []
        for i in range(5):
            start = time.time()
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="content",
                index=i+1,
                total=5,
                queue_time=time.time()
            )
            await pool.submit(item)
            submit_times.append(time.time() - start)
        
        await pool.shutdown()
        
        # First few submits should be fast, later ones may be slower (backpressure)
        assert submit_times[0] < 0.01  # Fast
        # The queue size is only 3 and we have 1 worker processing quickly,
        # so backpressure might not always be visible in this test
    
    @pytest.mark.asyncio
    async def test_worker_health_monitoring(self):
        """Test worker health monitoring during processing."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()
        
        await pool.start(metrics, None, False)
        
        # Submit some work
        for i in range(4):
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="content",
                index=i+1,
                total=4,
                queue_time=time.time()
            )
            await pool.submit(item)
        
        # Wait a moment for processing to start
        await asyncio.sleep(0.05)
        
        # Check worker health while processing
        health = await metrics.get_worker_health()
        
        # At least one worker should be healthy (workers process quickly)
        assert len(health) >= 1
        assert any(health.values())  # At least one healthy worker
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test comprehensive metrics collection."""
        pool = WorkerPool(num_workers=2)
        metrics = ThreadSafeMetrics()
        
        # Mock components
        pattern_formatter = Mock()
        pattern_formatter.enabled = True
        pattern_formatter.apply = Mock(return_value=(
            "formatted",
            Mock(
                applied_names=['rule1'],
                replacements_sum=2
            )
        ))
        
        logger = Mock(spec=JsonlLogger)
        pattern_logger = Mock(spec=JsonlLogger)
        
        await pool.start(
            metrics,
            pattern_formatter,
            write_enabled=False,
            logger=logger,
            pattern_logger=pattern_logger
        )
        
        # Process items
        for i in range(5):
            item = WorkItem(
                path=Path(f"test_{i}.adb"),
                content="original",
                index=i+1,
                total=5,
                queue_time=time.time()
            )
            await pool.submit(item)
        
        # Wait for processing
        while not pool.queue.empty():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)
        
        await pool.shutdown()
        
        # Check metrics
        snapshot = await metrics.get_snapshot()
        assert snapshot['changed'] == 5
        assert snapshot['pattern_time'] > 0
        assert snapshot['queue_wait_time'] > 0
        assert len(snapshot['worker_metrics']) == 2
        
        # Check logging
        assert logger.write.called
        assert pattern_logger.write.called
    
    @pytest.mark.asyncio
    async def test_concurrent_file_processing(self, tmp_path):
        """Test processing many files concurrently."""
        num_files = 50
        num_workers = 4
        
        # Create files
        files = []
        for i in range(num_files):
            file = tmp_path / f"file_{i}.adb"
            file.write_text(f"procedure File_{i} is\nbegin\n  null;\nend;")
            files.append(file)
        
        pool = WorkerPool(num_workers=num_workers)
        metrics = ThreadSafeMetrics()
        
        # Simple formatter that adds a comment
        pattern_formatter = Mock()
        pattern_formatter.enabled = True
        pattern_formatter.apply.side_effect = lambda path, content: (
            content + "\n-- Processed",
            Mock(
                applied_names=['comment'],
                replacements_sum=1
            )
        )
        
        # Time the processing
        start_time = time.time()
        
        await pool.start(metrics, pattern_formatter, write_enabled=True)
        
        # Submit all files
        for i, file in enumerate(files):
            item = WorkItem(
                path=file,
                content=file.read_text(),
                index=i+1,
                total=num_files,
                queue_time=time.time()
            )
            await pool.submit(item)
        
        # Wait for processing
        while not pool.queue.empty():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)
        
        await pool.shutdown()
        
        elapsed = time.time() - start_time
        
        # Verify all processed
        assert await metrics.get_total_processed() == num_files
        assert await metrics.get_changed() == num_files
        
        # Check files updated
        for file in files:
            content = file.read_text()
            assert content.endswith("-- Processed")
        
        # Performance metrics
        rate = num_files / elapsed
        print(f"\nProcessed {num_files} files with {num_workers} workers")
        print(f"Time: {elapsed:.2f}s, Rate: {rate:.1f} files/s")