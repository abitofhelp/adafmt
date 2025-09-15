# Software Design Description (SDD)
# adafmt — Pattern Formatter Layer

**Document Version:** 1.4.0  
**Date:** September 15, 2025  
**Status:** Implementation Ready (with 12-char slugs, title/category)

---

## 1. Architecture Overview

The Pattern Formatter is a **post‑ALS** stage. It loads a set of compiled regex rules at startup, keeps them immutable, and applies them sequentially to ALS‑formatted buffers. It reports activity to the UI/TTY, emits a dedicated Pat Log (`adafmt_<timestamp>_patterns.log`), and contributes to the Extra Metrics section.

**Important:** Pattern processing only occurs on files that have valid Ada syntax. If ALS fails on a file, adafmt runs compiler validation. Only files that pass compiler validation (false positive ALS failures) proceed to pattern processing. Files with true syntax errors are skipped entirely.

```
┌──────────────┐     ┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│ File Walker  │ --> │     ALS      │ --> │ Pattern Formatter  │ --> │ Atomic Write │
└──────────────┘     └──────────────┘     └────────────────────┘     └──────────────┘
                                     \--> UI/TTY status + Pat Log
```

For optional validation mode (`--validate-patterns`):
```
┌────────────────────┐     ┌──────────────┐
│ Pattern Formatter  │ --> │  ALS (check) │ --> Report differences
└────────────────────┘     └──────────────┘
```

---

## 2. Key Components

### 2.1 PatternFormatter
- **State (Python 3.8 typing):**
  - `rules: Tuple[CompiledRule, ...]`
  - `enabled: bool`, `loaded_count: int`
  - `files_touched: Dict[str, int]`
  - `replacements: Dict[str, int]`
- **Methods:**
  - `load_from_json(path: Path, logger, ui) -> PatternFormatter`
  - `apply(path: Path, text: str, logger=None, ui=None) -> Tuple[str, FileApplyResult]`
- **Safety:** skip invalid rules; continue on per‑pattern error; enforce timeout per application.

### 2.2 CompiledRule
- `name: str` (12‑char slug)  
- `title: str` (human-readable title, 1-80 chars)  
- `category: str` (one of: comment, hygiene, operator, delimiter, declaration, attribute)  
- `find: Pattern` (from third‑party `regex` module when available)  
- `replace: str`

### 2.3 FileApplyResult
- `applied_names: List[str]` — distinct pattern names that changed the file  
- `replacements_sum: int` — total replacements across patterns

### 2.4 Pattern JSON Loader
- Validates schema (12-char names, title 1-80 chars, valid category), compiles regex (maps `flags` to engine flags), and returns immutable rule set.  
- Closes the file immediately after reading (including exceptions).  
- Enforces **name uniqueness**, required fields (name, title, category, find, replace), allowed flags, and successful compilation.

### 2.5 Pattern Validator (NEW)
- **Purpose:** Optional validation of pattern output using ALS
- **Modes:**
  - `warn`: Log if ALS would make changes to pattern output
  - `strict`: Exit with error if ALS would change pattern output
- **Implementation:** Runs ALS format check on pattern output in-memory

---

## 3. CLI & Configuration

- **`--patterns-path <FILE>`** — override default `./adafmt_patterns.json`.  
- **`--no-patterns`** — disable loading and applying patterns; still produce Pat Log with `patterns_loaded:0`.  
- **`--write`** — apply changes to disk; absence implies **dry run**.  
- **`--patterns-timeout-ms <int>`** — default **50**.  
- **`--patterns-max-bytes <int>`** — default **10485760** (10 MiB).
- **`--validate-patterns[=warn|strict]`** — validate pattern output with ALS (NEW).

---

## 4. UI / TUI Integration

### 4.1 Per‑File Status Line
Append to the existing ALS line:

```
ALS: ✓ edits=<n> | Patterns: patterns=<N> applied=<K> (+<R>) | mode=DRY|WRITE
```

### 4.2 Footer (Pretty/Basic/Plain)
Insert **"Pat Log"** line **under "Log"** and above "Stderr":

```
Log:     ./adafmt_<ts>_log.jsonl (default location)
Pat Log: ./adafmt_<ts>_patterns.log (default location)
Stderr:  ./adafmt_<ts>_stderr.log (default location)
ALS Log: ~/.als/ada_ls_log.*.log (default location)
```

### 4.3 TTY Exit Paths
Print the same four lines (Log, Pat Log, Stderr, ALS) before process exit.

---

## 5. Logging — Pattern JSONL (Pat Log)

