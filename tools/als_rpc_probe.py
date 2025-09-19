#!/usr/bin/env python3
# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Simple ALS integration probe: init -> didOpen -> hover -> formatting.

This tool tests Ada Language Server communication using the adafmt ALSClient.
It can run with or without a specific file to process.
"""
import argparse, asyncio, json, time
from pathlib import Path
from adafmt.als_client import ALSClient

def _abs(p: str) -> Path:
    return Path(p).expanduser().resolve()

async def main():
    ap = argparse.ArgumentParser(
        description="ALS probe (ALSClient-based)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    ap.add_argument("--project-path", required=True, help="Absolute path to .gpr")
    ap.add_argument("--file", help="File to open/hover/format (optional)")
    ap.add_argument("--alr-mode", choices=("auto","yes","no"), default="auto",
                    help="Alire mode: auto-detect, force yes, or force no")
    ap.add_argument("--crate-dir", help="Alire crate directory (optional)")
    ap.add_argument("--init-timeout", type=float, default=180,
                    help="Timeout for ALS initialization")
    ap.add_argument("--warmup-seconds", type=float, default=10,
                    help="Warmup period after initialization")
    ap.add_argument("--hover-timeout", type=float, default=15,
                    help="Timeout for hover request")
    ap.add_argument("--format-timeout", type=float, default=60,
                    help="Timeout for formatting request")
    ap.add_argument("--verbose", action="store_true",
                    help="Enable verbose output")
    args = ap.parse_args()
    
    # Convert paths to absolute
    project_file_path = str(_abs(args.project_path))
    target_file_path = str(_abs(args.file)) if args.file else None
    crate_dir = str(_abs(args.crate_dir)) if args.crate_dir else None

    # Create ALS client
    als = ALSClient(
        project_file_path=project_file_path,
        alr_mode=args.alr_mode,
        crate_dir=crate_dir,
        init_timeout_seconds=args.init_timeout,
        warmup_seconds=args.warmup_seconds,
        process_timeout_seconds=300,
        stderr_file_path=None
    )

    start = time.time()
    await als.start()
    
    if args.verbose:
        print(f"Started ALS in {time.time()-start:.1f}s")
        if als.log_file_path:
            print(f"ALS log: {als.log_file_path}")
    
    if target_file_path:
        # Open the file
        print(f"\n=== Opening {target_file_path} ===")
        await als.did_open(target_file_path, Path(target_file_path).read_text(encoding="utf-8"))
        
        # Try hover at position 0,0
        print(f"\n=== Hover at 0:0 ===")
        try:
            hover_resp = await als.request_with_timeout(
                "textDocument/hover",
                {
                    "textDocument": {"uri": f"file://{target_file_path}"},
                    "position": {"line": 0, "character": 0}
                },
                timeout=args.hover_timeout
            )
            print(json.dumps(hover_resp, indent=2))
        except Exception as e:
            print(f"Hover failed: {type(e).__name__}: {e}")
        
        # Try formatting
        print(f"\n=== Formatting ===")
        try:
            fmt_resp = await als.request_with_timeout(
                "textDocument/formatting",
                {
                    "textDocument": {"uri": f"file://{target_file_path}"},
                    "options": {"tabSize": 3, "insertSpaces": True}
                },
                timeout=args.format_timeout
            )
            if fmt_resp:
                print(f"Got {len(fmt_resp)} edits")
                for i, edit in enumerate(fmt_resp[:3]):  # Show first 3 edits
                    print(f"  Edit {i+1}: {json.dumps(edit, indent=2)}")
                if len(fmt_resp) > 3:
                    print(f"  ... and {len(fmt_resp)-3} more edits")
            else:
                print("No edits returned (file already formatted)")
        except Exception as e:
            print(f"Formatting failed: {type(e).__name__}: {e}")
        
        # Close the file
        await als.did_close(target_file_path)
        print(f"\n=== Closed {target_file_path} ===")
    else:
        print("\nNo file specified - ALS initialized successfully")
        print("Use --file to test hover and formatting operations")
    
    # Shutdown
    await als.shutdown()
    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())