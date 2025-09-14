"""Shared pytest configuration and fixtures for adafmt test suite.

This module provides common fixtures, configuration, and utilities used across
all test modules. Fixtures defined here are automatically available to all tests
without explicit imports.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Generator, List, Any
from unittest.mock import Mock, MagicMock

import pytest

# Add src to path for imports during testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adafmt.als_client import ALSClient
from adafmt.logging_jsonl import JsonlLogger


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may require ALS)"
    )
    config.addinivalue_line(
        "markers", "requires_als: mark test as requiring ALS installation"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (>1 second execution time)"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as performance benchmark"
    )


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_ada_file(tmp_path: Path) -> Path:
    """Create a temporary Ada file with basic content.
    
    Returns:
        Path to a temporary .adb file containing a simple procedure.
    """
    file_path = tmp_path / "test_procedure.adb"
    file_path.write_text("""procedure Test_Procedure is
begin
   null;
end Test_Procedure;
""")
    return file_path


@pytest.fixture
def temp_ada_spec(tmp_path: Path) -> Path:
    """Create a temporary Ada specification file.
    
    Returns:
        Path to a temporary .ads file containing a package spec.
    """
    file_path = tmp_path / "test_package.ads"
    file_path.write_text("""package Test_Package is
   procedure Do_Something;
   function Calculate (X : Integer) return Integer;
end Test_Package;
""")
    return file_path


@pytest.fixture
def temp_project_file(tmp_path: Path) -> Path:
    """Create a temporary GNAT project file.
    
    Returns:
        Path to a temporary .gpr file with minimal configuration.
    """
    file_path = tmp_path / "test_project.gpr"
    file_path.write_text("""project Test_Project is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Main use ("main.adb");
end Test_Project;
""")
    return file_path


@pytest.fixture
def ada_project_structure(tmp_path: Path) -> Path:
    """Create a complete Ada project structure for testing.
    
    Creates:
        - Project file (test.gpr)
        - Source directory with multiple Ada files
        - Object directory
        - Test files with various formatting issues
    
    Returns:
        Path to the project root directory.
    """
    # Create directories
    (tmp_path / "src").mkdir()
    (tmp_path / "obj").mkdir()
    (tmp_path / "tests").mkdir()
    
    # Create project file
    gpr_content = """project Test is
   for Source_Dirs use ("src", "tests");
   for Object_Dir use "obj";
   for Main use ("main.adb");
end Test;
"""
    (tmp_path / "test.gpr").write_text(gpr_content)
    
    # Create source files
    (tmp_path / "src" / "main.adb").write_text("""procedure Main is
   X:Integer:=1;  -- Needs formatting
begin
   if X>0 then
      null;
   end if;
end Main;
""")
    
    (tmp_path / "src" / "utils.ads").write_text("""package Utils is
   function Add(A,B:Integer)return Integer;  -- Needs spacing
end Utils;
""")
    
    (tmp_path / "src" / "utils.adb").write_text("""package body Utils is
   function Add(A,B:Integer)return Integer is
   begin
      return A+B;  -- Needs spacing
   end Add;
