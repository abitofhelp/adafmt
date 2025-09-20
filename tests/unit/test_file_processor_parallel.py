# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for file processor parallel configuration."""

from unittest.mock import Mock
import pytest

from adafmt.file_processor import FileProcessor
from adafmt.pattern_formatter import PatternFormatter


class TestFileProcessorParallelConfig:
    """Test FileProcessor parallel mode configuration."""
    
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
        
        # Zero workers with pattern formatter - not parallel
        processor = FileProcessor(num_workers=0, pattern_formatter=pattern_formatter)
        assert not processor.use_parallel
    
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