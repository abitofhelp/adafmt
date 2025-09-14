#!/usr/bin/env python3
# =============================================================================
# adafmt - Ada Language Formatter
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# Licensed under the MIT License. See LICENSE file in the project root.
# =============================================================================

"""Entry point for adafmt when run as a module (python -m adafmt)."""

import sys
import os

# Add the parent directory to the path so we can import adafmt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adafmt.cli import main

if __name__ == "__main__":
    main()