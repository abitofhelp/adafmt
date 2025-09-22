# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""File discovery and resolution logic for the Ada formatter."""

from pathlib import Path
from typing import List, Optional, Any

from .file_discovery import collect_files
from .path_validator import validate_path


def is_ada_file(path: Path) -> bool:
    """Check if a path points to an Ada source file."""
    return path.suffix.lower() in (".ads", ".adb", ".ada")


def discover_files(
    files: Optional[List[str]] = None,
    include_paths: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    ui: Optional[Any] = None
) -> List[Path]:
    """
    Discover and validate Ada files to process.
    
    Args:
        files: Specific files to process (if provided, discovery is skipped)
        include_paths: Directories to search for Ada files
        exclude_paths: Directories to exclude from search
        ui: UI instance for logging (optional)
        
    Returns:
        List of validated absolute paths to Ada files
    """
    file_paths: List[Path] = []
    
    if files:
        # User specified specific files
        # Convert to absolute paths and filter Ada files
        for p in files:
            path = Path(p)
            if is_ada_file(path):
                abs_path = path.resolve()
                # Validate path after resolving to absolute
                validation_error = validate_path(str(abs_path))
                if validation_error:
                    if ui:
                        ui.log_line(f"[warning] Skipping invalid file path '{p}' (resolved to '{abs_path}') - {validation_error}")
                    else:
                        print(f"[warning] Skipping invalid file path '{p}' (resolved to '{abs_path}') - {validation_error}")
                    continue
                file_paths.append(abs_path)
    else:
        # Discover files in include paths
        if ui:
            ui.log_line("[discovery] Starting file discovery...")
        else:
            print("[discovery] Starting file discovery...")
        
        # Collect files and convert to absolute paths
        collected_files = collect_files(include_paths or [], exclude_paths or [])
        for p in collected_files:
            path = Path(p)
            if is_ada_file(path):
                abs_path = path.resolve()
                # Validate path after resolving to absolute
                validation_error = validate_path(str(abs_path))
                if validation_error:
                    if ui:
                        ui.log_line(f"[warning] Skipping invalid file path '{p}' (resolved to '{abs_path}') - {validation_error}")
                    else:
                        print(f"[warning] Skipping invalid file path '{p}' (resolved to '{abs_path}') - {validation_error}")
                    continue
                file_paths.append(abs_path)
        
        if ui:
            ui.log_line("[discovery] File discovery completed")
        else:
            print("[discovery] File discovery completed")
            
    return file_paths