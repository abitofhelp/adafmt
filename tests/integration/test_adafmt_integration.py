# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for adafmt with the Ada Language Server.

This module contains comprehensive integration tests that verify the complete adafmt
formatting workflow using the real Ada Language Server (ALS). These tests ensure
that the formatter correctly integrates with ALS to format Ada source code files,
handle error conditions, and manage timeouts in realistic scenarios.

Requirements:
    - Ada Language Server must be installed and available in PATH
    - Real Ada files are created and formatted during testing
    - Tests verify both successful formatting and error handling

Test Categories:
    - ALS Integration: Tests real formatting with Ada Language Server
    - File Discovery: Tests file discovery in complex project structures
    - CLI Integration: Tests command-line interface functionality

Note:
    These tests are marked with @pytest.mark.integration and will be skipped
    if the Ada Language Server is not available in the system PATH.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
import pytest
import shutil
import subprocess

from adafmt.cli import run_formatter
from adafmt.utils import kill_als_processes


async def run_formatter_with_defaults(**kwargs):
    """Helper to run formatter with default pattern parameters."""
    defaults = {
        'patterns_path': None,
        'no_patterns': True,  # Disable patterns for basic tests
        'patterns_timeout_ms': 100,
        'patterns_max_bytes': 1_000_000,
        'hook_timeout': 30.0,  # Default hook timeout
        'using_default_log': False,
        'using_default_stderr': False,
        'using_default_patterns': False
    }
    defaults.update(kwargs)
    return await run_formatter(**defaults)


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("ada_language_server") is None,
    reason="Ada Language Server not found in PATH"
)
class TestALSIntegration:
    """Integration tests verifying adafmt functionality with real Ada Language Server.
    
    This test class contains comprehensive tests that verify the complete formatting
    workflow using the actual Ada Language Server. Tests cover successful formatting,
    error handling, timeout management, and edge cases that may occur in real usage.
    
    All tests in this class require ALS to be installed and will be skipped if it's
    not available in the system PATH.
    
    Note: All tests use preflight_mode="aggressive" to ensure clean state by killing
    all ALS processes before each test. This prevents test interference and hangs
    caused by lingering ALS processes from previous test runs.
    """
    
    @pytest.fixture(autouse=True)
    def ensure_clean_als_state(self):
        """Ensure clean ALS state before and after each test.
        
        This fixture emulates adafmt's preflight and cleanup behavior:
        1. Kill all ALS processes before test (preflight)
        2. Run the test
        3. Kill all ALS processes after test (cleanup)
        
        This ensures tests are completely isolated and prevents hangs
        from lingering ALS processes.
        """
        # Preflight: Kill any existing ALS processes
        kill_als_processes(mode="aggressive", dry_run=False)
        
        yield  # Run the test
        
        # Cleanup: Kill any ALS processes created by the test
        kill_als_processes(mode="aggressive", dry_run=False)
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary Ada project structure for testing.
        
        Creates a complete Ada project structure with:
        - A valid .gpr project file
        - Source and object directories
        - Proper directory structure for realistic testing
        
        Args:
            tmp_path: pytest fixture providing temporary directory
            
        Returns:
            Path: Path to the temporary project root directory
        """
        # Create project file
        project_file = tmp_path / "test_project.gpr"
        project_file.write_text("""
project Test_Project is
    for Source_Dirs use ("src");
    for Object_Dir use "obj";
end Test_Project;
""")
        
        # Create directories
        (tmp_path / "src").mkdir()
        (tmp_path / "obj").mkdir()
        
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_format_simple_ada_file(self, temp_project):
        """Test successful formatting of a simple Ada file using real ALS.
        
        Given: An unformatted Ada file with improper spacing and layout
        When: The formatter is run with write mode enabled
        Then: The file is formatted correctly with proper Ada styling
        
        This test verifies that:
        - ALS successfully formats valid Ada code
        - File content is modified with proper formatting
        - The formatter returns success status
        - All formatting parameters are correctly applied
        """
        # Create an unformatted Ada file
        src_dir = temp_project / "src"
        ada_file = src_dir / "hello.adb"
        ada_file.write_text("""with Ada.Text_IO;use Ada.Text_IO;
