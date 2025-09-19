# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""ALS client initialization and setup for the Ada formatter."""

import asyncio
from pathlib import Path
from typing import Optional, Any

from .als_client import ALSClient
from .metrics import MetricsCollector


async def initialize_als_client(
    project_file: Path,
    no_als: bool,
    stderr_path: Optional[Path],
    init_timeout: int,
    warmup_seconds: int,
    metrics: MetricsCollector,
    ui: Optional[Any] = None
) -> Optional[ALSClient]:
    """
    Initialize and start the Ada Language Server client.
    
    Args:
        project_file: Path to GNAT project file
        no_als: If True, skip ALS initialization
        stderr_path: Path for ALS stderr output
        init_timeout: Timeout for ALS initialization
        warmup_seconds: Seconds to wait after ALS starts
        metrics: Metrics collector instance
        ui: UI instance for logging
        
    Returns:
        Initialized ALS client or None if --no-als
    """
    client = None
    
    if not no_als:
        metrics.start_timer('als_startup')
        als_start_success = False
        try:
            client = ALSClient(
                project_file=project_file, 
                stderr_file_path=stderr_path,
                init_timeout=init_timeout,
                logger=ui.log_line if ui else print
            )
            await client.start()
            als_start_success = True
        finally:
            startup_duration = metrics.end_timer('als_startup')
            metrics.record_als_startup(startup_duration, als_start_success, str(project_file))
        
        # Add warmup delay after start
        if warmup_seconds > 0:
            if ui:
                ui.log_line(f"[als] Warming up for {warmup_seconds} seconds...")
            else:
                print(f"[als] Warming up for {warmup_seconds} seconds...")
            await asyncio.sleep(warmup_seconds)
            
        # Echo launch context for debugging
        launch_msg = f"[als] cwd={client._launch_cwd} cmd={client._launch_cmd}"
        if ui:
            ui.log_line(launch_msg)
        else:
            print(launch_msg)
        
        # Display log paths early so users know where to find them
        if ui:
            ui.log_line(f"[als] ALS log: {client.als_log_path or '~/.als/ada_ls_log.*.log (default location)'}")
            ui.log_line(f"[als] Stderr log: {client._stderr_log_path}")
        else:
            print(f"[als] ALS log: {client.als_log_path or '~/.als/ada_ls_log.*.log (default location)'}")
            print(f"[als] Stderr log: {client._stderr_log_path}")
            
    else:
        if ui:
            ui.log_line("[als] ALS formatting disabled (--no-als)")
        else:
            print("[als] ALS formatting disabled (--no-als)")
            
    return client