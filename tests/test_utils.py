"""Unit tests for the utils module.

This module contains comprehensive unit tests for utility functions that support
the adafmt formatter. Tests cover:

- Path validation and absolute path requirements
- Atomic file writing operations
- ALS process management and detection
- Preflight checks and conflict resolution
- Stale lock file detection and cleanup
- Process killing strategies

These utilities ensure safe, reliable operation of the formatter in various environments.
"""
import os
import signal
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from adafmt.utils import (
    ensure_abs,
    atomic_write,
    list_als_pids,
    preflight,
    _als_processes,
    kill_als_processes,
    find_stale_locks,
    clean_stale_locks,
    ProcessInfo
)


class TestEnsureAbs:
    """Test suite for the ensure_abs path validation function.
    
    Tests the ensure_abs function that enforces absolute path requirements
    for command-line arguments, preventing relative path confusion and
    ensuring consistent behavior across different working directories.
    """
    
    def test_absolute_path_unchanged(self):
        """Test that absolute paths are returned without modification.
        
        Given: An absolute path starting with /
        When: ensure_abs is called with the path
        Then: Returns the same path unchanged
        """
        abs_path = "/home/user/project.gpr"
        result = ensure_abs(abs_path, "--project-file")
        assert result == abs_path
    
    def test_relative_path_raises_error(self):
        """Test that relative paths raise descriptive ValueError.
        
        Given: A relative path without leading /
        When: ensure_abs is called with the path
        Then: Raises ValueError with flag name and path in message
        """
        with pytest.raises(ValueError) as exc_info:
            ensure_abs("relative/path.gpr", "--project-file")
        assert "--project-file must be an absolute path" in str(exc_info.value)
        assert "relative/path.gpr" in str(exc_info.value)
    
    def test_empty_path_raises_error(self):
        """Test that empty paths raise ValueError.
        
        Given: An empty string as path
        When: ensure_abs is called
        Then: Raises ValueError for invalid path
        """
        with pytest.raises(ValueError):
            ensure_abs("", "--some-flag")
    
    @pytest.mark.parametrize("path,flag", [
        ("./local.gpr", "--project-path"),
        ("../parent.gpr", "--include-path"),
        ("subdir/file.gpr", "--exclude-path"),
    ])
    def test_various_relative_paths(self, path, flag):
        """Test various relative path formats all raise errors.
        
        Given: Different forms of relative paths (./, ../, no prefix)
        When: ensure_abs is called with any relative path
        Then: Raises ValueError with appropriate flag name
        """
        with pytest.raises(ValueError) as exc_info:
            ensure_abs(path, flag)
        assert flag in str(exc_info.value)


class TestAtomicWrite:
    """Test suite for the atomic_write function.
    
    Tests the atomic file writing implementation that ensures files are
    written completely or not at all, preventing partial writes and
    corruption during failures.
    """
    
    def test_basic_write(self, tmp_path):
        """Test basic atomic write creates file with content.
        
        Given: A target file path and content string
        When: atomic_write is called
        Then: File is created with the exact content
        """
        target = tmp_path / "test.txt"
        content = "Hello, World!\n"
        
        atomic_write(str(target), content)
        
        assert target.exists()
        assert target.read_text(encoding="utf-8") == content
    
    def test_overwrite_existing_file(self, tmp_path):
        """Test atomic write safely overwrites existing files.
        
        Given: An existing file with old content
        When: atomic_write is called with new content
        Then: File contains new content, old content is replaced
        """
        target = tmp_path / "existing.txt"
        target.write_text("old content")
        
        new_content = "new content\n"
        atomic_write(str(target), new_content)
        
        assert target.read_text(encoding="utf-8") == new_content
    
    def test_creates_parent_directories(self, tmp_path):
        """Test atomic write creates missing parent directories.
        
        Given: A target path with non-existent parent directories
        When: atomic_write is called
        Then: All parent directories are created along with the file
        """
        target = tmp_path / "deep" / "nested" / "dir" / "file.txt"
        
        atomic_write(str(target), "content")
        
        assert target.exists()
        assert target.parent.is_dir()
    
    def test_unicode_content(self, tmp_path):
        """Test atomic write correctly handles Unicode content.
        
        Given: Content containing Unicode characters (Chinese, emoji)
        When: atomic_write is called
        Then: File is written with UTF-8 encoding preserving all characters
        """
        target = tmp_path / "unicode.txt"
        content = "Hello 世界 🚀\n"
        
        atomic_write(str(target), content)
        
        assert target.read_text(encoding="utf-8") == content
    
    def test_atomic_behavior_on_error(self, tmp_path):
        """Test write atomicity is maintained even during failures.
        
        Given: An existing file and a simulated write failure
        When: atomic_write fails during the write operation
        Then: Original file remains unchanged (no partial write)
        """
        target = tmp_path / "atomic.txt"
        target.write_text("original")
        
        # Mock tempfile to simulate write failure
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.side_effect = IOError("Disk full")
            
            with pytest.raises(IOError):
                atomic_write(str(target), "new content")
            
            # Original file should be unchanged
            assert target.read_text() == "original"


