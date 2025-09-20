# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Utility functions for adafmt.

This module contains helper functions used throughout adafmt:
    - Path validation and manipulation
    - Atomic file writing
    - ALS process management
    - Datetime formatting

These utilities handle platform-specific operations and provide
safe, robust implementations of common tasks.
"""

from __future__ import annotations

import os
import signal
import sys
import tempfile
import shutil
import subprocess
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

def ensure_abs(p: str, flag: str) -> str:
    """Ensure a path is absolute, raising an error if not.

    This validation function helps catch configuration errors early
    by requiring absolute paths for critical parameters like project
    files and include/exclude paths.

    Args:
        p: Path string to validate
        flag: Parameter name for error message (e.g., "--project-file-path")

    Returns:
        The unchanged path if it's absolute

    Raises:
        ValueError: If the path is not absolute

    Example:
        >>> ensure_abs("/home/user/project.gpr", "--project-file-path")
        '/home/user/project.gpr'
        >>> ensure_abs("relative/path.gpr", "--project-file-path")
        ValueError: --project-file-path must be an absolute path: relative/path.gpr
    """
    if not os.path.isabs(p):
        raise ValueError(f"{flag} must be an absolute path: {p}")
    return p

def to_iso8601_basic(dt: datetime) -> str:
    """Convert a datetime to ISO 8601 BASIC format (YYYYMMDDTHHMMSSZ).

    Converts any timezone-aware datetime to UTC and formats it
    according to ISO 8601 BASIC format without fractional seconds.

    Args:
        dt: Timezone-aware datetime object

    Returns:
        String in format: 20250920T220311Z

    Raises:
        ValueError: If naive (timezone-unaware) datetime is provided

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 9, 20, 22, 3, 11, tzinfo=timezone.utc)
        >>> to_iso8601_basic(dt)
        '20250920T220311Z'
    """
    if dt.tzinfo is None:
        raise ValueError("Naive datetime provided; supply an aware datetime with tzinfo")
    else:
        dt_utc = dt.astimezone(timezone.utc)
    # format: 20250920T220311Z
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")

def atomic_write(path: str, data: str) -> None:
    """Write data to a file atomically.

    This function ensures that the file is either completely written
    or not modified at all, preventing partial writes or corruption.

    The atomic write process:
    1. Create parent directories if needed
    2. Write data to a temporary file in the same directory
    3. Atomically rename the temp file to the target path

    Args:
        path: Target file path
        data: String data to write

    Note:
        - The temporary file is created in the same directory as the target
          to ensure the rename operation is atomic (same filesystem)
        - Parent directories are created with default permissions
        - Uses UTF-8 encoding

    Example:
        >>> atomic_write("/tmp/config.toml", "key = 'value'\n")
        # File is written atomically, no partial content possible
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(target.parent)) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)  # Atomic rename on same filesystem

def list_als_pids() -> List[int]:
    """List process IDs of running Ada Language Server instances.

    Uses pgrep to find processes matching 'ada_language_server'.
    This works on macOS and most Unix-like systems.

    Returns:
        List of integer PIDs, empty list if none found or on error

    Note:
        - Uses 'pgrep -f' to match the full command line
        - Returns empty list on any error (pgrep not found, etc.)
        - Windows support would require a different implementation
          using psutil or WMI
    """
    # macOS/Unix: use pgrep
    try:
        out = subprocess.check_output(["pgrep", "-f", "ada_language_server"], text=True, timeout=5)
        return [int(x) for x in out.split()] if out.strip() else []
    except Exception:
        return []




# --- Enhanced preflight & hooks (cross-platform) ---

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore
    _HAS_PSUTIL = False

# Type alias for logger functions
LogFn = Optional[Callable[[str], None]]

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    cmdline: str
    user: Optional[str]
    age_minutes: float

    def is_stale(self, minutes: int = 30) -> bool:
        """Check if process is older than specified minutes."""
        return self.age_minutes >= minutes

def _current_username() -> str:
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return ""

