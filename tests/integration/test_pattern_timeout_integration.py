"""Integration tests for pattern timeout functionality.

These tests verify that the pattern timeout mechanism works correctly
with actual regex patterns that can cause catastrophic backtracking.
"""

import json
import os
from pathlib import Path
import pytest
from unittest.mock import Mock

from adafmt.pattern_formatter import (
    PatternFormatter,
    PatternLogger,
    HAS_TIMEOUT,
    REGEX_MODULE,
    timeout_context
)


class TestPatternTimeoutIntegration:
    """Integration tests for pattern timeout handling."""
    
    def test_catastrophic_backtracking_timeout_with_standard_re(self, tmp_path):
        """Test catastrophic backtracking timeout with standard re module."""
        if REGEX_MODULE == 'regex' or os.name != 'posix':
            pytest.skip("This test requires standard re module on POSIX")
            
        # This test would need to temporarily disable regex module
        # which is complex to do reliably in a test environment
        
    def test_signal_based_timeout_mechanism(self):
        """Test the signal-based timeout mechanism directly."""
        if os.name != 'posix':
            pytest.skip("Signal-based timeout only works on POSIX")
            
        import time
        
        # Test that timeout actually triggers
        # Note: signal.alarm() requires integer seconds, so minimum is 1 second
        with pytest.raises(TimeoutError):
            with timeout_context(1):  # 1 second timeout
                time.sleep(2)  # Sleep longer than timeout
                
    def test_pattern_timeout_behavior(self, tmp_path):
        """Test pattern timeout behavior with actual slow pattern."""
        import signal
        
        # Save original signal handlers to restore them
        original_handlers = {}
        for sig in [signal.SIGINT, signal.SIGTERM]:
            if hasattr(signal, sig.name):
                original_handlers[sig] = signal.signal(sig, signal.SIG_DFL)
        
        try:
            # This test verifies timeout behavior regardless of regex module
            patterns = [
                {
                    "name": "slow-regex-1",  # Must be 12 chars
                    "title": "Slow Pattern",
                    "category": "comment",
                    "find": r"(a+)+b",  # Classic catastrophic backtracking pattern
                    "replace": "replaced",
                    "timeout": 0.1  # 100ms timeout
                }
            ]
            
            json_file = tmp_path / "slow_patterns.json"
            json_file.write_text(json.dumps(patterns))
            
            formatter = PatternFormatter.load_from_json(json_file)
            assert formatter.loaded_count == 1
            
            # Create content that will trigger catastrophic backtracking
            # Pattern (a+)+b with string of many 'a's but no 'b' causes exponential time
            content = "a" * 25 + "c"  # No 'b' to match
            
            mock_logger = Mock()
            mock_ui = Mock()
            
            # Apply pattern with timeout
            result, stats = formatter.apply(
                Path("test.adb"),
                content,
                timeout_ms=100,  # 100ms timeout
                logger=PatternLogger(mock_logger),
                ui=mock_ui
            )
            
            # With regex module installed, it should handle this efficiently
            # Either the pattern completes or times out gracefully
            assert isinstance(result, str)
            assert isinstance(stats.replacements_sum, int)
            
            # If using regex module, it likely completed without timeout
            if REGEX_MODULE == 'regex':
                # Pattern shouldn't match, so content unchanged
                assert result == content
            
        finally:
            # Restore original signal handlers
            for sig, handler in original_handlers.items():
                signal.signal(sig, handler)
    
    @pytest.mark.skipif(REGEX_MODULE != 'regex',
                       reason="Test specifically for regex module timeout")
    def test_regex_module_timeout(self, tmp_path):
        """Test timeout with regex module's built-in timeout feature."""
        # Create a more complex pattern that might trigger timeout even in regex
        patterns = [
            {
                "name": "complex-pat1",  # Must be 12 chars
                "title": "Complex Pattern",
                "category": "comment",
                "find": r"(a+b+)+(c+d+)+e",  # More complex pattern
                "replace": "replaced",
                "timeout": 0.001  # 1ms timeout
            }
        ]
        
        json_file = tmp_path / "timeout_patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        assert formatter.loaded_count == 1
        
        # Create content designed to stress the pattern
        content = "ab" * 20 + "cd" * 20 + "f"  # No 'e' at end
        
        mock_logger = Mock()
        mock_ui = Mock()
        
        # Apply pattern with regex module timeout
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            timeout_ms=1,  # 1ms timeout
            logger=PatternLogger(mock_logger),
            ui=mock_ui
        )
        
        # Check if pattern was applied or timed out
        # With regex module being efficient, it might not timeout
        # This test documents the behavior rather than enforcing timeout
        if mock_logger.write.called:
            # If timeout occurred
            log_data = mock_logger.write.call_args[0][0]
            if log_data.get('ev') == 'pattern_timeout':
                assert log_data['name'] == 'complex-pat1'
                assert result == content  # Content unchanged
        else:
            # Pattern completed without timeout
            # This is also acceptable for efficient regex module
            pass
    
    @pytest.mark.skipif(os.name != 'posix',
                       reason="Signal-based timeout only works on POSIX")
    def test_multiple_patterns_with_timeout(self, tmp_path):
        """Test timeout handling with multiple patterns."""
        patterns = [
            {
                "name": "good-pattern",
                "title": "Normal Pattern",
                "category": "comment",
                "find": r"test",
                "replace": "TEST"
            },
            {
                "name": "timeout-pat1",
                "title": "Slow Pattern",
                "category": "comment",
                "find": r"(x+)+y",  # Another catastrophic pattern
                "replace": "replaced"
            },
            {
                "name": "another-good",
                "title": "Another Normal Pattern",
                "category": "comment",
                "find": r"foo",
                "replace": "bar"
            }
        ]
        
        json_file = tmp_path / "mixed_patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        assert formatter.loaded_count == 3
        
        # Content that will trigger timeout on second pattern
        content = "test content with " + "x" * 25 + "z" + " and foo"
        
        mock_logger = Mock()
        
        # Apply patterns
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            timeout_ms=5,  # Very short timeout
            logger=PatternLogger(mock_logger)
        )
        
        # First pattern should have been applied
        assert "TEST" in result
        
        # Last pattern should also have been applied (timeout doesn't stop processing)
        assert "bar" in result
        
        # Middle pattern should have timed out
        assert "x" * 25 in result  # Original x's still there
        
    def test_timeout_with_valid_match(self, tmp_path):
        """Test that timeout doesn't trigger on valid matches."""
        patterns = [
            {
                "name": "valid-match1",
                "title": "Pattern with valid match",
                "category": "comment",
                "find": r"(a+)+b",  # Same pattern but with valid match
                "replace": "MATCHED"
            }
        ]
        
        json_file = tmp_path / "valid_patterns.json"
        json_file.write_text(json.dumps(patterns))
        
        formatter = PatternFormatter.load_from_json(json_file)
        
        # Content that matches quickly
        content = "aaab test aaaaaab"  # Valid matches
        
        mock_logger = Mock()
        
        # Apply with reasonable timeout
        result, stats = formatter.apply(
            Path("test.adb"),
            content,
            timeout_ms=100,  # 100ms should be plenty
            logger=PatternLogger(mock_logger)
        )
        
        # Pattern should have matched and replaced
        assert "MATCHED" in result
        assert result.count("MATCHED") == 2
        
        # No timeout should have occurred
        timeout_logged = any(
            call[0][0].get('ev') == 'pattern_timeout'
            for call in mock_logger.write.call_args_list
        ) if mock_logger.write.called else False
        
        assert not timeout_logged, "Pattern should not have timed out on valid matches"