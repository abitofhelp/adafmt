# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Command-line interface for adafmt - redirects to new CLI."""

# Import from the new CLI module
from .cli_new import app, main

# Export the main function and app for compatibility
__all__ = ["main", "app"]