- **Filename:** `adafmt_<timestamp>_patterns.log` (created once per run).  
- **Events** (JSONL object per line):
  - `run_start`: `{ev, ts, patterns_path, patterns_loaded, mode, timeout_ms, max_bytes}`
  - `file`: `{ev, ts, path, als_ok, als_edits, patterns_applied[], replacements}`
  - `file_skipped_large`: `{ev, ts, path, size_bytes, max_bytes}`
  - `pattern`: `{ev, ts, path, name, title, category, replacements}`
  - `pattern_error`: `{ev, ts, path, name, title, category, error}`
  - `pattern_timeout`: `{ev, ts, path, name, title, category, timeout_ms}`
  - `validation_check`: `{ev, ts, path, als_would_change, mode}` (NEW)
  - `run_end`: `{ev, ts, files_total, files_als_ok, patterns_loaded, patterns_summary{ name:{files_touched, replacements} }}`

Reuse the existing `JsonlLogger`; instantiate a second logger instance for Pat Log. Share the same startup timestamp as other logs.

---

## 6. Control Flow

### 6.1 Startup
1. Parse CLI (`--no-patterns`, `--patterns-path`, `--write`, `--patterns-timeout-ms`, `--patterns-max-bytes`, `--validate-patterns`).  
2. Create shared `<timestamp>` for the run and initialize logs (including Pat Log).  
3. If not `--no-patterns`: load and compile rules; else set `enabled=false`, `loaded_count=0`.  
4. Emit Pat Log `run_start`.

### 6.2 Per File
1. Run ALS; if failure → compiler validation:
   - If compiler fails: true syntax error → skip file entirely
   - If compiler succeeds: false positive → continue to patterns
2. If ALS success or false positive → **size check**: if `> max_bytes`, emit `file_skipped_large`, skip patterns.  
3. Apply rules sequentially with timeout per rule application (`timeout_ms`).  
4. Emit `file` + `pattern` events; on timeout/error, emit `pattern_timeout`/`pattern_error`.  
5. **If validation mode** (NEW):
   - Run ALS format check on pattern output
   - Log `validation_check` event
   - In `strict` mode, track validation failures
6. If `--write` and buffer changed → atomic write.  
7. Update UI per‑file status line.

### 6.3 Shutdown
1. Render **Extra Metrics**: list patterns with `files_touched>0`.  
2. Emit Pat Log `run_end` with `patterns_summary`.  
3. Print four final paths (Log, Pat Log, Stderr, ALS).  
4. **If validation strict mode had failures**, exit with code 2 (NEW).
5. Close all logs.

---

## 7. Implementation Notes

- **Regex engine & timeout:** Prefer third‑party `regex` module for `subn(..., timeout=ms)`. If unavailable, use signal-based timeout or document limitation.  
- **Type hints:** Use Python 3.8 compatible generics: `Dict[str, int]`, `List[str]`, `Tuple[...]`.  
- **Atomic writes:** temp file + `os.replace`; preserve EOLs/encoding (leverage existing utils).  
- **Determinism:** sort rules by `name` before applying.
- **Validation:** Reuse existing ALS client for format checking in validation mode.

---

## 8. Error Handling

- **Load errors**: skip bad entries; if none valid → enabled=false (`patterns=0`).  
- **Runtime errors/timeouts**: continue to next pattern; TTY red `[name]`; log event; pipeline continues.  
- **Write failures**: log; keep original; continue run.
- **Validation failures**: log warning/error based on mode; strict mode sets exit code.

---

## 9. Testing Strategy

- **Unit**: loader validation (schema, flags, compile), timeout behavior (inject slow regex), size cap.  
- **Golden**: before/after fixtures (common Ada constructs).  
- **CLI**: `--no-patterns`, missing file, dry vs write, large file skip.  
- **Integration**: end‑to‑end with ALS success/failure and multiple patterns.
- **Validation**: test both warn and strict modes with patterns that conflict with ALS.

---

## 10. History
- 1.4.0 — 2025‑09‑15 — Updated to 12-char pattern names; added title and category fields; pattern events include all fields.
- 1.3.0 — 2025‑09‑14 — Added compiler validation flow clarification; patterns only process syntactically valid code.
- 1.2.0 — 2025‑09‑14 — Added --validate-patterns design and validation flow.
- 1.1.0 — 2025‑09‑14 — Incorporated Claude's safeguards (timeout, filename fix, 3.8 typing, validation, size caps).  
- 1.0.0 — 2025‑09‑14 — Initial draft.