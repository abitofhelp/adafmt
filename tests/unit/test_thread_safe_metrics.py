# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for thread-safe metrics collection."""

import asyncio
from unittest.mock import patch
import pytest

from adafmt.thread_safe_metrics import ThreadSafeMetrics, WorkerMetrics


class TestWorkerMetrics:
    """Test WorkerMetrics dataclass."""
    
    def test_worker_metrics_initialization(self):
        """Test WorkerMetrics initializes correctly."""
        metrics = WorkerMetrics(worker_id=1)
        
        assert metrics.worker_id == 1
        assert metrics.files_processed == 0
        assert metrics.errors == 0
        assert metrics.total_time == 0.0
        assert metrics.pattern_time == 0.0
        assert metrics.io_time == 0.0
        assert isinstance(metrics.last_activity, float)
    
    @patch('time.time', return_value=1234567890.0)
    def test_worker_metrics_last_activity_timestamp(self, mock_time):
        """Test last_activity is set to current time."""
        metrics = WorkerMetrics(worker_id=2)
        # The dataclass field default_factory is called during initialization
        assert isinstance(metrics.last_activity, float)


class TestThreadSafeMetrics:
    """Test ThreadSafeMetrics class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test metrics collector initializes correctly."""
        with patch('time.time', return_value=1000.0):
            metrics = ThreadSafeMetrics()
        
        snapshot = await metrics.get_snapshot()
        
        assert snapshot['changed'] == 0
        assert snapshot['unchanged'] == 0
        assert snapshot['errors'] == 0
        assert snapshot['skipped'] == 0
        assert snapshot['total_time'] == 0.0
        assert snapshot['pattern_time'] == 0.0
        assert snapshot['io_time'] == 0.0
        assert snapshot['queue_wait_time'] == 0.0
        assert snapshot['worker_metrics'] == {}
        assert snapshot['error_messages'] == []
    
    @pytest.mark.asyncio
    async def test_increment_counters(self):
        """Test incrementing various counters."""
        metrics = ThreadSafeMetrics()
        
        # Increment counters
        await metrics.increment_changed()
        await metrics.increment_changed()
        await metrics.increment_unchanged()
        await metrics.increment_errors()
        await metrics.increment_skipped()
        
        # Check values
        assert await metrics.get_changed() == 2
        assert await metrics.get_errors() == 1
        assert await metrics.get_total_processed() == 5  # 2 changed + 1 unchanged + 1 error + 1 skipped
    
    @pytest.mark.asyncio
    async def test_timing_categories(self):
        """Test adding timing for different categories."""
        metrics = ThreadSafeMetrics()
        
        await metrics.add_timing('total', 1.5)
        await metrics.add_timing('pattern', 0.5)
        await metrics.add_timing('io', 0.3)
        await metrics.add_timing('queue_wait', 0.2)
        
        snapshot = await metrics.get_snapshot()
        
        assert snapshot['total_time'] == 1.5
        assert snapshot['pattern_time'] == 0.5
        assert snapshot['io_time'] == 0.3
        assert snapshot['queue_wait_time'] == 0.2
    
    @pytest.mark.asyncio
    async def test_error_messages(self):
        """Test error message collection."""
        metrics = ThreadSafeMetrics()
        
        # Add error messages
        await metrics.add_error_message("Error 1")
        await metrics.add_error_message("Error 2")
        
        snapshot = await metrics.get_snapshot()
        assert snapshot['error_messages'] == ["Error 1", "Error 2"]
    
    @pytest.mark.asyncio
    async def test_error_message_limit(self):
        """Test error message limit of 100."""
        metrics = ThreadSafeMetrics()
        
        # Add 105 error messages
        for i in range(105):
            await metrics.add_error_message(f"Error {i}")
        
        snapshot = await metrics.get_snapshot()
        assert len(snapshot['error_messages']) == 100
    
    @pytest.mark.asyncio
    async def test_worker_metrics_updates(self):
        """Test updating worker-specific metrics."""
        metrics = ThreadSafeMetrics()
        
        # Update worker 1
        await metrics.update_worker_metrics(
            worker_id=1,
            files_processed=5,
            errors=1,
            time_delta=2.5,
            pattern_time=1.0,
            io_time=0.5
        )
        
        # Update worker 2
        await metrics.update_worker_metrics(
            worker_id=2,
            files_processed=3,
            errors=0,
            time_delta=1.5,
            pattern_time=0.8,
            io_time=0.3
        )
        
        # Update worker 1 again (should accumulate)
        await metrics.update_worker_metrics(
            worker_id=1,
            files_processed=2,
            errors=1,
            time_delta=1.0,
            pattern_time=0.5,
            io_time=0.2
        )
        
        snapshot = await metrics.get_snapshot()
        worker_metrics = snapshot['worker_metrics']
        
        assert worker_metrics[1]['files_processed'] == 7
        assert worker_metrics[1]['errors'] == 2
        assert worker_metrics[1]['total_time'] == 3.5
        assert worker_metrics[1]['pattern_time'] == 1.5
        assert worker_metrics[1]['io_time'] == 0.7
        
        assert worker_metrics[2]['files_processed'] == 3
        assert worker_metrics[2]['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_worker_health_monitoring(self):
        """Test worker health status checking."""
        metrics = ThreadSafeMetrics()
        
        # Create workers with different activity times
        with patch('time.time', return_value=1000.0):
            await metrics.update_worker_metrics(worker_id=1, files_processed=1)
        
        with patch('time.time', return_value=1010.0):
            await metrics.update_worker_metrics(worker_id=2, files_processed=1)
        
        # Check health at different times
        with patch('time.time', return_value=1020.0):
            health = await metrics.get_worker_health()
            assert health[1] is True  # 20s ago, still healthy
            assert health[2] is True  # 10s ago, still healthy
        
        with patch('time.time', return_value=1035.0):
            health = await metrics.get_worker_health()
            assert health[1] is False  # 35s ago, unhealthy
            assert health[2] is True   # 25s ago, still healthy
    
    @pytest.mark.asyncio
    async def test_elapsed_time_tracking(self):
        """Test elapsed time calculation."""
        with patch('time.time', return_value=1000.0):
            metrics = ThreadSafeMetrics()
        
        with patch('time.time', return_value=1060.0):
            snapshot = await metrics.get_snapshot()
            assert snapshot['elapsed_time'] == 60.0
    
    @pytest.mark.asyncio
    async def test_snapshot_returns_copy(self):
        """Test snapshot returns independent copy."""
        metrics = ThreadSafeMetrics()
        
        await metrics.add_error_message("Error 1")
        
        snapshot1 = await metrics.get_snapshot()
        snapshot2 = await metrics.get_snapshot()
        
        # Modify first snapshot
        snapshot1['error_messages'].append("Extra error")
        
        # Second snapshot should be unaffected
        assert len(snapshot2['error_messages']) == 1
        assert snapshot2['error_messages'] == ["Error 1"]
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access is thread-safe."""
        metrics = ThreadSafeMetrics()
        
        async def increment_task():
            for _ in range(100):
                await metrics.increment_changed()
                await asyncio.sleep(0.001)
        
        async def timing_task():
            for i in range(100):
                await metrics.add_timing('total', 0.01)
                await asyncio.sleep(0.001)
        
        async def worker_task(worker_id):
            for _ in range(50):
                await metrics.update_worker_metrics(
                    worker_id=worker_id,
                    files_processed=1
                )
                await asyncio.sleep(0.002)
        
        # Run concurrent tasks
        tasks = [
            increment_task(),
            increment_task(),
            timing_task(),
            worker_task(1),
            worker_task(2)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify final state
        assert await metrics.get_changed() == 200  # 2 tasks * 100 increments
        
        snapshot = await metrics.get_snapshot()
        assert abs(snapshot['total_time'] - 1.0) < 0.01  # 100 * 0.01
        assert snapshot['worker_metrics'][1]['files_processed'] == 50
        assert snapshot['worker_metrics'][2]['files_processed'] == 50
    
    @pytest.mark.asyncio
    async def test_get_total_processed(self):
        """Test total processed calculation."""
        metrics = ThreadSafeMetrics()
        
        await metrics.increment_changed()
        await metrics.increment_changed()
        await metrics.increment_unchanged()
        await metrics.increment_errors()
        await metrics.increment_skipped()
        await metrics.increment_skipped()
        
        total = await metrics.get_total_processed()
        assert total == 6  # 2 + 1 + 1 + 2