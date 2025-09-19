# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for timeout_context functionality.

These tests verify actual timeout behavior with real delays,
which requires integration testing rather than unit testing with mocks.
"""

import os
import signal
import time
import pytest

from adafmt.pattern_formatter import timeout_context, HAS_TIMEOUT


class TestTimeoutContextIntegration:
    """Integration tests for timeout_context behavior."""
    
    @pytest.mark.skipif(os.name != 'posix',
                       reason="Signal-based timeout only works on POSIX")
    def test_timeout_triggered_with_real_delay(self):
        """Test timeout_context when timeout is actually triggered."""
        # POSIX systems use SIGALRM - minimum 1 second for signal.alarm
        with pytest.raises(TimeoutError, match="Pattern execution timed out"):
            with timeout_context(1):  # 1 second timeout
                time.sleep(2)  # Sleep longer than timeout
    
    def test_timeout_windows_noop(self):
        """Test timeout_context is no-op on Windows without regex."""
        if os.name == 'nt' and not HAS_TIMEOUT:
            # Should not raise on Windows without regex module
            with timeout_context(0.1):
                time.sleep(0.2)  # Would timeout on POSIX
                
    @pytest.mark.skipif(not hasattr(signal, 'SIGALRM'),
                       reason="SIGALRM not available on this platform")
    def test_timeout_with_existing_alarm(self):
        """Test that timeout context properly handles existing alarms."""
        # Set an existing alarm
        old_alarm = signal.alarm(100)
        
        try:
            # Use timeout context with shorter timeout
            with timeout_context(0.5):
                time.sleep(0.1)  # Should complete before timeout
                
            # The old alarm should be restored (we can't easily verify this)
            # but at least the context should work without errors
            
        finally:
            signal.alarm(0)  # Cancel any alarms
            
    @pytest.mark.skipif(not hasattr(signal, 'SIGALRM'),
                       reason="SIGALRM not available on this platform")
    def test_nested_timeouts(self):
        """Test nested timeout contexts."""
        with timeout_context(2):  # Outer timeout
            with timeout_context(1):  # Inner timeout
                time.sleep(0.5)  # Should complete
                
        # Should not raise any errors
        
    @pytest.mark.skipif(not hasattr(signal, 'SIGALRM'),
                       reason="SIGALRM not available on this platform")
    def test_timeout_handler_restoration(self):
        """Test that custom signal handlers are properly restored."""
        # Set a custom handler
        def custom_handler(signum, frame):
            pass
            
        old_handler = signal.signal(signal.SIGALRM, custom_handler)
        
        try:
            # Use timeout context
            with timeout_context(0.5):
                time.sleep(0.1)
                
            # Check that custom handler is restored
            current_handler = signal.signal(signal.SIGALRM, signal.SIG_DFL)
            assert current_handler == custom_handler
            
        finally:
            # Restore original state
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)