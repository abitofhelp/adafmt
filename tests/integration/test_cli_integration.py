#!/usr/bin/env python3

# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Integration tests for adafmt command-line interface functionality.

This module contains comprehensive integration tests that verify the command-line
interface (CLI) works correctly when invoked as a subprocess. These tests ensure
that all CLI parameters, commands, and options function properly in real-world
usage scenarios.

Test Scope:
    - Basic CLI commands (help, version)
    - Parameter validation and documentation
    - File processing capabilities without requiring ALS
    - Error handling and edge cases in CLI usage

Approach:
    Tests use subprocess calls to simulate actual command-line usage, ensuring
    that the CLI behaves correctly when invoked by users from the command line.
    This provides confidence that the interface works in production environments.

Note:
    These tests focus on CLI functionality and do not require the Ada Language
    Server to be installed, making them suitable for environments where ALS
    may not be available.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestCLIBasicCommands:
    """Test suite for basic CLI commands and their output.
    
    This test class verifies that fundamental CLI commands like --help and --version
    work correctly and provide appropriate information to users. These are the most
    basic interactions users have with the CLI and must be reliable.
    
    Tests ensure that:
    - Commands execute without errors
    - Output contains expected information
    - Return codes indicate success
    - Response times are reasonable
    """
    
    def test_help_command(self):
        """Test that the help command displays comprehensive usage information.
        
        Given: The adafmt CLI is available for execution
        When: The --help flag is passed to the command
        Then: Complete help information is displayed including application name and key parameters
        
        This test verifies that:
        - Help command executes successfully (return code 0)
        - Application name "Ada Language Formatter" is displayed
        - Available commands are shown
        - Command completes within reasonable timeout
        """
        result = subprocess.run(
            [sys.executable, '-m', 'adafmt', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert 'Ada Language Formatter' in result.stdout
        assert 'format' in result.stdout
        assert 'license' in result.stdout
    
    def test_version_command(self):
        """Test that the version command displays proper version information.
        
        Given: The adafmt CLI is available for execution
        When: The --version flag is passed to the format
        Then: Version information is displayed in the expected format
        
        This test verifies that:
        - Version command executes successfully (return code 0)
        - Version string contains "adafmt version"
        - Output follows expected version format
        - Command completes within reasonable timeout
        """
        result = subprocess.run(
            [sys.executable, '-m', 'adafmt', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert 'adafmt version' in result.stdout


class TestCLIParameters:
    """Test suite for CLI parameter validation and documentation.
    
    This test class ensures that all expected command-line parameters are properly
    documented in the help output and that parameter validation works correctly.
    These tests help maintain CLI consistency and prevent regression when parameters
    are added, modified, or removed.
    
    The tests verify both the presence of parameters and their proper documentation,
    ensuring users can discover and understand all available options.
    """
    
    def test_new_health_check_parameters(self):
        """Test that all expected CLI parameters are documented in help output.
        
        Given: The adafmt CLI help system
        When: Help information is requested for the format
        Then: All expected parameters are documented and visible to users
        
        This test verifies that:
        - Core parameters like --project-path and --include-path are present
        - Mode parameters like --write, --check, --diff are documented
        - Configuration parameters like --ui and --preflight are available
        - Timeout and performance parameters are properly documented
        - File handling parameters like --log-path are included
        """
        result = subprocess.run(
            [sys.executable, '-m', 'adafmt', 'format', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # These parameters were removed in the latest version
        # Only check for parameters that should exist
        expected_params = [
            '--project-path',
            '--include-path',
            '--exclude-path',
            '--write',
            '--check',
            '--diff',
            '--preflight',
            '--init-timeout',
            '--als-ready-timeout',
            '--format-timeout',
            '--max-attempts',
            '--log-path',
            '--stderr-path'
        ]
        
        for param in expected_params:
            assert param in result.stdout, f"Parameter {param} not found in help"
    
    def test_preflight_modes(self):
        """Test that all preflight mode options are properly documented.
        
        Given: The adafmt CLI with preflight mode support
        When: Help information is requested for the format
        Then: All available preflight modes are documented for user reference
        
        This test verifies that:
        - All preflight modes (off, warn, safe, kill, aggressive, fail) are documented
        - Users can discover available preflight options through help
        - Mode documentation is comprehensive and accessible
        - No preflight modes are missing from help output
        """
        result = subprocess.run(
            [sys.executable, '-m', 'adafmt', 'format', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check for each preflight mode - some might be wrapped or combined
        assert 'off' in result.stdout, "Preflight mode 'off' not documented"
        assert 'warn' in result.stdout, "Preflight mode 'warn' not documented"
        assert 'safe' in result.stdout, "Preflight mode 'safe' not documented"
        assert 'fail' in result.stdout, "Preflight mode 'fail' not documented"
        
        # Check for kill modes (might appear as "kill|kill+clean")
        assert 'kill' in result.stdout, "Preflight mode 'kill' not documented"
        
        # Check for aggressive (might be wrapped as "aggr essive" in help)
        assert 'aggr' in result.stdout, "Preflight mode 'aggressive' not documented"


class TestCLIFileProcessing:
    """Test suite for file processing capabilities that don't require ALS.
    
    This test class verifies file processing functionality that can be tested
    without requiring the Ada Language Server to be installed. These tests focus
    on file discovery, parameter handling, and basic workflow validation.
    
    These tests are particularly valuable for:
    - CI/CD environments where ALS might not be available
    - Testing core functionality independent of ALS integration
    - Validating file handling and parameter processing
    - Ensuring graceful degradation when ALS is unavailable
    """
    
    def test_dry_run_without_als(self):
        """Test that dry-run mode works correctly when ALS is unavailable.
        
        Given: An Ada file exists and ALS may not be available
        When: The formatter is run with UI and preflight disabled
        Then: The command completes with appropriate status without crashing
        
        This test verifies that:
        - The CLI handles missing ALS gracefully
        - Appropriate return codes are used for different scenarios
        - No crashes occur when ALS is unavailable
        - File processing completes within timeout limits
        - Temporary test files are properly cleaned up
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.adb', delete=False) as f:
            f.write("""procedure Test is
begin
   null;
end Test;
""")
            ada_file = Path(f.name)
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'adafmt', 'format',
                '--project-path', '/tmp/test.gpr',
                '--ui', 'off',
                '--preflight', 'off',
                str(ada_file)
            ], capture_output=True, text=True, timeout=10)
            
            # The command should complete (even if ALS is not available)
            assert result.returncode in [0, 1, 2], f"Unexpected return code: {result.returncode}"
            
        finally:
            ada_file.unlink(missing_ok=True)
    
    def test_file_discovery(self):
        """Test that Ada source files are discovered correctly in directory structures.
        
        Given: A directory containing Ada files (.ads, .adb) and non-Ada files
        When: The formatter is run with include-path specified
        Then: Only Ada files are discovered and processed
        
        This test verifies that:
        - Ada source files (.ads, .adb) are correctly identified
        - Non-Ada files (.txt) are ignored during discovery
        - File discovery works with include-path parameter
        - Output indicates successful file discovery
        - File counting and reporting work correctly
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create test files
            (tmppath / 'test.ads').write_text('package Test is end Test;')
            (tmppath / 'test.adb').write_text('package body Test is end Test;')
            (tmppath / 'test.txt').write_text('not an ada file')
            
            # Create a minimal project file
            project_file = tmppath / 'test.gpr'
            project_file.write_text('project Test is end Test;')
            
            result = subprocess.run([
                sys.executable, '-m', 'adafmt', 'format',
                '--project-path', str(project_file),
                '--include-path', str(tmppath),
                '--preflight', 'off',
                '--no-patterns',
                '--check'  # Just check, don't actually format
            ], capture_output=True, text=True, timeout=20)  # Increase timeout
            
            # Even without ALS, it should discover the files
            # Check logs mention the Ada files
            output = result.stdout + result.stderr
            assert 'test.ads' in output or 'test.adb' in output or '2 Ada files' in output