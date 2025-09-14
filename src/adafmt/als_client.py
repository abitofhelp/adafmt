# =============================================================================
# adafmt - Ada Language Formatter
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# Licensed under the MIT License. See LICENSE file in the project root.
# =============================================================================

"""Ada Language Server (ALS) client implementation.

This module provides an asynchronous client for communicating with the Ada
Language Server using JSON-RPC over stdio. It implements the Language Server
Protocol (LSP) for formatting Ada source code.

The client supports:
    - Async communication using JSON-RPC over stdin/stdout
    - Proper error handling and cleanup
    - Request/response correlation with timeouts

Typical usage:
    client = ALSClient(project_file=Path("project.gpr"))
    await client.start()
    try:
        # Use client for formatting
        result = await client.request_with_timeout({...}, timeout=30)
    finally:
        await client.shutdown()
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
import shlex
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Any, Dict, Optional, Tuple

from .utils import extract_log_path_from_traces_cfg

JsonDict = Dict[str, Any]
"""Type alias for JSON-compatible dictionaries used in LSP messages."""


class ALSProtocolError(RuntimeError):
    """Exception raised when ALS returns an error response.
    
    This exception wraps Language Server Protocol errors returned by ALS,
    such as syntax errors in Ada code or unsupported operations.
    
    Attributes:
        payload: The error object from the JSON-RPC response, typically
                containing 'code', 'message', and optional 'data' fields.
                
    Common error codes:
        -32803: GNATFORMAT error for syntactically invalid Ada code
        -32800: Request cancelled
        -32601: Method not found
    """
    def __init__(self, payload: JsonDict):
        super().__init__(str(payload))
        self.payload = payload


def _has_cmd(cmd: str) -> bool:
    """Check if a command is available in the system PATH.
    
    Args:
        cmd: Command name to check (e.g., 'ada_language_server')
        
    Returns:
        True if the command is found in PATH, False otherwise
        
    Note:
        This uses shutil.which() which respects the PATHEXT environment
        variable on Windows for executable extensions.
    """
    return which(cmd) is not None


def _timestamp() -> str:
    """Generate ISO timestamp for stderr logging.
    
    Returns:
        ISO 8601 formatted timestamp with second precision
        Example: "2025-09-12T14:30:45"
    """
    return dt.datetime.now().isoformat(timespec="seconds")


def build_als_command(traces_config: Optional[str] = None) -> Tuple[str, dict]:
    """Build the command line and environment for launching ALS.
    
    Args:
        traces_config: Optional path to GNATCOLL traces config file
                
    Returns:
        Tuple of (command_line, environment_dict) where:
        - command_line: Full command to execute ("ada_language_server")
        - environment_dict: Copy of current environment variables
    """
    cmd = "ada_language_server"
    env = os.environ.copy()
    
    # Add traces config if provided
    if traces_config:
        cmd += f" --tracefile={traces_config}"

    return cmd, env


@dataclass
class ALSClient:
    """Asynchronous client for Ada Language Server communication.
    
    This client manages the lifecycle of an ALS process and provides
    methods for JSON-RPC communication following the Language Server Protocol.
    
    Attributes:
        project_file: Path to the GPR project file for Ada compilation
        stderr_file_path: Optional path for ALS stderr log file
        logger: Optional logger function for debug output
        process: The ALS subprocess once started
        als_log_path: Path to ALS log file (populated after initialization)
        
    Internal attributes:
        _reader_task: Background task reading ALS responses
        _stderr_task: Background task for stderr capture
        _pending: Map of request IDs to Future objects for response correlation
        _id: Counter for generating unique request IDs
        _launch_cmd: Command used to start ALS (for debugging)
        _launch_cwd: Working directory used for ALS (for debugging)
        _stderr_lines: Count of stderr lines captured
        _start_ns: Process start time in nanoseconds
        _end_ns: Process end time in nanoseconds
        _returncode: Process exit code
        _stderr_log_path: Resolved path to stderr log file
    """
    project_file: Path
    stderr_file_path: Optional[Path] = None
    logger: Optional[Any] = None
    als_traces_config_path: Optional[str] = None
    als_log_path: Optional[str] = None
    init_timeout: float = 180.0
    process: Optional[asyncio.subprocess.Process] = None
    _reader_task: Optional[asyncio.Task] = None
    _stderr_task: Optional[asyncio.Task] = None
    _pending: Dict[str, asyncio.Future] = field(default_factory=dict)
    _id: int = 0
    _launch_cmd: Optional[str] = None
    _launch_cwd: Optional[str] = None
    _stderr_lines: int = 0
    _start_ns: Optional[int] = None
    _end_ns: Optional[int] = None
    _returncode: Optional[int] = None
    _stderr_log_path: Optional[Path] = None

    def _resolve_stderr_path(self, cwd: Path | None) -> Path:
        """Resolve the final stderr log file path.
        
        Determines where to write ALS stderr output based on user preferences
        and the current working directory.
        
        Args:
            cwd: Working directory
            
        Returns:
            Resolved absolute path for the stderr log file
            
        Logic:
            - If user provided stderr_file_path:
                * absolute: use as-is
                * relative starting with ./: resolve from current working directory
                * other relative: resolve against base directory
            - Else: <base>/als_stderr.log
            - Base = cwd if provided, else current directory
        """
        base = cwd or Path.cwd()
        if self.stderr_file_path:
            # Always use the path as provided if it's absolute
            if self.stderr_file_path.is_absolute():
                return self.stderr_file_path
            # For relative paths, use current working directory
            return Path.cwd() / self.stderr_file_path
        return base / "als_stderr.log"

    async def _pump_stderr(self, stream: asyncio.StreamReader, log_path: Path) -> None:
        """Capture stderr to file with timestamps, also mirror to logger.
        
        Runs as a background task, reading lines from ALS stderr and writing
        them to a log file with timestamps. Also sends them to the configured
        logger for real-time display.
        
        Args:
            stream: Async stream reader connected to ALS stderr
            log_path: Path where stderr should be logged
            
        Note:
            - Creates parent directories if needed
            - Each line is prefixed with ISO timestamp
            - Lines are flushed immediately for real-time monitoring
            - Increments _stderr_lines counter for metrics
        """
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            while not stream.at_eof():
                chunk = await stream.readline()
                if not chunk:
                    break
                line = chunk.decode(errors="replace").rstrip("\n")
                stamped = f"{_timestamp()} | {line}\n"
                f.write(stamped)
                f.flush()
                
                # Filter out ALS progress indicators that look like "##O=#" or similar patterns
                if self.logger and not (line.strip() and all(c in "#=-O " for c in line)):
                    self.logger(f"[als][stderr] {line}")
                
                self._stderr_lines += 1

    async def start(self) -> None:
        """Start the Ada Language Server process.
        
        This method:
        1. Spawns the ALS subprocess with proper environment
        2. Sends LSP initialize request
        3. Starts background task to read responses
        
        Raises:
            OSError: If ALS executable cannot be found or started
            
        Note:
            After start(), the client is ready to handle LSP requests.
            Always call shutdown() when done to clean up resources.
        """
        # Anchor to project directory to prevent VFS errors
        cwd = str(self.project_file.parent)

        # Build the command
        cmdline, env = build_als_command(self.als_traces_config_path)
        self._launch_cmd = cmdline
        self._launch_cwd = cwd or "."
        
        # Parse traces config early if provided to set als_log_path
        if self.als_traces_config_path and not self.als_log_path:
            parsed_log = extract_log_path_from_traces_cfg(self.als_traces_config_path)
            if parsed_log:
                self.als_log_path = parsed_log
                if self.logger:
                    self.logger(f"[als] Parsed log path from traces config: {parsed_log}")
            elif self.logger:
                self.logger("[als] Warning: Could not parse log path from traces config")

        # Spawn ALS
        self._start_ns = time.perf_counter_ns()
        self.process = await asyncio.create_subprocess_exec(
            *shlex.split(cmdline),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,  # ← the fix
        )
        self._reader_task = asyncio.create_task(self._reader_loop())
        
        # Start stderr capture task
        # This runs in background, writing timestamped stderr lines to log file
        stderr_path = self._resolve_stderr_path(Path(cwd) if cwd else None)
        self._stderr_log_path = stderr_path
        
        # Ensure stderr directory exists
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.process.stderr:
            self._stderr_task = asyncio.create_task(self._pump_stderr(self.process.stderr, stderr_path))

        # Initialize with proper workspace info to prevent "NO_PROJECT" fallback
        project_dir = self.project_file.parent.resolve()
        init_response = await self.request_with_timeout({
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": project_dir.as_uri(),
                "workspaceFolders": [
                    {
                        "uri": project_dir.as_uri(),
                        "name": project_dir.name
                    }
                ],
                "capabilities": {},
                "initializationOptions": {
                    "ada": {
                        "projectFile": str(self.project_file),
                        "scenarioVariables": {},
                        "projectDiagnostics": False,
                        "alireDiagnostics": False,
                        "enableIndexing": False
                    }
                },
            },
        }, timeout=self.init_timeout)
        
        # Check if ALS returns log info in the initialize response
        if init_response and isinstance(init_response, dict):
            # Some LSP servers return server info with log paths
            server_info = init_response.get("serverInfo", {})
            if self.logger and server_info:
                self.logger(f"[als] Server info: {server_info}")
        
        await self._notify("initialized", {})
        # no special warmup here; caller may handle readiness

    async def restart(self) -> None:
        """Restart the ALS process.
        
        Performs a complete shutdown and restart cycle. Useful for
        recovering from ALS crashes or clearing corrupted state.
        
        This is typically called after connection errors or when ALS
        becomes unresponsive.
        """
        await self.shutdown()
        await self.start()

    async def shutdown(self) -> None:
        """Gracefully shut down the ALS process.
        
        Attempts a clean shutdown by:
        1. Sending LSP 'shutdown' request
        2. Sending LSP 'exit' notification
        3. Cancelling the reader task
        4. Terminating the process (with fallback to kill)
        
        All errors are suppressed to ensure cleanup completes even
        if ALS is already dead or unresponsive.
        """
        # Try a clean shutdown; tolerate any errors.
        with contextlib.suppress(Exception):
            await self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "shutdown", "params": None})
            await self._notify("exit", {})

        if self._reader_task:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._reader_task
                
        if self._stderr_task:
            self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._stderr_task

        if self.process:
            with contextlib.suppress(ProcessLookupError):
                self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2)
            except Exception:
                with contextlib.suppress(ProcessLookupError):
                    self.process.kill()
            self.process = None

    # --------------- JSON-RPC plumbing ---------------
    def _next_id(self) -> str:
        """Generate the next unique request ID.
        
        Returns:
            String ID for JSON-RPC request correlation
        """
        self._id += 1
        return str(self._id)

    async def _notify(self, method: str, params: Any) -> None:
        """Send a JSON-RPC notification (no response expected).
        
        Args:
            method: LSP method name (e.g., 'textDocument/didOpen')
            params: Method parameters as JSON-serializable object
            
        Note:
            Notifications don't have an ID and don't expect a response.
        """
        await self._write({"jsonrpc": "2.0", "method": method, "params": params})

    async def _send(self, msg: JsonDict) -> None:
        """Send a JSON-RPC message and prepare for response if needed.
        
        Args:
            msg: Complete JSON-RPC message dictionary
            
        Note:
            If the message has an 'id', creates a Future to track
            the response. The Future will be resolved when the
            response arrives in _reader_loop.
        """
        await self._write(msg)
        if "id" in msg:
            fut = asyncio.get_running_loop().create_future()
            self._pending[str(msg["id"])] = fut

    async def request_with_timeout(self, msg: JsonDict, timeout: float) -> Any:
        """Send a request and wait for response with timeout.
        
        Args:
            msg: JSON-RPC request containing 'method' and 'params'
            timeout: Maximum seconds to wait for response
            
        Returns:
            The 'result' field from the JSON-RPC response
            
        Raises:
            asyncio.TimeoutError: If no response within timeout
            ALSProtocolError: If ALS returns an error response
            
        Example:
            result = await client.request_with_timeout({
                "method": "textDocument/formatting",
                "params": {"textDocument": {"uri": "file:///..."}}
            }, timeout=30)
        """
        mid = self._next_id()
        msg["id"] = mid
        await self._send(msg)
        fut = self._pending[mid] = asyncio.get_running_loop().create_future()
        return await asyncio.wait_for(fut, timeout=timeout)

    async def _write(self, msg: JsonDict) -> None:
        """Write a JSON-RPC message to ALS stdin.
        
        Formats the message according to LSP specification:
        - HTTP-like header with Content-Length
        - Empty line (CRLF)
        - JSON body in UTF-8
        
        Args:
            msg: JSON-RPC message to send
            
        Note:
            The assert ensures we don't try to write to a dead process.
            In production, this should be a proper check with error handling.
        """
        assert self.process and self.process.stdin
        data = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
        self.process.stdin.write(header + data)
        await self.process.stdin.drain()

    async def _reader_loop(self) -> None:
        """Background task that reads responses from ALS stdout.
        
        Continuously reads LSP messages from ALS and correlates responses
        with pending requests. Runs until the process dies or is cancelled.
        
        The LSP wire format is:
        - Header line: "Content-Length: <bytes>\r\n"
        - Empty line: "\r\n"
        - JSON body of specified length
        
        When a response arrives:
        - If it has an 'error', the waiting Future gets ALSProtocolError
        - If it has a 'result', the waiting Future gets the result value
        - Notifications (no 'id') are currently ignored
        """
        assert self.process and self.process.stdout
        r = self.process.stdout
        while True:
            # Read LSP header
            header = await r.readline()
            if not header:
                break
            if not header.startswith(b"Content-Length:"):
                continue
            length = int(header.split(b":")[1].strip())
            await r.readline()  # CRLF
            payload = await r.readexactly(length)
            msg = json.loads(payload.decode("utf-8"))
            if "id" in msg and ("result" in msg or "error" in msg):
                mid = str(msg["id"])
                fut = self._pending.pop(mid, None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(ALSProtocolError(msg["error"]))
                    else:
                        fut.set_result(msg["result"])
        # end reader

    async def wait(self) -> int:
        """Wait for ALS process to complete and return exit code.
        
        Waits for the ALS process to terminate and ensures the stderr
        capture task completes. Records timing metrics for summary.
        
        Returns:
            Process exit code (0 for success, non-zero for errors)
            
        Note:
            - Updates _end_ns and _returncode for summary()
            - Gives stderr capture task up to 2 seconds to finish
            - Should be called instead of process.wait() to ensure
              proper cleanup and metric collection
        """
        rc = await self.process.wait() if self.process else 0
        if self._stderr_task:
            try:
                await asyncio.wait_for(self._stderr_task, timeout=2)
            except asyncio.TimeoutError:
                if self.logger:
                    self.logger("[als] stderr pump timeout on shutdown")
        self._end_ns = time.perf_counter_ns()
        self._returncode = rc
        return rc

    def summary(self) -> dict:
        """Return a concise run summary suitable for UI/console display.
        
        Provides metrics about the ALS process execution for reporting
        and debugging purposes.
        
        Returns:
            Dictionary containing:
            - returncode: Process exit code (None if still running)
            - duration_ms: Total run time in milliseconds (None if not completed)
            - stderr_lines: Number of stderr lines captured
            - stderr_log_path: Path to stderr log file (as string)
            
        Example:
            >>> summary = client.summary()
            >>> print(f"ALS ran for {summary['duration_ms']:.1f}ms")
            >>> print(f"Stderr: {summary['stderr_lines']} lines at {summary['stderr_log_path']}")
        """
        dur_ms: float | None = None
        if self._start_ns is not None and self._end_ns is not None:
            dur_ms = (self._end_ns - self._start_ns) / 1_000_000.0
        return {
            "returncode": self._returncode,
            "duration_ms": dur_ms,
            "stderr_lines": self._stderr_lines,
            "stderr_log_path": str(self._stderr_log_path) if self._stderr_log_path else None,
        }