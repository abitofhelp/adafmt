# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Tests for hook security improvements."""

from unittest.mock import patch, MagicMock
import subprocess

from adafmt.utils import run_hook


class TestHookSecurity:
    """Test secure hook execution."""
    
    @patch('subprocess.run')
    def test_hook_no_shell_injection(self, mock_run):
        """Test that shell metacharacters are not interpreted."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr="", 
        )
        
        # Attempt shell injection - should be treated as literal
        malicious_hook = 'echo test; rm -rf /'
        result = run_hook(malicious_hook, "test")
        
        # Verify subprocess.run was called with a list, not shell=True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        
        # First argument should be a list
        assert isinstance(call_args[0][0], list)
        assert call_args[0][0] == ['echo', 'test;', 'rm', '-rf', '/']
        
        # Ensure shell=False (default when not specified)
        assert call_args[1].get('shell', False) is False
        
    @patch('subprocess.run')
    def test_hook_with_quotes(self, mock_run):
        """Test that quoted arguments are parsed correctly."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        
        hook_cmd = 'git commit -m "Auto-format Ada code"'
        result = run_hook(hook_cmd, "test")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ['git', 'commit', '-m', 'Auto-format Ada code']
        
    def test_hook_invalid_quotes(self):
        """Test handling of invalid quoted strings."""
        # Unmatched quotes should fail parsing
        hook_cmd = 'echo "unclosed quote'
        logger_calls = []
        
        result = run_hook(hook_cmd, "test", logger=logger_calls.append)
        
        assert result is False
        assert any("Invalid command format" in call for call in logger_calls)
        
    @patch('subprocess.run')
    def test_hook_timeout(self, mock_run):
        """Test that timeout is properly passed."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        
        result = run_hook("echo test", "test", timeout=10)
        
        mock_run.assert_called_once()
        assert mock_run.call_args[1]['timeout'] == 10
        
    @patch('subprocess.run')
    def test_hook_timeout_exceeded(self, mock_run):
        """Test handling when hook exceeds timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('echo', 5)
        logger_calls = []
        
        result = run_hook("sleep 10", "test", timeout=5, logger=logger_calls.append)
        
        assert result is False
        assert any("timeout after 5s" in call for call in logger_calls)
        
    @patch('subprocess.run')
    def test_hook_with_environment_variables(self, mock_run):
        """Test that environment variables in commands are not expanded."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        
        # $HOME should not be expanded
        hook_cmd = 'echo $HOME'
        result = run_hook(hook_cmd, "test")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # $HOME is passed as literal argument
        assert call_args[0][0] == ['echo', '$HOME']
        
    def test_hook_dry_run(self):
        """Test that dry run doesn't execute commands."""
        logger_calls = []
        
        with patch('subprocess.run') as mock_run:
            result = run_hook("echo test", "test", logger=logger_calls.append, dry_run=True)
            
        # Command should not be executed
        mock_run.assert_not_called()
        assert result is True
        assert any("[dry-run]" in call for call in logger_calls)
        
    @patch('subprocess.run')
    def test_hook_command_with_spaces_in_path(self, mock_run):
        """Test handling of paths with spaces."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        
        # Properly quoted path with spaces
        hook_cmd = '"/path with spaces/script.sh" --arg value'
        result = run_hook(hook_cmd, "test")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ['/path with spaces/script.sh', '--arg', 'value']