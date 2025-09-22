# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

import re
import json
from dataclasses import dataclass
from typing import Tuple, Dict
from pathlib import Path

try:
    import regex as rx  # type: ignore
except Exception:
    rx = None

NAME_RE = re.compile(r'^[a-z0-9\-_]{12}$')
ALLOWED_FLAGS = {"MULTILINE": re.MULTILINE, "IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL}

# Load patterns from the actual patterns file
patterns_file = Path(__file__).parent / "test_patterns.json"
if patterns_file.exists():
    with open(patterns_file) as f:
        DEFAULT_PATTERNS = json.load(f)
else:
    # Fallback to empty patterns
    DEFAULT_PATTERNS = []

@dataclass
class ApplyStats:
    replacements_by_rule: Dict[str,int]
    total_replacements: int
    applied_rules: list

class PatternEngine:
    @staticmethod
    def load_list(items: list):
        # validate + compile
        rules = []
        seen = set()
        for it in items:
            name = it["name"]
            assert NAME_RE.fullmatch(name), f"invalid name: {name}"
            assert name not in seen, f"duplicate name: {name}"
            seen.add(name)
            flags_bits = 0
            for f in it.get("flags", []):
                flags_bits |= ALLOWED_FLAGS[f]
            comp = (rx.compile if rx else re.compile)(it["find"], flags_bits)
            rules.append((name, comp, it["replace"]))
        rules.sort(key=lambda x: x[0])
        return rules

    @staticmethod
    def apply(text: str, rules, timeout_ms: int = 50) -> Tuple[str, ApplyStats]:
        out = text
        hits = {}
        total = 0
        for (name, pat, repl) in rules:
            if rx:
                try:
                    out, n = pat.subn(repl, out, timeout=timeout_ms/1000.0 if timeout_ms else None)
                except rx.TimeoutError:  # pragma: no cover
                    continue
            else:
                out, n = pat.subn(repl, out)
            if n:
                total += n
                hits[name] = hits.get(name, 0) + n
        return out, ApplyStats(hits, total, sorted(hits.keys()))

def fake_als(text: str) -> str:
    # minimal ALS-like normalization for tests
    text = re.sub(r"[ \t]*:=[ \t]*", " := ", text)
    if not text.endswith("\n"):
        text += "\n"
    return text


def is_gcc_available() -> bool:
    """Check if gcc is available for Ada compilation."""
    import subprocess
    try:
        result = subprocess.run(
            ['gcc', '--version'],
            capture_output=True,
            timeout=2
        )
        # Check if it succeeded and doesn't have license agreement message
        if result.returncode == 0:
            return True
        # Check for Xcode license message
        output = (result.stdout or b'').decode('utf-8', errors='ignore') + (result.stderr or b'').decode('utf-8', errors='ignore')
        if 'Xcode license' in output:
            return False
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def compiles_ada(ada_code: str, timeout: int = 5) -> Tuple[bool, str]:
    """Check if Ada code compiles successfully using gcc.
    
    Args:
        ada_code: The Ada source code to compile
        timeout: Compilation timeout in seconds
        
    Returns:
        Tuple of (success: bool, message: str)
        - success: True if compilation succeeded
        - message: Empty string on success, error details on failure
    """
    import subprocess
    import tempfile
    import os
    
    # Create a temporary directory for compilation
    temp_dir = tempfile.mkdtemp()
    src_path = os.path.join(temp_dir, 'test.adb')
    obj_path = os.path.join(temp_dir, 'test.o')
    
    # Write the source code
    with open(src_path, 'w') as f:
        f.write(ada_code)
    
    try:
        # Compile with gcc
        # -c: compile only (no linking)
        # -gnat2012: Ada 2012 mode
        # -gnatp: suppress all checks (faster compilation for tests)
        # Note: We don't use -gnatwe (warnings as errors) because temp files
        # trigger filename warnings that aren't relevant to our tests
        result = subprocess.run(
            ['gcc', '-c', '-gnat2012', '-gnatp', src_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=temp_dir  # Run in temp directory
        )
        
        # GCC returns 0 for success, even with warnings
        # Only actual errors cause non-zero return codes
        if result.returncode == 0:
            return True, ""
        else:
            # Extract meaningful error message
            error_lines = result.stderr.strip().split('\n')
            # Filter to only show actual errors, not warnings
            meaningful_errors = []
            for line in error_lines:
                # Skip warnings and focus on errors
                if 'error:' in line.lower():
                    # Replace temp filename with a generic placeholder
                    if src_path in line:
                        line = line.replace(src_path, '<ada_source>')
                    meaningful_errors.append(line)
            
            error_msg = '\n'.join(meaningful_errors) if meaningful_errors else result.stderr
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"Compilation timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, "gcc not found - ensure GNAT is installed"
    except Exception as e:
        return False, f"Compilation error: {str(e)}"
    finally:
        # Clean up temporary directory and all files
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass