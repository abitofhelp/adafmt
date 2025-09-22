# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Performance tests for async file I/O operations."""

import asyncio
import time
import pytest

from adafmt.async_file_io import (
    buffered_read,
    atomic_write_async,
)


class TestAsyncIOPerformance:
    """Performance tests for async I/O operations."""
    
    @pytest.mark.asyncio
    async def test_buffered_read_performance(self, tmp_path):
        """Test performance of buffered async read vs sync read."""
        # Create test file with 1MB of content
        test_file = tmp_path / "large.txt"
        content = "x" * (1024 * 1024)  # 1MB
        test_file.write_text(content)
        
        # Time async read
        start = time.perf_counter()
        async_content = await buffered_read(test_file, buffer_size=8192)
        async_time = time.perf_counter() - start
        
        # Time sync read for comparison
        start = time.perf_counter()
        sync_content = test_file.read_text()
        sync_time = time.perf_counter() - start
        
        # Verify content matches
        assert async_content == sync_content
        
        # Log performance (async should be comparable)
        print(f"\nAsync read time: {async_time:.4f}s")
        print(f"Sync read time: {sync_time:.4f}s")
        print(f"Ratio (async/sync): {async_time/sync_time:.2f}")
    
    @pytest.mark.asyncio
    async def test_concurrent_reads(self, tmp_path):
        """Test performance of concurrent async reads."""
        # Create multiple test files
        files = []
        for i in range(10):
            test_file = tmp_path / f"file_{i}.txt"
            test_file.write_text(f"Content of file {i}\n" * 1000)
            files.append(test_file)
        
        # Time concurrent async reads
        start = time.perf_counter()
        tasks = [buffered_read(f) for f in files]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start
        
        # Time sequential sync reads
        start = time.perf_counter()
        sync_results = [f.read_text() for f in files]
        sequential_time = time.perf_counter() - start
        
        # Verify results match
        assert results == sync_results
        
        # Log performance
        print(f"\nConcurrent async time: {concurrent_time:.4f}s")
        print(f"Sequential sync time: {sequential_time:.4f}s")
        print(f"Speedup: {sequential_time/concurrent_time:.2f}x")
    
    @pytest.mark.asyncio
    async def test_atomic_write_performance(self, tmp_path):
        """Test performance of atomic writes."""
        test_file = tmp_path / "atomic.txt"
        content = "Test content\n" * 10000  # ~120KB
        
        # Time multiple atomic writes
        iterations = 10
        start = time.perf_counter()
        for i in range(iterations):
            await atomic_write_async(test_file, f"{content}\nIteration {i}")
        atomic_time = time.perf_counter() - start
        
        # Average time per write
        avg_time = atomic_time / iterations
        print(f"\nAverage atomic write time: {avg_time:.4f}s")
        print(f"Total time for {iterations} writes: {atomic_time:.4f}s")
        
        # Verify final content
        assert f"Iteration {iterations-1}" in test_file.read_text()
    
    @pytest.mark.asyncio
    async def test_buffer_size_impact(self, tmp_path):
        """Test impact of buffer size on performance."""
        test_file = tmp_path / "buffer_test.txt"
        content = "x" * (5 * 1024 * 1024)  # 5MB
        test_file.write_text(content)
        
        buffer_sizes = [1024, 4096, 8192, 16384, 32768]
        results = []
        
        for buffer_size in buffer_sizes:
            start = time.perf_counter()
            await buffered_read(test_file, buffer_size=buffer_size)
            elapsed = time.perf_counter() - start
            results.append((buffer_size, elapsed))
            print(f"\nBuffer size {buffer_size}: {elapsed:.4f}s")
        
        # Generally, larger buffers should be faster (to a point)
        # Just verify we can read with different buffer sizes
        assert all(elapsed > 0 for _, elapsed in results)