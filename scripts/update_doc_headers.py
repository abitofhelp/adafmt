#!/usr/bin/env python3
# Update **Version:** and **Date:** headers in README.md and docs/**.md.
# - Detects next version via python-semantic-release (noop/print), unless SEMVER_NEXT or --version is supplied.
# - Writes ISO 8601 UTC timestamp for Date (e.g., 2025-09-19T23:41:07Z).
# - Safe, idempotent replacements; supports --no-backup; auto-detects repo root for running semantic-release.

from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

RE_VERSION = re.compile(r"(?m)^(?P<prefix>\*\*Version:\*\*\s*)(?P<value>.*?)(?P<suffix>\s*)$")
RE_DATE = re.compile(r"(?m)^(?P<prefix>\*\*Date:\*\*\s*)(?P<value>.*?)(?P<suffix>\s*)$")

DEFAULT_GLOBS = ["README.md", "docs/**/*.md"]

def iso8601_now_utc_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def try_run(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, cwd=str(cwd) if cwd else None)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"

def git_root() -> Optional[Path]:
    code, out, err = try_run(["git", "rev-parse", "--show-toplevel"])
    if code == 0 and out:
        p = Path(out.strip())
        if p.exists():
            return p
    return None

def detect_next_version(cwd: Optional[Path]) -> Optional[str]:
    env_override = os.getenv("SEMVER_NEXT")
    if env_override:
        return env_override.strip()
    candidates = [
        [sys.executable, "-m", "semantic_release", "version", "--noop", "--print"],
        [sys.executable, "-m", "semantic_release", "version", "--print", "--noop"],
        ["semantic-release", "version", "--noop", "--print"],
        ["semantic-release", "version", "--print", "--noop"],
        [sys.executable, "-m", "semantic_release", "print-version"],
        ["semantic-release", "print-version"],
    ]
    for cmd in candidates:
        code, out, err = try_run(cmd, cwd=cwd)
        if code == 0 and out:
            m = re.search(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", out.strip())
            if m:
                return m.group(0)
    return None

def iter_markdown_files(paths: Iterable[str]) -> Iterable[Path]:
    if not paths:
        paths = DEFAULT_GLOBS
    seen = set()
    for p in paths:
        pth = Path(p)
        if pth.is_file() and pth.suffix.lower() == ".md":
            if pth not in seen:
                seen.add(pth)
                yield pth
        else:
            for fp in Path().glob(p):
                if fp.is_file() and fp.suffix.lower() == ".md" and fp not in seen:
                    seen.add(fp)
                    yield fp

def replace_header(content: str, version: str, iso_date: str) -> Tuple[str, bool, bool]:
    changed_version = False
    changed_date = False
    new_text, n1 = RE_VERSION.subn(lambda m: f"{m.group('prefix')}{version}{m.group('suffix')}", content, count=1)
    changed_version = n1 > 0
    new_text, n2 = RE_DATE.subn(lambda m: f"{m.group('prefix')}{iso_date}{m.group('suffix')}", new_text, count=1)
    changed_date = n2 > 0
    return new_text, changed_version, changed_date

def make_backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
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
    ap = argparse.ArgumentParser(description="Update **Version:** and **Date:** headers in README.md and docs/**.md.")
    ap.add_argument("--write", action="store_true", help="Apply changes to files (default is dry-run).")
    ap.add_argument("--no-backup", action="store_true", help="Do not create .bak backups when writing.")
    ap.add_argument("--version", help="Override next version (skips semantic-release detection).")
    ap.add_argument("paths", nargs="*", help="Files or globs (default: README.md docs/**/*.md).")
    args = ap.parse_args(argv)

    repo_root = git_root()
    if not repo_root:
        print("ERROR: Not inside a Git repository (git rev-parse failed). Run from a repo.", file=sys.stderr)
        return 2

    version = args.version or detect_next_version(repo_root)
    if not version:
        print("ERROR: Could not determine next version from python-semantic-release.\\n"
              " - Ensure it's installed and configured, or\\n"
              " - Provide --version X.Y.Z or set SEMVER_NEXT.", file=sys.stderr)
        return 2

    iso_date = iso8601_now_utc_z()

    files = sorted(set(iter_markdown_files(args.paths)))
    if not files:
        print("No markdown files matched. (Try specifying paths or check docs/ exists.)")
        return 1

    print(f"Planned updates:")
    print(f"  Version -> {version}")
    print(f"  Date    -> {iso_date}\\n")

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
            which = ",".join([w for w, b in (("Version", ch_ver), ("Date", ch_date)) if b]) or "none"
            print(f"[{action}] {f} ({which})")
            if args.write:
                try:
                    if not args.no_backup:
                        make_backup(f)
                    f.write_text(new_text, encoding="utf-8")
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
    raise SystemExit(main())