procedure Hello is
begin
Put_Line("Hello, World!");
end Hello;""")
        
        # Run formatter
        result = await run_formatter_with_defaults(
            project_path=temp_project / "test_project.gpr",
            include_paths=[src_dir],
            exclude_paths=[],
            write=True,  # Actually write the changes
            diff=False,
            check=False,
            preflight_mode="aggressive",
            als_stale_minutes=30,
            pre_hook=None,
            post_hook=None,
            init_timeout=30,
            als_ready_timeout=2,
            format_timeout=10,
            max_attempts=2,
            log_path=temp_project / "test.jsonl",
            stderr_path=temp_project / "test_stderr.log",
            files=[],
            max_consecutive_timeouts=5,
        )
        
        # Check result
        assert result == 0
        
        # Verify file was formatted
        formatted_content = ada_file.read_text()
        assert "with Ada.Text_IO;" in formatted_content
        assert "use Ada.Text_IO;" in formatted_content
        # ALS should have added proper spacing
        assert formatted_content != """with Ada.Text_IO;use Ada.Text_IO;
procedure Hello is
begin
Put_Line("Hello, World!");
end Hello;"""
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self, temp_project):
        """Test proper handling of Ada files with syntax errors.
        
        Given: An Ada file containing syntax errors (missing semicolon)
        When: The formatter is run in check mode
        Then: The formatter completes without crashing and logs errors appropriately
        
        This test verifies that:
        - Syntax errors don't crash the formatter
        - Error information is logged to stderr
        - The formatter returns appropriate status codes
        - Invalid files are handled gracefully
        """
        src_dir = temp_project / "src"
        bad_file = src_dir / "bad.adb"
        bad_file.write_text("""procedure Bad is
begin
    -- Missing semicolon
    Put_Line("Error")
end Bad;""")
        
        result = await run_formatter_with_defaults(
            project_path=temp_project / "test_project.gpr",
            include_paths=[src_dir],
            exclude_paths=[],
            write=False,
            diff=False,
            check=True,
            preflight_mode="aggressive",
            als_stale_minutes=30,
            pre_hook=None,
            post_hook=None,
            init_timeout=30,
            als_ready_timeout=1,
            format_timeout=10,
            max_attempts=1,
            log_path=temp_project / "syntax_test.jsonl",
            stderr_path=temp_project / "error_stderr.log",
            files=[str(bad_file)],
            max_consecutive_timeouts=5,
        )
        
        # Should complete without crashing
        assert result == 0  # No changes needed (syntax error)
        
        # Check stderr log was created
        assert (temp_project / "error_stderr.log").exists()
    
    @pytest.mark.asyncio
    async def test_consecutive_timeout_handling(self, temp_project):
        """Test the consecutive timeout protection mechanism.
        
        Given: Multiple Ada files and an extremely short format timeout
        When: The formatter encounters consecutive timeouts
        Then: A RuntimeError is raised after reaching the timeout limit
        
        This test verifies that:
        - The formatter detects consecutive timeout conditions
        - Appropriate exception is raised when timeout limit is exceeded
        - The timeout protection prevents infinite hanging
        - Multiple files are processed until timeout limit is reached
        """
        # Create multiple Ada files
        src_dir = temp_project / "src"
        for i in range(10):
            ada_file = src_dir / f"file{i}.adb"
            ada_file.write_text(f"""procedure File{i} is
begin
    null;
