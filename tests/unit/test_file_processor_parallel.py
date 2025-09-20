# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for file processor parallel integration."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

from adafmt.file_processor import FileProcessor
from adafmt.pattern_formatter import PatternFormatter
from adafmt.als_client import ALSClient
from adafmt.logging_jsonl import JsonlLogger


class TestFileProcessorParallel:
    """Test FileProcessor with parallel workers."""
    
    def test_parallel_mode_detection(self):
        """Test parallel mode is correctly detected based on parameters."""
        # No workers specified - not parallel
        processor = FileProcessor()
        assert not processor.use_parallel
        
        # Workers specified but no pattern formatter - not parallel
        processor = FileProcessor(num_workers=3)
        assert not processor.use_parallel
        
        # Workers specified with disabled pattern formatter - not parallel
        pattern_formatter = Mock(spec=PatternFormatter)
        pattern_formatter.enabled = False
        processor = FileProcessor(num_workers=3, pattern_formatter=pattern_formatter)
        assert not processor.use_parallel
        
        # Workers specified with enabled pattern formatter - parallel
        pattern_formatter.enabled = True
        processor = FileProcessor(num_workers=3, pattern_formatter=pattern_formatter)
        assert processor.use_parallel
    
    @pytest.mark.asyncio
    async def test_worker_pool_initialization(self):
        """Test worker pool is initialized when use_parallel is True."""
        pattern_formatter = Mock(spec=PatternFormatter)
        pattern_formatter.enabled = True
        
        processor = FileProcessor(
            num_workers=2,
            pattern_formatter=pattern_formatter,
            write=True
        )
        
        assert processor.use_parallel
        assert processor.worker_pool is None
        
        await processor.initialize_worker_pool()
        
        assert processor.worker_pool is not None
        assert processor.thread_safe_metrics is not None
        assert processor.worker_pool.num_workers == 2
        
        # Cleanup
        await processor.shutdown_worker_pool()
    
    @pytest.mark.asyncio
    async def test_process_file_with_workers(self, tmp_path):
        """Test processing file with worker pool enabled."""
        # Create test file
        test_file = tmp_path / "test.adb"
        test_file.write_text("procedure Test is\nbegin\n  null;\nend Test;")
        
        # Mock ALS client - simulate formatting response
        als_client = AsyncMock()
        als_client._notify = AsyncMock()
        als_client.request_with_timeout = AsyncMock(return_value=[
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 3, "character": 8}
                },
                "newText": "procedure Test is\nbegin\n   null;\nend Test;"
            }
        ])
        als_client.project_path = tmp_path
        als_client.log_path_stack = []
        als_client.opened_files = set()
        
        # Mock pattern formatter
        pattern_formatter = Mock(spec=PatternFormatter)
        pattern_formatter.enabled = True
        pattern_formatter.format = Mock(return_value=Mock(
            content="procedure Test is\nbegin\n   null; -- formatted\nend Test;",
            replacements=1,
            pattern_counts={'test_rule': 1}
        ))
        
        # Create processor with workers
        processor = FileProcessor(
            client=als_client,
            pattern_formatter=pattern_formatter,
            num_workers=2,
            write=True
        )
        
        await processor.initialize_worker_pool()
        
        # Process file
        status, note = await processor.process_file(test_file, 1, 1, 0.0)
        
        # Debug output
        print(f"Status: {status}, Note: {note}")
        
        # Should return "queued" status when using workers
        assert status == "queued"
        assert note is None
        
        # Check queue size
        print(f"Queue size before wait: {processor.worker_pool.queue.qsize()}")
        
        # Wait a bit for worker to process
        await asyncio.sleep(0.5)
        
        # Check queue size after wait
        print(f"Queue size after wait: {processor.worker_pool.queue.qsize()}")
        
        # Shutdown and check metrics
        await processor.shutdown_worker_pool()
        
        # Check final metrics
        print(f"Pattern files changed: {processor.pattern_files_changed}")
        print(f"Thread safe metrics: {await processor.thread_safe_metrics.get_snapshot() if processor.thread_safe_metrics else 'None'}")
        
        # Worker should have processed the file
        assert processor.pattern_files_changed > 0
    
    @pytest.mark.asyncio
    async def test_process_without_workers(self, tmp_path):
        """Test processing file without worker pool (inline)."""
        # Create test file
        test_file = tmp_path / "test.adb"
        test_file.write_text("procedure Test is\nbegin\n  null;\nend Test;")
        
        # Mock ALS client - no formatting changes
        als_client = AsyncMock()
        als_client._notify = AsyncMock()
        als_client.request_with_timeout = AsyncMock(return_value=[])  # No changes
        als_client.project_path = tmp_path
        als_client.log_path_stack = []
        als_client.opened_files = set()
        
        # Mock pattern formatter
        pattern_formatter = Mock(spec=PatternFormatter)
        pattern_formatter.enabled = True
        pattern_formatter.apply = Mock(return_value=(
            "procedure Test is\nbegin\n   null; -- formatted\nend Test;",
            Mock(applied_names=["test_rule"], replacements_sum=1)
        ))
        pattern_formatter.format = Mock(return_value=Mock(
            content="procedure Test is\nbegin\n   null; -- formatted\nend Test;",
            replacements=1,
            pattern_counts={'test_rule': 1}
        ))
        pattern_formatter.files_touched = {}
        
        # Create processor without workers
        processor = FileProcessor(
            client=als_client,
            pattern_formatter=pattern_formatter,
            write=True
        )
        
        # Process file
        status, note = await processor.process_file(test_file, 1, 1, 0.0)
        
        # Should process inline and return "changed" status
        assert status == "changed"
        assert note is None
        assert processor.pattern_files_changed == 1
    
    @pytest.mark.asyncio
    async def test_no_parallel_when_no_patterns(self):
        """Test no parallel processing when pattern formatter is None."""
        processor = FileProcessor(num_workers=3)
        
        await processor.initialize_worker_pool()
        
        # Should not create worker pool
        assert processor.worker_pool is None
        assert processor.thread_safe_metrics is None
    
    @pytest.mark.asyncio
    async def test_shutdown_without_initialization(self):
        """Test shutdown when worker pool was never initialized."""
        processor = FileProcessor(num_workers=3)
        
        # Should not raise error
        await processor.shutdown_worker_pool()