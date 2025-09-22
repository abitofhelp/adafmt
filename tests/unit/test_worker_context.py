# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for worker context and data structures."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import pytest

from adafmt.worker_context import WorkItem, WorkerContext
from adafmt.thread_safe_metrics import ThreadSafeMetrics
from adafmt.pattern_formatter import PatternFormatter
from adafmt.logging_jsonl import JsonlLogger


class TestWorkItem:
    """Test WorkItem dataclass."""
    
    def test_work_item_creation(self):
        """Test creating a WorkItem."""
        item = WorkItem(
            path=Path("test.adb"),
            content="procedure Test;",
            index=1,
            total=10,
            queue_time=1234.5
        )
        
        assert item.path == Path("test.adb")
        assert item.content == "procedure Test;"
        assert item.index == 1
        assert item.total == 10
        assert item.queue_time == 1234.5
    
    def test_work_item_equality(self):
        """Test WorkItem equality comparison."""
        item1 = WorkItem(
            path=Path("test.adb"),
            content="content",
            index=1,
            total=10,
            queue_time=100.0
        )
        
        item2 = WorkItem(
            path=Path("test.adb"),
            content="content",
            index=1,
            total=10,
            queue_time=100.0
        )
        
        assert item1 == item2
    
    def test_work_item_different_paths(self):
        """Test WorkItems with different paths are not equal."""
        item1 = WorkItem(Path("a.adb"), "content", 1, 10, 100.0)
        item2 = WorkItem(Path("b.adb"), "content", 1, 10, 100.0)
        
        assert item1 != item2


class TestWorkerContext:
    """Test WorkerContext class."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        return {
            'metrics': Mock(spec=ThreadSafeMetrics),
            'pattern_formatter': Mock(spec=PatternFormatter),
            'logger': Mock(spec=JsonlLogger),
            'pattern_logger': Mock(spec=JsonlLogger),
            'ui_queue': asyncio.Queue(),
        }
    
    def test_context_initialization(self, mock_components):
        """Test WorkerContext initialization."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=mock_components['pattern_formatter'],
            logger=mock_components['logger'],
            pattern_logger=mock_components['pattern_logger'],
            write_enabled=True,
            diff_enabled=False,
            buffer_size=4096,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        assert context.metrics == mock_components['metrics']
        assert context.pattern_formatter == mock_components['pattern_formatter']
        assert context.logger == mock_components['logger']
        assert context.pattern_logger == mock_components['pattern_logger']
        assert context.write_enabled is True
        assert context.diff_enabled is False
        assert context.buffer_size == 4096
        assert context.ui_queue == mock_components['ui_queue']
        assert isinstance(context.shutdown_event, asyncio.Event)
        assert not context.shutdown_event.is_set()
    
    def test_context_with_existing_shutdown_event(self, mock_components):
        """Test context with pre-existing shutdown event."""
        shutdown_event = asyncio.Event()
        
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=True,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=shutdown_event
        )
        
        assert context.shutdown_event is shutdown_event
    
    def test_should_shutdown(self, mock_components):
        """Test shutdown checking."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        # Initially not shutting down
        assert not context.should_shutdown()
        
        # Set shutdown
        context.shutdown_event.set()
        assert context.should_shutdown()
    
    @pytest.mark.asyncio
    async def test_report_completion(self, mock_components):
        """Test reporting file completion."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        # Report completion
        await context.report_completion(
            path=Path("test.adb"),
            index=5,
            total=20,
            status="changed",
            note="Formatted",
            worker_id=2
        )
        
        # Check message in queue
        message = await context.ui_queue.get()
        assert message == {
            'type': 'completion',
            'path': Path("test.adb"),
            'index': 5,
            'total': 20,
            'status': 'changed',
            'note': 'Formatted',
            'worker_id': 2
        }
    
    @pytest.mark.asyncio
    async def test_report_completion_minimal(self, mock_components):
        """Test reporting completion with minimal params."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        await context.report_completion(
            path=Path("test.ads"),
            index=1,
            total=1,
            status="unchanged"
        )
        
        message = await context.ui_queue.get()
        assert message['note'] is None
        assert message['worker_id'] == 0
    
    @pytest.mark.asyncio
    async def test_report_error(self, mock_components):
        """Test reporting errors."""
        # Make metrics async
        mock_components['metrics'].add_error_message = AsyncMock()
        
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=mock_components['logger'],
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        test_error = ValueError("Test error")
        await context.report_error(
            path=Path("error.adb"),
            error=test_error,
            worker_id=3
        )
        
        # Check metrics updated
        mock_components['metrics'].add_error_message.assert_called_once_with(
            "Worker 3: error.adb - Test error"
        )
        
        # Check logger called
        mock_components['logger'].write.assert_called_once_with({
            'ev': 'worker_error',
            'worker_id': 3,
            'path': 'error.adb',
            'error': 'Test error',
            'error_type': 'ValueError'
        })
    
    @pytest.mark.asyncio
    async def test_report_error_no_logger(self, mock_components):
        """Test error reporting without logger."""
        mock_components['metrics'].add_error_message = AsyncMock()
        
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,  # No logger
            pattern_logger=None,
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        await context.report_error(
            path=Path("error.adb"),
            error=RuntimeError("Runtime error"),
            worker_id=1
        )
        
        # Metrics should still be updated
        mock_components['metrics'].add_error_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_pattern_result(self, mock_components):
        """Test logging pattern application results."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=mock_components['pattern_logger'],
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        await context.log_pattern_result(
            path=Path("formatted.adb"),
            patterns_applied=5,
            replacements=12,
            time_taken=0.123,
            worker_id=2
        )
        
        mock_components['pattern_logger'].write.assert_called_once_with({
            'ev': 'pattern_applied',
            'worker_id': 2,
            'path': 'formatted.adb',
            'patterns_applied': 5,
            'replacements': 12,
            'time_ms': 123
        })
    
    @pytest.mark.asyncio
    async def test_log_pattern_result_no_logger(self, mock_components):
        """Test pattern logging without logger."""
        context = WorkerContext(
            metrics=mock_components['metrics'],
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,  # No pattern logger
            write_enabled=False,
            diff_enabled=False,
            ui_queue=mock_components['ui_queue'],
            shutdown_event=None
        )
        
        # Should not raise error
        await context.log_pattern_result(
            path=Path("test.adb"),
            patterns_applied=1,
            replacements=2,
            time_taken=0.5,
            worker_id=1
        )
    
    def test_context_minimal_init(self):
        """Test context with minimal initialization."""
        metrics = Mock(spec=ThreadSafeMetrics)
        ui_queue = asyncio.Queue()
        
        context = WorkerContext(
            metrics=metrics,
            pattern_formatter=None,
            logger=None,
            pattern_logger=None,
            write_enabled=True,
            diff_enabled=False,
            ui_queue=ui_queue,
            shutdown_event=None
        )
        
        assert context.metrics == metrics
        assert context.pattern_formatter is None
        assert context.logger is None
        assert context.pattern_logger is None
        assert context.write_enabled is True
        assert context.diff_enabled is False
        assert context.buffer_size == 8192  # Default
        assert context.ui_queue == ui_queue
        assert isinstance(context.shutdown_event, asyncio.Event)