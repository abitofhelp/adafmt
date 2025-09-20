#!/usr/bin/env python3
"""
Update markdown headers (**Version:** and **Date:**) across docs/**.md.

- Detects the next version using python-semantic-release (noop/print).
- Writes ISO 8601 UTC timestamp for Date (e.g., 2025-09-19T23:41:07Z).
- Safe, idempotent replacements; preserves trailing spaces at EOL.
- Creates .bak backups unless --no-backup is passed.

Usage:
  Dry run (show planned changes):
    python update_doc_headers.py

  Apply changes:
    python update_doc_headers.py --write

  Override version:
    python update_doc_headers.py --write --version 1.2.3

  Specify roots/files explicitly:
    python update_doc_headers.py --write docs docs/guides/configuration-guide.md
"""

from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Regexes that preserve original whitespace:
RE_VERSION = re.compile(
    r"(?m)^(?P<prefix>\*\*Version:\*\*\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)
RE_DATE = re.compile(
    r"(?m)^(?P<prefix>\*\*Date:\*\*\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)

DEFAULT_GLOBS = ["docs/**/*.md"]


def iso8601_now_utc_z() -> str:
    # ISO 8601 with trailing Z (UTC)
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def try_run(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"


def detect_next_version() -> Optional[str]:
    """
    Ask python-semantic-release for the next version, without side effects.
    Tries several CLI spellings for cross-version compatibility.
    Allows override via SEMVER_NEXT.
    """
    env_override = os.getenv("SEMVER_NEXT")
    if env_override:
        return env_override.strip()

    candidates = [
        ["semantic-release", "version", "--noop", "--print"],
        ["semantic-release", "version", "--print", "--noop"],
        ["semantic-release", "--noop", "version", "--print"],
        # Some installs are module-invoked:
        [sys.executable, "-m", "semantic_release", "version", "--noop", "--print"],
        [sys.executable, "-m", "semantic_release", "version", "--print", "--noop"],
        # Older variants (may not exist anymore, harmless to try):
        ["semantic-release", "print-version"],
        [sys.executable, "-m", "semantic_release", "print-version"],
    ]

    for cmd in candidates:
        code, out, err = try_run(cmd)
        if code == 0 and out:
            # Heuristic: version lines often look like "1.2.3"
            line = out.strip().splitlines()[-1].strip()
            if re.fullmatch(r"\d+\.\d+\.\d+(?:[-+].+)?", line):
                return line
            # Some versions print "next version: 1.2.3"
            m = re.search(r"(\d+\.\d+\.\d+(?:[-+].+)?)", out)
            if m:
                return m.group(1)
        # If command not found or failed, fall through to the next candidate.
    return None


def iter_markdown_files(paths: Iterable[str]) -> Iterable[Path]:
    if not paths:
        paths = DEFAULT_GLOBS
    for p in paths:
        pth = Path(p)
        if pth.is_file() and pth.suffix.lower() == ".md":
            yield pth
        else:
            # Treat as glob
            for fp in Path().glob(p):
                if fp.is_file() and fp.suffix.lower() == ".md":
                    yield fp


def replace_header(content: str, version: str, iso_date: str) -> Tuple[str, bool, bool]:
    """
    Returns (new_content, changed_version, changed_date)
    """
    changed_version = False
    changed_date = False

    def _sub(rex: re.Pattern, new_value: str) -> Tuple[str, bool]:
        def repl(m: re.Match) -> str:
            return f"{m.group('prefix')}{new_value}{m.group('suffix')}"

        new_text, n = rex.subn(repl, content if not hasattr(rex, "_done") else _sub.current, count=1)
        return new_text, n > 0

    # Chain replacements while preserving potential earlier changes
    _sub.current = content
    _sub.rex = RE_VERSION  # for mypy happiness
    _sub.current, changed_version = RE_VERSION.subn(
        lambda m: f"{m.group('prefix')}{version}{m.group('suffix')}", _sub.current, count=1
    )
    _sub.current, changed_date = RE_DATE.subn(
        lambda m: f"{m.group('prefix')}{iso_date}{m.group('suffix')}", _sub.current, count=1
    )
    return _sub.current, changed_version, changed_date


def make_backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
    # Avoid overwriting an existing backup unexpectedly; rotate a little
    if bak.exists():
        i = 1
        while True:
            candidate = path.with_suffix(path.suffix + f".bak.{i}")
            if not candidate.exists():
                bak = candidate
                break
            i += 1
    bak.write_bytes(path.read_bytes())
    return bak


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--write",
        action="store_true",
        help="Apply changes to files (default is dry-run).",
    )
    ap.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create .bak backups when writing.",
    )
    ap.add_argument(
        "--version",
        help="Override next version (skips semantic-release detection).",
    )
    ap.add_argument(
        "paths",
        nargs="*",
        help="Files or globs to process (default: docs/**/*.md).",
    )
    args = ap.parse_args(argv)

    version = args.version or detect_next_version()
    if not version:
        print(
            "ERROR: Could not determine next version from python-semantic-release.\n"
            " - Ensure 'semantic-release' is installed and configured, or\n"
            " - Provide --version X.Y.Z or set SEMVER_NEXT environment variable.",
            file=sys.stderr,
        )
        return 2

    iso_date = iso8601_now_utc_z()

    files = sorted(set(iter_markdown_files(args.paths)))
    if not files:
        print("No markdown files matched. (Try specifying paths or check docs/ exists.)")
        return 1

    print(f"Planned updates:")
    print(f"  Version -> {version}")
    print(f"  Date    -> {iso_date}")
    print()

    total_changed = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[SKIP] {f} (read error: {e})")
            continue

        new_text, ch_ver, ch_date = replace_header(text, version, iso_date)
        if ch_ver or ch_date:
            total_changed += 1
            action = "UPDATE" if args.write else "WOULD UPDATE"
            which = []
            if ch_ver:
                which.append("Version")
            if ch_date:
                which.append("Date")
            print(f"[{action}] {f} ({', '.join(which)})")
            if args.write:
                try:
                    if not args.no_backup:
                        make_backup(f)
                    f.write_text(new_text, encoding="utf-8", newline="")  # preserve LF/CRLF as read by Python
                except Exception as e:
                    print(f"[ERROR] {f} (write error: {e})")
        else:
            print(f"[OK] {f} (no header changes needed)")

    print()
    if args.write:
        print(f"Done. Files changed: {total_changed}/{len(files)}")
    else:
        print(f"Dry run complete. Files needing changes: {total_changed}/{len(files)}")
        print("Re-run with --write to apply changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