end Utils;
""")
    
    return tmp_path


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_als_client() -> Mock:
    """Create a mock ALS client for unit testing.
    
    Returns:
        Mock ALSClient with common method stubs.
    """
    client = Mock(spec=ALSClient)
    client.format_file.return_value = []
    client.start = Mock(return_value=None)
    client.shutdown = Mock(return_value=None)
    client.is_running = Mock(return_value=True)
    return client


@pytest.fixture
def mock_logger() -> Mock:
    """Create a mock JSONL logger for testing.
    
    Returns:
        Mock JsonlLogger with all logging methods stubbed.
    """
    logger = Mock(spec=JsonlLogger)
    logger.info = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.metric = Mock()
    logger.exception = Mock()
    return logger


@pytest.fixture
def mock_subprocess() -> MagicMock:
    """Create a mock subprocess.Popen for testing process interaction.
    
    Returns:
        MagicMock configured to simulate a running process.
    """
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process is running
    mock_process.returncode = None
    mock_process.pid = 12345
    mock_process.stdout = MagicMock()
    mock_process.stdin = MagicMock()
    mock_process.stderr = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.wait = MagicMock(return_value=0)
    return mock_process


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests.
    
    This fixture is required for pytest-asyncio to work properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_als_client(temp_project_file: Path, mock_logger: Mock) -> AsyncMock:
    """Create an async mock ALS client.
    
    Returns:
        AsyncMock configured for async/await testing.
    """
    from unittest.mock import AsyncMock
    
    client = AsyncMock(spec=ALSClient)
    client.format_file.return_value = []
    client.start.return_value = None
    client.shutdown.return_value = None
    return client


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_edits() -> List[dict]:
    """Provide sample LSP TextEdit objects for testing.
    
    Returns:
        List of edit dictionaries in LSP format.
    """
    return [
        {
            "range": {
                "start": {"line": 1, "character": 5},
                "end": {"line": 1, "character": 6}
            },
            "newText": " : "
        },
        {
            "range": {
                "start": {"line": 1, "character": 15},
                "end": {"line": 1, "character": 16}
            },
            "newText": " := "
        }
    ]


@pytest.fixture
def lsp_initialize_response() -> dict:
    """Provide a mock LSP initialize response.
    
    Returns:
        Dictionary simulating ALS capabilities response.
    """
    return {
        "capabilities": {
            "textDocumentSync": 2,
            "documentFormattingProvider": True,
            "documentRangeFormattingProvider": True,
            "documentOnTypeFormattingProvider": {
                "firstTriggerCharacter": ";",
                "moreTriggerCharacter": ["\n"]
            }
        },
        "serverInfo": {
            "name": "Ada Language Server",
            "version": "24.0.0"
        }
    }


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def isolated_environment(monkeypatch) -> None:
    """Provide an isolated environment for testing.
    
    Clears environment variables that might affect tests.
    """
    # Clear environment variables that might interfere
    env_vars_to_clear = [
        "ALS_HOME",
        "GPR_PROJECT_PATH", 
        "ADA_PROJECT_PATH",
        "LIBRARY_TYPE",
        "CI",
        "GITHUB_ACTIONS"
    ]
    
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def ci_environment(monkeypatch) -> None:
    """Simulate a CI environment for testing CI-specific behavior."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def capture_logs(tmp_path: Path) -> Path:
    """Create a temporary log file for capturing test logs.
    
    Returns:
        Path to temporary JSONL log file.
    """
    log_path = tmp_path / "test_debug.jsonl"
    return log_path


@pytest.fixture
def als_available() -> bool:
    """Check if ALS is available on the system.
    
    Returns:
        True if ada_language_server is in PATH.
    """
    import shutil
    return shutil.which("ada_language_server") is not None


@pytest.fixture
def skip_if_no_als(als_available: bool) -> None:
    """Skip test if ALS is not available."""
    if not als_available:
        pytest.skip("ALS (ada_language_server) not available")


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def large_ada_file(tmp_path: Path) -> Path:
    """Create a large Ada file for performance testing.
    
    Returns:
        Path to Ada file with 1000+ lines.
    """
    file_path = tmp_path / "large_package.adb"
    
    lines = ["package body Large_Package is\n"]
    
    # Generate many procedures
    for i in range(100):
        lines.extend([
            f"   procedure Proc_{i} is\n",
            "      X : Integer := 0;\n",
            "   begin\n",
            "      for I in 1 .. 100 loop\n",
            "         X := X + I;\n",
            "      end loop;\n",
            f"   end Proc_{i};\n\n"
        ])
    
    lines.append("end Large_Package;\n")
    
    file_path.write_text("".join(lines))
    return file_path


@pytest.fixture
def many_small_files(tmp_path: Path) -> List[Path]:
    """Create many small Ada files for batch testing.
    
    Returns:
        List of paths to 50 small Ada files.
    """
    files = []
    for i in range(50):
        file_path = tmp_path / f"unit_{i}.adb"
        file_path.write_text(f"""procedure Unit_{i} is
   X : Integer := {i};
begin
   null;
end Unit_{i};
""")
        files.append(file_path)
    return files