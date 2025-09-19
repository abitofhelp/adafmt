#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Unit tests for performance metrics collection."""

import json
import tempfile
from pathlib import Path
import pytest

from adafmt.metrics import MetricsCollector


class TestMetricsCollector:
    """Test suite for performance metrics collection."""
    
    def test_metrics_file_creation(self, tmp_path):
        """Test that metrics file is created with proper structure.
        
        Given: A temporary directory for metrics
        When: MetricsCollector writes metrics
        Then: JSONL file is created with valid JSON on each line
        """
        metrics_path = tmp_path / "test_metrics.jsonl"
        collector = MetricsCollector(str(metrics_path))
        
        # Record a file format metric
        collector.record_file_format(
            file_path="/src/test.adb",
            als_success=True,
            als_edits=3,
            patterns_applied=["comment-norm", "operator-asg"],
            duration=0.123
        )
        
        # Verify file exists
        assert metrics_path.exists()
        
        # Verify content is valid JSONL
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data['ev'] == 'file_format'
        assert data['path'] == '/src/test.adb'
        assert data['als_success'] is True
        assert data['als_edits'] == 3
        assert data['patterns_applied'] == ["comment-norm", "operator-asg"]
        assert data['duration_ms'] == 123.0
        assert 'run_id' in data
        assert 'ts' in data
    
    def test_timing_functions(self, tmp_path):
        """Test timer start/end functionality.
        
        Given: A metrics collector
        When: Using start_timer and end_timer
        Then: Duration is recorded accurately
        """
        metrics_path = tmp_path / "test_metrics.jsonl"
        collector = MetricsCollector(str(metrics_path))
        
        # Start and end a timer
        collector.start_timer('test_operation')
        import time
        time.sleep(0.1)  # Sleep 100ms
        duration = collector.end_timer('test_operation', extra_field='test_value')
        
        # Duration should be around 0.1 seconds
        assert 0.09 < duration < 0.15
        
        # Check recorded metric
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
        
        data = json.loads(lines[0])
        assert data['ev'] == 'timing'
        assert data['name'] == 'test_operation'
        assert 90 < data['duration_ms'] < 150
        assert data['extra_field'] == 'test_value'
    
    def test_run_summary(self, tmp_path):
        """Test run summary metrics recording.
        
        Given: A completed formatting run
        When: Recording run summary
        Then: Summary metrics are properly recorded
        """
        metrics_path = tmp_path / "test_metrics.jsonl"
        collector = MetricsCollector(str(metrics_path))
        
        collector.record_run_summary(
            total_files=10,
            als_succeeded=8,
            als_failed=2,
            patterns_changed=5,
            total_duration=12.5
        )
        
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
        
        data = json.loads(lines[0])
        assert data['ev'] == 'run_summary'
        assert data['total_files'] == 10
        assert data['als_succeeded'] == 8
        assert data['als_failed'] == 2
        assert data['patterns_changed'] == 5
        assert data['duration_ms'] == 12500.0
        assert data['avg_file_ms'] == 1250.0
    
    def test_default_path(self):
        """Test that default path uses ~/.adafmt/metrics.jsonl.
        
        Given: No explicit metrics path
        When: Creating MetricsCollector
        Then: Uses ~/.adafmt/metrics.jsonl
        """
        collector = MetricsCollector()
        expected_path = Path.home() / ".adafmt" / "metrics.jsonl"
        assert collector.path == expected_path
    
    def test_cumulative_metrics(self, tmp_path):
        """Test that metrics accumulate across multiple runs.
        
        Given: Multiple metric collection sessions
        When: Writing metrics in each session
        Then: All metrics are preserved in the file
        """
        metrics_path = tmp_path / "test_metrics.jsonl"
        
        # First run
        collector1 = MetricsCollector(str(metrics_path))
        collector1.record_file_format(
            file_path="/src/file1.adb",
            als_success=True,
            als_edits=1,
            patterns_applied=[],
            duration=0.1
        )
        
        # Second run (different instance)
        collector2 = MetricsCollector(str(metrics_path))
        collector2.record_file_format(
            file_path="/src/file2.adb",
            als_success=True,
            als_edits=2,
            patterns_applied=["hygiene-eol"],
            duration=0.2
        )
        
        # Verify both metrics exist
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        data1 = json.loads(lines[0])
        assert data1['path'] == '/src/file1.adb'
        assert data1['als_edits'] == 1
        
        data2 = json.loads(lines[1])
        assert data2['path'] == '/src/file2.adb'
        assert data2['als_edits'] == 2
        
        # Different run IDs
        assert data1['run_id'] != data2['run_id']
    
    def test_pattern_timeout_recording(self, tmp_path):
        """Test pattern timeout event recording.
        
        Given: A pattern timeout occurs
        When: Recording the timeout
        Then: Timeout event is properly logged
        """
        metrics_path = tmp_path / "test_metrics.jsonl"
        collector = MetricsCollector(str(metrics_path))
        
        collector.record_pattern_timeout(
            pattern_name="complex_pattern",
            file_path="/src/big_file.adb",
            timeout_ms=100
        )
        
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
        
        data = json.loads(lines[0])
        assert data['ev'] == 'pattern_timeout'
        assert data['pattern_name'] == 'complex_pattern'
        assert data['path'] == '/src/big_file.adb'
        assert data['timeout_ms'] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])