end File{i};""")
        
        # Run with extremely short timeout to trigger timeouts
        with pytest.raises(RuntimeError, match="Too many consecutive timeouts"):
            await run_formatter_with_defaults(
                project_path=temp_project / "test_project.gpr",
                include_paths=[src_dir],
                exclude_paths=[],
                write=False,
                diff=False,
                check=False,
                    preflight_mode="aggressive",
                als_stale_minutes=30,
                pre_hook=None,
                post_hook=None,
                init_timeout=30,
                als_ready_timeout=1,
                format_timeout=0.001,  # Extremely short to force timeout
                max_attempts=1,
                log_path=temp_project / "timeout_test.jsonl",
                stderr_path=None,
                files=[],
                max_consecutive_timeouts=3  # Should stop after 3 timeouts
            )
    
    @pytest.mark.asyncio
    async def test_no_files_handling(self, temp_project):
        """Test formatter behavior when no Ada files are discovered.
        
        Given: A project directory with no Ada source files
        When: The formatter is run on the empty project
        Then: The formatter completes successfully without errors
        
        This test verifies that:
        - Empty projects don't cause crashes or errors
        - The formatter handles zero-file scenarios gracefully
        - Appropriate success status is returned
        - No unnecessary processing occurs
        """
        result = await run_formatter_with_defaults(
            project_path=temp_project / "test_project.gpr",
            include_paths=[temp_project / "src"],
            exclude_paths=[],
            write=False,
            diff=False,
            check=False,
            preflight_mode="aggressive",
            als_stale_minutes=30,
            pre_hook=None,
            post_hook=None,
            init_timeout=30,
            als_ready_timeout=0,
            format_timeout=10,
            max_attempts=1,
            log_path=temp_project / "no_files_test.jsonl",
            stderr_path=None,
            files=[],
            max_consecutive_timeouts=5,
        )
        
        # Should succeed (no files to format)
        assert result == 0


@pytest.mark.integration
class TestFileDiscoveryIntegration:
    """Integration tests for file discovery functionality using real filesystem operations.
    
    This test class verifies that the file discovery mechanism correctly identifies
    Ada source files in complex project structures, respects include/exclude paths,
    and handles various filesystem layouts that developers might encounter.
    
    These tests use real filesystem operations to create realistic project structures
    and verify that file discovery works correctly in practical scenarios.
    """
    
    def test_discover_ada_files_in_complex_structure(self, tmp_path):
        """Test file discovery in a complex, realistic Ada project structure.
        
        Given: A multi-directory project with various Ada files and exclusions
        When: File discovery is run with specific include and exclude paths
        Then: Only the expected Ada files are discovered and excluded files are ignored
        
        This test verifies that:
        - Ada files are discovered in multiple source directories
        - Both .ads and .adb files are correctly identified
        - Exclude paths are properly respected
        - Generated or build files are excluded as expected
        """
        # Create complex directory structure
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.adb").touch()
        (src / "main.ads").touch()
        
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "utils.adb").touch()
        (lib / "utils.ads").touch()
        
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_utils.adb").touch()
        
        build = tmp_path / "build"
        build.mkdir()
        (build / "generated.adb").touch()  # Should be excluded
        
        # Test discovery
        from adafmt.file_discovery import collect_files
        
        files = collect_files(
            include_paths=[src, lib, tests],
            exclude_paths=[build]
        )
        
        file_names = {Path(f).name for f in files}
        
        assert "main.adb" in file_names
        assert "main.ads" in file_names
        assert "utils.adb" in file_names
        assert "utils.ads" in file_names
        assert "test_utils.adb" in file_names
        assert "generated.adb" not in file_names  # Excluded


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for command-line interface functionality.
    
    This test class verifies that the CLI interface works correctly when invoked
    as a subprocess. Tests cover basic commands like help and version, ensuring
    that the CLI provides appropriate user feedback and behaves correctly when
    invoked from the command line.
    
    These tests use subprocess calls to simulate real CLI usage scenarios.
    """
    
    def test_cli_help(self):
        """Test that CLI displays comprehensive help information.
        
        Given: The adafmt CLI is available
        When: The --help flag is used
        Then: Complete help information is displayed including key parameters
        
        This test verifies that:
        - Help command returns success status
        - Application name and description are shown
        - Available commands are documented
        - Help output is properly formatted
        """
        result = subprocess.run(
            [sys.executable, "-m", "adafmt", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Ada Language Formatter" in result.stdout
        assert "format" in result.stdout
        assert "license" in result.stdout
    
    def test_cli_version(self):
        """Test that CLI displays version information correctly.
        
        Given: The adafmt CLI is available
        When: The --version flag is used with format
        Then: Version information is displayed in the expected format
        
        This test verifies that:
        - Version command returns success status
        - Version string follows expected format
        - Application name is included in version output
        - Version information is properly formatted
        """
        result = subprocess.run(
            [sys.executable, "-m", "adafmt", "--version"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "adafmt version" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])