def _als_processes(only_user: bool = True) -> List[ProcessInfo]:
    """Return list of ProcessInfo objects for running ALS processes."""
    username = _current_username()
    now = time.time()
    if _HAS_PSUTIL:
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline", "create_time", "username"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "ada_language_server" in name or "ada_language_server" in cmdline:
                    u = (proc.info.get("username") or "")
                    if (not only_user) or (not u or u == username):
                        ct = float(proc.info.get("create_time") or now)
                        age_minutes = max(0.0, (now - ct) / 60.0)
                        yield ProcessInfo(
                            pid=int(proc.info["pid"]),
                            cmdline=cmdline,
                            user=u or "",
                            age_minutes=age_minutes
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied):  # pragma: no cover
                continue
    else:
        # Fallback: use platform tools
        if sys.platform == "win32":
            try:
                out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq ada_language_server.exe"], text=True, stderr=subprocess.DEVNULL, timeout=5)
                for line in out.splitlines():
                    if "ada_language_server" in line.lower():
                        parts = [p for p in line.split() if p]
                        # columns vary; pid typically second token
                        try:
                            pid = int(parts[1])
                        except Exception:
                            continue
                        yield ProcessInfo(
                            pid=pid,
                            cmdline="ada_language_server.exe",
                            user="",
                            age_minutes=0.0
                        )
            except Exception:
                pass
        else:
            # Try different ps formats for different platforms
            ps_commands = [
                # Linux format
                ["ps", "ax", "-o", "pid,etimes,command"],
                # macOS/BSD format - use etime instead of etimes
                ["ps", "ax", "-o", "pid,etime,command"],
                # Fallback - just get pids and commands, no timing
                ["ps", "ax", "-o", "pid,command"]
            ]

            for ps_cmd in ps_commands:
                try:
                    out = subprocess.check_output(ps_cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
                    for line in out.splitlines()[1:]:
                        if "ada_language_server" in line and "grep" not in line:
                            try:
                                parts = line.strip().split(None, 2)
                                if len(parts) >= 2:
                                    pid = int(parts[0])
                                    # Try to parse time if available
                                    age_minutes = 0.0
                                    if len(parts) >= 3 and len(ps_cmd) > 3:  # Has time column
                                        time_str = parts[1]
                                        # Parse etime format (MM:SS or HH:MM:SS or DD-HH:MM:SS)
                                        if ':' in time_str:
                                            time_parts = time_str.split(':')
                                            if len(time_parts) == 2:  # MM:SS
                                                age_minutes = int(time_parts[0]) + int(time_parts[1]) / 60.0
                                            elif len(time_parts) == 3:  # HH:MM:SS
                                                age_minutes = int(time_parts[0]) * 60 + int(time_parts[1]) + int(time_parts[2]) / 60.0
                                        elif '-' in time_str:  # DD-HH:MM:SS
                                            day_time = time_str.split('-', 1)
                                            days = int(day_time[0])
                                            time_parts = day_time[1].split(':')
                                            age_minutes = days * 24 * 60 + int(time_parts[0]) * 60 + int(time_parts[1]) + int(time_parts[2]) / 60.0

                                    cmd = parts[-1] if len(parts) >= 2 else "ada_language_server"
                                    yield ProcessInfo(
                                        pid=pid,
                                        cmdline=cmd,
                                        user="",
                                        age_minutes=age_minutes
                                    )
                            except Exception:
                                continue
                    break  # Success, don't try other formats
                except Exception:
                    continue  # Try next format

def kill_als_processes(mode: str = "safe", stale_minutes: int = 30, logger=None, dry_run: bool=False) -> int:
    """Kill ALS processes per mode. Returns number killed. Modes:
       - 'safe' / 'kill': kill only processes older than stale_minutes (current user)
       - 'aggressive': kill all ALS for current user
       - 'off'/'none'/'warn'/'fail': handled by caller, this returns 0
    """
    if mode in ("off", "none", "warn", "fail"):
        return 0
    killed = 0
    only_user = True
    min_age = 0.0 if mode == "aggressive" else float(stale_minutes)
    for proc in list(_als_processes(only_user=only_user)):
        should = proc.age_minutes >= min_age
        if should:
            if logger:
                logger(f"[preflight] Killing ALS pid={proc.pid} age={proc.age_minutes:.1f}m cmd={proc.cmdline!r}" + (" [dry-run]" if dry_run else ""))
            if not dry_run:
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], check=False, timeout=5)
                    else:
                        os.kill(proc.pid, signal.SIGTERM)
                        time.sleep(0.3)
                        # If still alive, SIGKILL
                        try:
                            os.kill(proc.pid, 0)
                            os.kill(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    killed += 1
                except Exception as e:  # pragma: no cover
                    if logger:
                        logger(f"[preflight] Failed to kill {proc.pid}: {e}")
    return killed

def _iter_lock_dirs(search_paths: List[Path]):
    seen = set()
    for root in (search_paths or [Path.cwd()]):
        root = Path(root)
        if not root.exists():
            continue
        # Look for .als-lock directories
        for p in root.rglob(".als-lock"):
            try:
                p = p.resolve()
            except Exception:
                p = Path(p)
            if p.is_dir() and str(p) not in seen:
                seen.add(str(p))
                yield p
        # Also look for .als-alire lock files (created by ALS)
        for p in root.rglob(".als-alire"):
            try:
                p = p.resolve()
            except Exception:
                p = Path(p)
            if p.is_file() and str(p) not in seen:
                seen.add(str(p))
                yield p

def _pid_alive(pid: int) -> bool:
    try:
        if _HAS_PSUTIL:
            return psutil.pid_exists(pid)
        else:
            if sys.platform == "win32":
                out = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}"], text=True, stderr=subprocess.DEVNULL, timeout=5)
                return str(pid) in out
            else:
                os.kill(pid, 0)
                return True
    except Exception:
        return False

