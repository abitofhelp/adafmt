# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Run setup and initialization for the Ada formatter."""

from pathlib import Path
from typing import Optional, Any

from .utils import run_hook, preflight


def execute_pre_hook(
    pre_hook: Optional[str],
    hook_timeout: float,
    ui: Optional[Any] = None
) -> bool:
    """
    Execute pre-hook if provided.
    
    Args:
        pre_hook: Command to run before formatting
        hook_timeout: Timeout in seconds
        ui: UI instance for logging
        
    Returns:
        True if hook succeeded or not provided, False if failed
    """
    if pre_hook:
        ok = run_hook(
            pre_hook, "pre", 
            logger=(ui.log_line if ui else print), 
            timeout=int(hook_timeout), 
            dry_run=False
        )
        if not ok:
            if ui:
                ui.log_line("[error] pre-hook failed; aborting.")
            else:
                print("[error] pre-hook failed; aborting.")
            return False
    return True


def run_preflight_checks(
    project_path: Path,
    preflight_mode: str,
    als_stale_minutes: int,
    ui: Optional[Any] = None
) -> int:
    """
    Run preflight checks for ALS processes and locks.
    
    Args:
        project_path: Path to project file
        preflight_mode: Preflight mode setting
        als_stale_minutes: Age threshold for stale processes
        ui: UI instance for logging
        
    Returns:
        0 if successful, non-zero error code if failed
    """
    if preflight_mode not in ("off", "none"):
        project_root = project_path.parent
        return preflight(
            mode=preflight_mode.replace("+", ""),  # Handle kill+clean
            als_stale_minutes=als_stale_minutes,
            lock_ttl_minutes=10,  # default
            search_paths=[project_root],
            logger=(ui.log_line if ui else print),
            dry_run=False,
        )
    return 0