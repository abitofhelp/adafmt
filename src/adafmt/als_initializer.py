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
from .logging_jsonl import JsonlLogger


async def initialize_als_client(
    project_file: Path,
    no_als: bool,
    stderr_path: Optional[Path],
    init_timeout: int,
    als_ready_timeout: int,
    metrics: MetricsCollector,
    ui: Optional[Any] = None,
    debug_logger: Optional[JsonlLogger] = None
) -> Optional[ALSClient]:
    """
    Initialize and start the Ada Language Server client.
    
    Args:
        project_file: Path to GNAT project file
        no_als: If True, skip ALS initialization
        stderr_path: Path for ALS stderr output
        init_timeout: Timeout for ALS initialization
        als_ready_timeout: Maximum seconds to wait for ALS to become ready
        metrics: Metrics collector instance
        ui: UI instance for logging
        debug_logger: Optional debug logger for ALS operations
        
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
                logger=ui.log_line if ui else print,
                debug_logger=debug_logger
            )
            await client.start()
            als_start_success = True
        finally:
            startup_duration = metrics.end_timer('als_startup')
            metrics.record_als_startup(startup_duration, als_start_success, str(project_file))
        
        # Readiness probe: Send dummy requests until ALS is fully initialized
        # This replaces the fixed warmup delay with actual readiness detection
        if ui:
            ui.log_line("[als] Verifying ALS readiness...")
        else:
            print("[als] Verifying ALS readiness...")
            
        # Create a minimal Ada source for readiness check
        dummy_ada_source = """package Dummy is
   procedure Test;
end Dummy;"""
        
        dummy_uri = "file:///tmp/adafmt_readiness_probe.ads"
        
        # Retry readiness check with exponential backoff
        max_retries = max(1, als_ready_timeout // 5) if als_ready_timeout > 0 else 3  # Use timeout to determine retries
        retry_delay = 2.0  # Start with 2 second delay
        
        for attempt in range(max_retries):
            try:
                # Open dummy file
                await client._notify("textDocument/didOpen", {
                    "textDocument": {
                        "uri": dummy_uri,
                        "languageId": "ada",
                        "version": 1,
                        "text": dummy_ada_source
                    }
                })
                
                # Try formatting with extended timeout for first request
                await client.request_with_timeout({
                    "method": "textDocument/formatting",
                    "params": {
                        "textDocument": {"uri": dummy_uri},
                        "options": {"tabSize": 3, "insertSpaces": True}
                    }
                }, timeout=60)  # Longer timeout for first request
                
                # Close dummy file
                await client._notify("textDocument/didClose", {
                    "textDocument": {"uri": dummy_uri}
                })
                
                if ui:
                    ui.log_line("[als] ALS is ready for formatting")
                else:
                    print("[als] ALS is ready for formatting")
                break  # Success!
                
            except Exception as e:
                if attempt < max_retries - 1:
                    if ui:
                        ui.log_line(f"[als] ALS not ready yet (attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s...")
                    else:
                        print(f"[als] ALS not ready yet (attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)  # Exponential backoff, max 10s
                else:
                    if ui:
                        ui.log_line(f"[als] Warning: Readiness check failed after {max_retries} attempts: {e}")
                        ui.log_line("[als] Continuing anyway - first file may take longer")
                    else:
                        print(f"[als] Warning: Readiness check failed after {max_retries} attempts: {e}")
                        print("[als] Continuing anyway - first file may take longer")
            
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