def find_stale_locks(search_paths: List[Path], ttl_minutes: int = 10) -> List[Path]:
    now = time.time()
    stale = []
    for lock_path in _iter_lock_dirs(search_paths):
        try:
            age_min = (now - lock_path.stat().st_mtime) / 60.0
        except Exception:
            age_min = float("inf")

        # For directories, check for pid file
        if lock_path.is_dir():
            pid_file = lock_path / "pid"
            active = False
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    active = _pid_alive(pid)
                except Exception:
                    active = False
            if (not active) and age_min >= float(ttl_minutes):
                stale.append(lock_path)
        # For files (.als-alire), just check age
        elif lock_path.is_file() and age_min >= float(ttl_minutes):
            stale.append(lock_path)
    return stale

def clean_stale_locks(search_paths: List[Path], ttl_minutes: int = 10, logger=None, dry_run: bool=False) -> int:
    removed = 0
    for lock_path in find_stale_locks(search_paths, ttl_minutes=ttl_minutes):
        if logger:
            logger(f"[preflight] Removing stale lock: {lock_path}" + (" [dry-run]" if dry_run else ""))
        if not dry_run:
            try:
                if lock_path.is_dir():
                    shutil.rmtree(lock_path, ignore_errors=False)
                else:
                    lock_path.unlink()
                removed += 1
            except Exception as e:  # pragma: no cover
                if logger:
                    logger(f"[preflight] Failed to remove {lock_path}: {e}")
    return removed


def run_hook(hook_cmd: Optional[str], phase: str, logger=None, timeout: int=60, dry_run: bool=False) -> bool:
    if not hook_cmd:
        return True

    # Parse command safely without shell
    import shlex
    try:
        cmd_list = shlex.split(hook_cmd)
    except ValueError as e:
        if logger:
            logger(f"[{phase}-hook] Invalid command format: {e}")
        return False

    if logger:
        # Log the command as parsed list for transparency
        logger(f"[{phase}-hook] {' '.join(cmd_list)}" + (" [dry-run]" if dry_run else ""))
    if dry_run:
        return True
    try:
        # Execute without shell for security
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout, check=False)
        if result.stdout and logger:
            for line in result.stdout.strip().splitlines():
                logger(f"[{phase}-hook] {line}")
        if result.stderr and logger:
            for line in result.stderr.strip().splitlines():
                logger(f"[{phase}-hook] [stderr] {line}")
        if result.returncode != 0:
            if logger:
                logger(f"[{phase}-hook] exited with code {result.returncode}")
            return False
        return True
    except subprocess.TimeoutExpired:
        if logger:
            logger(f"[{phase}-hook] timeout after {timeout}s")
        return False
    except Exception as e:  # pragma: no cover
        if logger:
            logger(f"[{phase}-hook] error: {e}")
        return False

def preflight(
    mode: str = "safe",
    als_stale_minutes: int = 30,
    lock_ttl_minutes: int = 10,
    search_paths: Optional[List[Path]] = None,
    logger=None,
    dry_run: bool=False,
) -> int:
    """Preflight environment for formatting.
       Returns 0 on success, non-zero to abort.
    """
    mp = (mode or "").lower()
    if mp in ("off", "none"):
        return 0


    # Report counts
    als_pids = list(_als_processes(only_user=True))
    locks = list(find_stale_locks(search_paths or [Path.cwd()], ttl_minutes=lock_ttl_minutes))
    if logger:
        logger(f"[preflight] ALS processes (user): {len(als_pids)}; stale locks: {len(locks)}")

    if mp == "warn":
        return 0
    if mp == "fail":
        if als_pids or locks:
            if logger:
                logger("[preflight] Conflicts found; aborting due to --preflight=fail")
            return 2
        return 0

    # Kill processes
    kill_als_processes(
        mode="aggressive" if mp == "aggressive" else "safe",
        stale_minutes=als_stale_minutes,
        logger=logger,
        dry_run=dry_run,
    )

    # Clean locks if requested
    if mp in ("kill+clean", "aggressive"):
        removed = clean_stale_locks(search_paths or [Path.cwd()], ttl_minutes=lock_ttl_minutes, logger=logger, dry_run=dry_run)
        if logger and removed:
            logger(f"[preflight] Removed {removed} stale ALS locks")

    return 0


# --- New function for traces config parsing ---

def extract_log_path_from_traces_cfg(cfg_path: str) -> Optional[str]:
    """Extract the log file path from a GNATCOLL traces config file.

    Looks for lines starting with '>' which indicate log file paths.
    Handles both absolute and relative paths (relative to config location).

    Args:
        cfg_path: Path to the traces config file

    Returns:
        Resolved absolute path to the log file, or None if not found

    Example config line:
        >/tmp/als.log:buffer_size=0
        >als.log:buffer_size=0
    """
    import re

    traces_line_pattern = re.compile(r'^\s*>\s*((?:[A-Za-z]:)?[^:]*?)(?::.*)?\s*')

    try:
        p = Path(cfg_path).expanduser().resolve()
        if not p.exists():
            return None

        with p.open('r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if not line.lstrip().startswith('>'):
                    continue

                m = traces_line_pattern.match(line)
                if not m:
                    continue

                raw = m.group(1).strip()
                logp = (p.parent / raw) if not Path(raw).is_absolute() else Path(raw)
                return str(logp.expanduser().resolve())

    except Exception:
        return None

    return None
