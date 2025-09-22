# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

import re
from dataclasses import dataclass
from typing import Tuple, Dict
try:
    import regex as rx  # type: ignore
except Exception:
    rx = None

NAME_RE = re.compile(r'^[a-z0-9\-_]{12}$')
ALLOWED_FLAGS = {"MULTILINE": re.MULTILINE, "IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL}

DEFAULT_PATTERNS = [
  {
    "name": "assoc_arrow1",
    "title": "Spaces around `=>`",
    "category": "operator",
    "find": "[ \\t]*=>[ \\t]*",
    "replace": " => ",
    "comment": "Applies to named associations, aggregates, case arms."
  },
  {
    "name": "attr_tick_01",
    "title": "No space before attribute tick `'`",
    "category": "attribute",
    "find": "^(?:(?:[^\\\"\\\\n]*\\\"){2})*[^\\\"\\\\n]*?(?P<pre>(?:\\\\w|\\\\)))\\\\s+'",
    "replace": "\\\\g<pre>'",
    "flags": [
      "MULTILINE"
    ],
    "comment": "E.g., `Obj 'Address` \u2192 `Obj'Address`; avoids strings (even-quote heuristic)."
  },
  {
    "name": "cmt_whole_01",
    "title": "Whole-line comment spacing: `--  text`",
    "category": "comment",
    "find": "^(?P<i>[ \\\\t]*)--[ \\\\t]*(?P<t>\\\\S.*)$",
    "replace": "\\\\g<i>--  \\\\g<t>",
    "flags": [
      "MULTILINE"
    ],
    "comment": "Preserves indentation; enforces two spaces after `--`."
  },
  {
    "name": "comma_space1",
    "title": "Comma spacing",
    "category": "delimiter",
    "find": "[ \\\\t]*,[ \\\\t]*(?=[^\\\\s\\\\)])",
    "replace": ", ",
    "comment": "No space before comma; exactly one space after (unless before `)` or EOL)."
  },
  {
    "name": "comment_eol1",
    "title": "EOL comment spacing: one before --, two after",
    "category": "comment",
    "find": "^(?P<head>(?:(?:[^\\\"\\\\n]*\\\"){2})*[^\\\"\\\\n]*?\\\\S)[ \\\\t]*--[ \\\\t]*(?P<text>.+)$",
    "replace": "\\\\g<head> --  \\\\g<text>",
    "flags": [
      "MULTILINE"
    ],
    "comment": "Avoids strings via even-quote heuristic; formats EOL comments as ` \u2420--\u2420\u2420text`."
  },
  {
    "name": "decl_colon01",
    "title": "Declaration colon spacing: `Name : Type`",
    "category": "declaration",
    "find": "^(?P<i>[ \\\\t]*)(?:(?:[^\\\\n\\\\\\\"]*\\\\\\\"){2})*[^\\\\n\\\\\\\"]*?(?P<lhs>\\\\b\\\\w(?:[\\\\w.]*\\\\w)?)[ \\\\t]*:[ \\\\t]*(?P<rhs>[^=\\\\n].*)$",
    "replace": "\\\\g<i>\\\\g<lhs> : \\\\g<rhs>",
    "flags": [
      "MULTILINE"
    ],
    "comment": "Excludes assignments (`:=`); preserves indentation; avoids strings with even-quote heuristic."
  },
  {
    "name": "eof_newline1",
    "title": "Ensure final newline at EOF",
    "category": "hygiene",
    "find": "([^\\\\n])\\\\Z",
    "replace": "\\\\1\\\\n",
    "comment": "Guarantee exactly one newline at end of file."
  },
  {
    "name": "paren_l_sp01",
    "title": "No space after `(`",
    "category": "delimiter",
    "find": "\\\\(\\\\s+",
    "replace": "(",
    "comment": "Trim spaces right after opening parenthesis."
  },
  {
    "name": "paren_r_sp01",
    "title": "No space before `)`",
    "category": "delimiter",
    "find": "\\\\s+\\\\)",
    "replace": ")",
    "comment": "Trim spaces right before closing parenthesis."
  },
  {
    "name": "range_dots01",
    "title": "Spaces around `..`",
    "category": "operator",
    "find": "(?<!\\\\.)[ \\\\t]*\\\\.\\\\.[ \\\\t]*(?!\\\\.)",
    "replace": " .. ",
    "comment": "Normalizes range operator spacing (`1 .. 10`)."
  },
  {
    "name": "semi_space01",
    "title": "No space before `;`",
    "category": "delimiter",
    "find": "[ \\\\t]+;",
    "replace": ";",
    "comment": "Remove any whitespace immediately before semicolons."
  },
  {
    "name": "assign_set01",
    "title": "Spaces around `:=`",
    "category": "operator",
    "find": "[ \\\\t]*:=[ \\\\t]*",
    "replace": " := ",
    "comment": "Assignment operator spacing."
  },
  {
    "name": "ws_trail_sp1",
    "title": "Trim trailing whitespace",
    "category": "hygiene",
    "find": "[ \\\\t]+$",
    "replace": "",
    "flags": [
      "MULTILINE"
    ],
    "comment": "Remove spaces/tabs at end of each line."
  }
]

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