class TestListAlsPids:
    """Test suite for the list_als_pids function.
    
    Tests the process ID detection functionality that finds running
    Ada Language Server processes using the pgrep command.
    """
    
    @patch('subprocess.check_output')
    def test_pids_found(self, mock_check_output):
        """Test successful detection of multiple ALS processes.
        
        Given: pgrep returns multiple process IDs
        When: list_als_pids is called
        Then: Returns list of integer PIDs
        """
        mock_check_output.return_value = "12345\n67890\n"
        
        pids = list_als_pids()
        
        assert pids == [12345, 67890]
        mock_check_output.assert_called_once_with(
            ["pgrep", "-f", "ada_language_server"], 
            text=True
        )
    
    @patch('subprocess.check_output')
    def test_no_pids_found(self, mock_check_output):
        """Test when no ALS processes are running.
        
        Given: pgrep returns empty output
        When: list_als_pids is called
        Then: Returns empty list
        """
        mock_check_output.return_value = ""
        
        pids = list_als_pids()
        
        assert pids == []
    
    @patch('subprocess.check_output')
    def test_pgrep_not_found(self, mock_check_output):
        """Test graceful handling when pgrep command is not available.
        
        Given: pgrep command doesn't exist on system
        When: list_als_pids is called
        Then: Returns empty list without crashing
        """
        mock_check_output.side_effect = FileNotFoundError()
        
        pids = list_als_pids()
        
        assert pids == []
    
    @patch('subprocess.check_output')
    def test_pgrep_error(self, mock_check_output):
        """Test handling of pgrep exit code 1 (no matches found).
        
        Given: pgrep exits with code 1 (normal for no matches)
        When: list_als_pids is called
        Then: Returns empty list (not an error condition)
        """
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'pgrep')
        
        pids = list_als_pids()
        
        assert pids == []


