# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Helper functions for the CLI module."""

from pathlib import Path

import typer

# Python 3.9+: importlib.resources.files
try:
    from importlib.resources import files as pkg_files
except ImportError:
    pkg_files = None

# Version is dynamically read from package metadata
try:
    from importlib.metadata import version
    APP_VERSION = version("adafmt")
except Exception:
    # Fallback for development/editable installs
    APP_VERSION = "0.0.0"


def read_license_text() -> str:
    """Read the LICENSE file from package data or filesystem."""
    # 1) Prefer a bundled copy inside the package: adafmt/LICENSE
    if pkg_files:
        try:
            return pkg_files("adafmt").joinpath("LICENSE").read_text(encoding="utf-8")
        except Exception:
            pass

    # 2) Fallbacks for dev runs from a source checkout
    here = Path(__file__).resolve()
    for candidate in (
        here.parent / "LICENSE",
        here.parent.parent / "LICENSE",
        here.parent.parent.parent / "LICENSE",  # src/adafmt -> src -> repo root
        Path.cwd() / "LICENSE",
    ):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError("LICENSE not found. Bundle it as package data or run from repo root.")


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"adafmt version {APP_VERSION}")
        raise typer.Exit()


def abs_path(p: str) -> str:
    """Convert a path string to an absolute path."""
    return str(Path(p).expanduser().resolve())