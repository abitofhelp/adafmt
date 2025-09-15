# Software Design Description (SDD)
# adafmt — Pattern Formatter Layer

**Document Version:** 1.0.0  
**Date:** September 14, 2025  
**Status:** Draft (for review by Claude)

---

## 1. Architecture Overview

The Pattern Formatter is a **post‑ALS** stage. It loads a set of compiled regex rules at startup, keeps them immutable, and applies them sequentially to ALS‑formatted buffers. It reports activity to the UI/TTY, emits a dedicated Pat Log (`adafmt_<timestamp>_paterns.log`), and contributes to the Extra Metrics section.

```
┌──────────────┐     ┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│ File Walker  │ --> │   ALS        │ --> │ Pattern Formatter  │ --> │ Atomic Write │
└──────────────┘     └──────────────┘     └────────────────────┘     └──────────────┘
                                     \--> UI/TTY status + Pat Log
```

---

## 2. Key Components

### 2.1 PatternFormatter
- **State:**
  - `rules: Tuple[CompiledRule]` (sorted by `name`)
  - `enabled: bool`, `loaded_count: int`
  - `files_touched: Dict[name,int]`
  - `replacements: Dict[name,int]`
- **Methods:**
  - `load_from_json(path, logger, ui) -> PatternFormatter`
  - `apply(path: Path, text: str, logger=None, ui=None) -> (out: str, FileApplyResult)`
- **Error handling:** skip invalid rules; log warnings; continue on per‑pattern runtime error.

### 2.2 CompiledRule
- `name: str` (10‑char slug)  
- `find: re.Pattern`  
- `replace: str`

### 2.3 FileApplyResult
- `applied_names: List[str]` — distinct pattern names that changed the file  
- `replacements_sum: int` — total replacements across patterns

### 2.4 Pattern JSON Loader
- Validates schema, compiles regex (maps `flags` to Python `re` flags), and returns immutable rule set.
- Closes the file immediately after reading (also on exceptions).

---

## 3. CLI & Configuration

- **`--patterns-path <FILE>`** — override default `./adafmt_patterns.json`.  
- **`--no-patterns`** — disable loading and applying patterns; still produce Pat Log with `patterns_loaded:0`.  
- **`--write`** — apply changes to disk; absence implies **dry run**.

Environment variables and project config remain unchanged.

---

## 4. UI / TUI Integration

### 4.1 Per‑File Status Line
Append to the existing ALS line:

```
ALS: ✓ edits=<n> | Patterns: patterns=<N> applied=<K> (+<R>) | mode=DRY|WRITE
```

### 4.2 Footer (Pretty/Basic/Plain)
Insert **“Pat Log”** line **under “Log”** and above “Stderr”:

```
Log:     ./adafmt_<ts>_log.jsonl (default location)
Pat Log: ./adafmt_<ts>_paterns.log (default location)
Stderr:  ./adafmt_<ts>_stderr.log (default location)
ALS Log: ~/.als/ada_ls_log.*.log (default location)
```

### 4.3 TTY Exit Paths
Print the same four lines (Log, Pat Log, Stderr, ALS) before process exit.

---

## 5. Logging — Pattern JSONL (Pat Log)

- **Filename:** `adafmt_<timestamp>_paterns.log` (created once per run).  
- **Open/close:** open once, flush on each write, close on shutdown.  
- **Events** (JSONL objects, one per line):
  - `run_start`: `{ev, ts, patterns_path, patterns_loaded, mode}`
  - `file`: `{ev, ts, path, als_ok, als_edits, patterns_applied[], replacements}`
  - `pattern`: `{ev, ts, path, name, replacements}` (only when `replacements>0`)
  - `pattern_error`: `{ev, ts, path, name, error}`
  - `run_end`: `{ev, ts, files_total, files_als_ok, patterns_loaded, patterns_summary{ name:{files_touched, replacements} }}`

Re‑use the existing `JsonlLogger` implementation; instantiate a second logger instance for Pat Log. Share the same startup timestamp as other logs.

---

## 6. Control Flow

### 6.1 Startup
1. Parse CLI (capture `--no-patterns`, `--patterns-path`, `--write`).  
2. Create shared `<timestamp>` for the run.  
3. Initialize logs, including **Pat Log** path.  
4. If not `--no-patterns`: load and compile rules from JSON; else set `enabled=false` and `loaded_count=0`.  
5. Emit Pat Log `run_start` event.

### 6.2 Per File
1. Run ALS; if failure → log, Pat Log `file` with `als_ok=false`, **skip** patterns.  
2. If success → apply rules sequentially; gather `applied_names` and `replacements_sum`.  
3. Emit Pat Log `file` + `pattern` events for each rule with `replacements>0`.  
4. If `--write` and buffer changed → atomic write.  
5. Update UI per‑file status line.

### 6.3 Shutdown
1. Render **Extra Metrics**: list patterns with `files_touched>0`.  
2. Emit Pat Log `run_end` with `patterns_summary`.  
3. Print four final paths (Log, Pat Log, Stderr, ALS).  
4. Close all logs.

---

## 7. Data Structures

```python
@dataclass(frozen=True)
class CompiledRule:
    name: str
    find: re.Pattern
    replace: str

@dataclass
class FileApplyResult:
    applied_names: list[str]
    replacements_sum: int

class PatternFormatter:
    _rules: tuple[CompiledRule]
    enabled: bool
    loaded_count: int
    files_touched: dict[str,int]
    replacements: dict[str,int]
```

---

## 8. Error Handling

- **Load errors**: skip bad entries; if none left → enabled=false (`patterns=0`).  
- **Runtime errors**: continue to next pattern; TTY red `[name]`; Pat Log `pattern_error`.  
- **Write failures**: log error, keep original file, continue.

---

## 9. Performance & Determinism

- Sequential application of ≤50 rules; adequate for typical Ada files.  
- Deterministic ordering by `name` ascending.  
- No parallelism to avoid reordering/race conditions.

---

## 10. Security Considerations

- Patterns authored by trusted users; document risks of pathological regexes.  
- Consider optional future switch to the third‑party `regex` lib with timeouts.

---

## 11. Testing Strategy

- **Unit tests:** loader validation, regex compilation, substitution counts, metrics aggregation.  
- **Golden tests:** before/after fixtures for representative Ada files.  
- **CLI tests:** `--no-patterns`, missing file, dry vs write.  
- **Integration:** end‑to‑end run with ALS mock returning edits and failure modes.

---

## 12. Document History
- 1.0.0 — 2025‑09‑14 — Initial draft for review.