class TestPreflight:
    """Test suite for the preflight check function.
    
    Tests the preflight system that detects and handles ALS process
    conflicts and stale lock files before formatting operations begin.
    Covers all preflight modes from passive warning to aggressive cleanup.
    """
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    def test_off_mode(self, mock_locks, mock_procs):
        """Test 'off' mode skips all preflight checks.
        
        Given: Preflight mode set to 'off'
        When: preflight is called
        Then: Returns 0 immediately without checking processes or locks
        """
        result = preflight("off")
        assert result == 0
        mock_procs.assert_not_called()
        mock_locks.assert_not_called()
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    def test_warn_mode_with_processes(self, mock_locks, mock_procs):
        """Test 'warn' mode reports conflicts but continues.
        
        Given: Running ALS processes and stale locks exist
        When: preflight is called in 'warn' mode
        Then: Logs warning message with counts and returns 0
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=5.0)
        proc2 = ProcessInfo(pid=456, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1, proc2]
        mock_locks.return_value = [Path("/tmp/.als-lock")]
        
        logger = MagicMock()
        result = preflight("warn", logger=logger)
        
        assert result == 0
        logger.assert_called_with("[preflight] ALS processes (user): 2; stale locks: 1")
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    def test_fail_mode_with_conflicts(self, mock_locks, mock_procs):
        """Test 'fail' mode aborts when conflicts are detected.
        
        Given: At least one ALS process is running
        When: preflight is called in 'fail' mode
        Then: Logs conflict message and returns exit code 2
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=5.0)
        mock_procs.return_value = [proc1]
        mock_locks.return_value = []
        
        logger = MagicMock()
        result = preflight("fail", logger=logger)
        
        assert result == 2
        logger.assert_any_call("[preflight] ALS processes (user): 1; stale locks: 0")
        logger.assert_any_call("[preflight] Conflicts found; aborting due to --preflight=fail")
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    def test_fail_mode_no_conflicts(self, mock_locks, mock_procs):
        """Test 'fail' mode succeeds when no conflicts exist.
        
        Given: No ALS processes or stale locks
        When: preflight is called in 'fail' mode
        Then: Returns 0 allowing formatting to proceed
        """
        mock_procs.return_value = []
        mock_locks.return_value = []
        
        result = preflight("fail")
        assert result == 0
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    @patch('adafmt.utils.kill_als_processes')
    def test_safe_mode(self, mock_kill, mock_locks, mock_procs):
        """Test 'safe' mode kills only stale ALS processes.
        
        Given: ALS process older than stale threshold
        When: preflight is called in 'safe' mode
        Then: Kills stale processes and returns 0
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1]
        mock_locks.return_value = []
        mock_kill.return_value = 1
        
        logger = MagicMock()
        result = preflight("safe", als_stale_minutes=30, logger=logger)
        
        assert result == 0
        mock_kill.assert_called_once_with(
            mode="safe",
            stale_minutes=30,
            logger=logger,
            dry_run=False
        )
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    @patch('adafmt.utils.kill_als_processes')
    @patch('adafmt.utils.clean_stale_locks')
    def test_kill_clean_mode(self, mock_clean, mock_kill, mock_locks, mock_procs):
        """Test 'kill+clean' mode removes processes and lock files.
        
        Given: ALS processes and stale lock files exist
        When: preflight is called in 'kill+clean' mode
        Then: Kills processes, cleans locks, logs actions, returns 0
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1]
        mock_locks.return_value = [Path("/tmp/.als-lock")]
        mock_kill.return_value = 1
        mock_clean.return_value = 1
        
        logger = MagicMock()
        result = preflight("kill+clean", logger=logger)
        
        assert result == 0
        mock_kill.assert_called_once()
        mock_clean.assert_called_once()
        logger.assert_any_call("[preflight] Removed 1 stale ALS locks")
    
    @patch('adafmt.utils._als_processes')
    @patch('adafmt.utils.find_stale_locks')
    @patch('adafmt.utils.kill_als_processes')
    def test_aggressive_mode(self, mock_kill, mock_locks, mock_procs):
        """Test 'aggressive' mode kills all ALS processes regardless of age.
        
        Given: Both fresh and stale ALS processes running
        When: preflight is called in 'aggressive' mode
        Then: Kills all processes including fresh ones
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=1.0)
        proc2 = ProcessInfo(pid=456, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1, proc2]
        mock_locks.return_value = []
        mock_kill.return_value = 2
        
        result = preflight("aggressive")
        
        assert result == 0
        mock_kill.assert_called_once_with(
            mode="aggressive",
            stale_minutes=30,
            logger=None,
            dry_run=False
        )


# Add subprocess import for the test
import subprocess
import time
from unittest.mock import MagicMock


class TestKillAlsProcesses:
    """Test suite for the kill_als_processes function.
    
    Tests the various strategies for terminating ALS processes,
    from conservative 'safe' mode to aggressive cleanup of all processes.
    """
    
    @patch('adafmt.utils._als_processes')
    def test_off_mode(self, mock_procs):
        """Test 'off' mode performs no process termination.
        
        Given: Mode set to 'off'
        When: kill_als_processes is called
        Then: Returns 0 without checking for processes
        """
        result = kill_als_processes("off")
        assert result == 0
        mock_procs.assert_not_called()
    
    @patch('adafmt.utils._als_processes')
    @patch('os.kill')
    @patch('time.sleep')
    def test_safe_mode_kills_stale(self, mock_sleep, mock_kill, mock_procs):
        """Test 'safe' mode selectively kills only stale processes.
        
        Given: Mix of fresh and stale ALS processes
        When: kill_als_processes is called in 'safe' mode
        Then: Only processes older than stale threshold are terminated
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=5.0)
        proc2 = ProcessInfo(pid=456, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1, proc2]
        
        logger = MagicMock()
        result = kill_als_processes("safe", stale_minutes=30, logger=logger)
        
        assert result == 1  # Only killed the stale one
        # Should only kill the process older than 30 minutes
        mock_kill.assert_any_call(456, signal.SIGTERM)
        logger.assert_called_with("[preflight] Killing ALS pid=456 age=35.0m cmd='ada_language_server'")
    
    @patch('adafmt.utils._als_processes')
    @patch('os.kill')
    @patch('time.sleep')
    def test_aggressive_mode_kills_all(self, mock_sleep, mock_kill, mock_procs):
        """Test 'aggressive' mode terminates all ALS processes.
        
        Given: Multiple ALS processes of any age
        When: kill_als_processes is called in 'aggressive' mode
        Then: All processes are terminated regardless of age
        """
        proc1 = ProcessInfo(pid=123, cmdline="ada_language_server", user="user", age_minutes=1.0)
        proc2 = ProcessInfo(pid=456, cmdline="ada_language_server", user="user", age_minutes=35.0)
        mock_procs.return_value = [proc1, proc2]
        
        result = kill_als_processes("aggressive")
        
        assert result == 2  # Killed both
        assert mock_kill.call_count >= 2  # At least SIGTERM for both


class TestFindStaleLocks:
    """Test suite for the find_stale_locks function.
    
    Tests the detection of stale ALS lock files and directories
    that may be left behind after abnormal process termination.
    """
    
    @patch('adafmt.utils._iter_lock_dirs')
    @patch('time.time')
    def test_find_stale_directory_locks(self, mock_time, mock_iter):
        """Test detection of stale lock directories based on age.
        
        Given: Lock directories with different ages
        When: find_stale_locks is called with TTL threshold
        Then: Returns only locks older than the TTL
        """
        mock_time.return_value = 1000.0  # Current time
        
        lock1 = MagicMock(spec=Path)
        lock1.is_dir.return_value = True
        lock1.stat.return_value.st_mtime = 400.0  # 10 minutes old
        lock1.__truediv__.return_value = MagicMock(exists=MagicMock(return_value=False))  # No pid file
        
        lock2 = MagicMock(spec=Path)
        lock2.is_dir.return_value = True
        lock2.stat.return_value.st_mtime = 950.0  # Less than 1 minute old
        
        mock_iter.return_value = [lock1, lock2]
        
        result = find_stale_locks([Path("/tmp")], ttl_minutes=10)
        
        assert len(result) == 1
        assert result[0] == lock1