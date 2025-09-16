#!/usr/bin/env python3
# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Mocked harness: runs adafmt pipeline without ALS by simulating edits.
Useful for quick sanity checks and CI smoke tests.
"""
from pathlib import Path
from adafmt.file_discovery import collect_files
from adafmt.edits import unified_diff

def main():
    print("[mock] discovering files under current directory…")
    files = collect_files([Path.cwd()], [])
    print(f"[mock] found {len(files)} Ada files")
    for f in files[:10]:
        txt = f.read_text(encoding="utf-8")
        # pretend formatting adds trailing newline
        new = txt if txt.endswith("\n") else txt + "\n"
        if new != txt:
            print(f"[changed] {f}")
            print(unified_diff(txt, new, str(f)))

if __name__ == "__main__":
    main()
