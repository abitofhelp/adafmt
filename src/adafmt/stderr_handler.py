# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Stderr redirection and handling for the Ada formatter."""

import contextlib
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Tuple


class Tee(io.TextIOBase):
    """Redirect output to multiple streams."""
    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]
    
    def write(self, s):
        wrote = 0
        for st in self._streams:
            try:
                wrote = st.write(s)
                st.flush()
            except Exception:
                pass
        return wrote
    
    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass


def setup_stderr_redirect(stderr_path: Optional[Path]) -> Tuple[Any, Any, Any]:
    """
    Set up stderr redirection to a file.
    
    Args:
        stderr_path: Path to redirect stderr to (or None to skip)
        
    Returns:
        Tuple of (original_stderr, tee_fp, restore_function)
    """
    orig_stderr = sys.stderr
    tee_fp = None
    
    def restore_stderr():
        nonlocal tee_fp, orig_stderr
        try:
            sys.stderr = orig_stderr
        except Exception:
            pass
        if tee_fp:
            with contextlib.suppress(Exception):
                tee_fp.flush()
                tee_fp.close()
            tee_fp = None
    
    try:
        if stderr_path:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            tee_fp = open(stderr_path, "w", encoding="utf-8")
            tee_fp.write(f"{datetime.now().isoformat()} | INFO  | ADAFMT STDERR START\n")
            tee_fp.flush()
            sys.stderr = Tee(tee_fp)  # Only write to file, not to terminal
    except Exception:
        sys.stderr = orig_stderr
        
    return orig_stderr, tee_fp, restore_stderr