# Software Requirements Specification (SRS)
# adafmt — Pattern Formatter Layer

**Document Version:** 1.0.0  
**Date:** September 14, 2025  
**Status:** Draft (for review by Claude)  
**Applies To:** adafmt ≥ next minor version

---

## 1. Introduction

### 1.1 Purpose
This SRS defines the functional and non‑functional requirements for the **Pattern Formatter** layer in **adafmt**. The layer post‑processes Ada source after ALS formatting to enforce additional whitespace/spacing and style rules that ALS/GNATformat do not standardize (e.g., ` --  `, operator spacing).

### 1.2 Scope
- Runs **after** ALS successfully formats a file.  
- If ALS fails for a file, patterns are **skipped** for that file.  
- Patterns are defined in a **JSON** file, loaded **once** at startup into an in‑memory, read‑only structure and the file handle is **closed immediately**.  
- User experience: reports pattern activity in per‑file status lines, a footer “Pat Log” path, and an end‑of‑run summary.  
- Honors adafmt’s **dry run** (no `--write`) vs **write** (`--write`) semantics.

### 1.3 Definitions, Acronyms, Abbreviations
- **ALS** – Ada Language Server (formatting engine).  
- **Pattern** – a (find, replace[, flags]) rule applied sequentially to text.  
- **Pat Log** – dedicated JSONL log file for pattern activity: `adafmt_<timestamp>_paterns.log`.

### 1.4 References
- adafmt SRS/SDD (main documents).

---

## 2. Overall Description

### 2.1 Product Perspective
The Pattern Formatter is a **post‑processing** stage in the adafmt pipeline, independent of ALS. It consumes ALS output and produces a possibly further normalized buffer according to project rules.

### 2.2 User Classes & Characteristics
- **CLI Users** (developers, CI): need deterministic formatting and actionable logs.
- **Maintainers**: need simple authoring of rules and clear failures.

### 2.3 Assumptions & Dependencies
- ALS is reachable and returns edits for formatted text.  
- Ada files are small enough to process in memory.  
- Patterns are authored by trusted users (no untrusted input).

---

## 3. Functional Requirements

### FR‑1 Patterns File Discovery & Flags
- **FR‑1.1** Default path: `./adafmt_patterns.json` (CWD).  
- **FR‑1.2** Override with `--patterns-path <FILE>`.  
- **FR‑1.3** Bypass entirely with **`--no-patterns`** (still show `patterns=0` and emit Pat Log).

### FR‑2 Loading & Validation
- **FR‑2.1** On launch, load the patterns JSON into memory and **close** the file handle immediately (also on exception or signal).  
- **FR‑2.2** For each rule, validate schema (see §4) and **compile** the regex.  
- **FR‑2.3** Invalid rules are **skipped** with TTY warning and Pat Log `pattern_error`; valid rules proceed.  
- **FR‑2.4** If file missing or zero valid rules: Pattern Formatter is **enabled=false** with **`patterns=0`** display.

### FR‑3 Per‑File Execution
- **FR‑3.1** If ALS fails: **skip** patterns for that file; record in logs; continue.  
- **FR‑3.2** If ALS succeeds: apply patterns **sequentially**, sorted by `name` ascending.  
- **FR‑3.3** Count replacements per pattern using regex `subn()`; collect per‑file applied pattern list and total replacements.  
- **FR‑3.4** Respect **dry run** vs **write**: without `--write`, do not persist file changes.

### FR‑4 UI & TTY
- **FR‑4.1** Per‑file status line (after ALS info):  
  `… | Patterns: patterns=<N> applied=<K> (+<R>) | mode=DRY|WRITE`  
- **FR‑4.2** Footer adds a new line **under “Log”** labeled **“Pat Log”** showing `adafmt_<timestamp>_paterns.log`.  
- **FR‑4.3** On process exit, print **four** paths in order: `Log`, `Pat Log`, `Stderr`, `ALS`.  
- **FR‑4.4** Display `patterns=0` (not “loaded=0”) whenever no patterns are active.

### FR‑5 Metrics
- **FR‑5.1** Track per pattern: `files_touched` (files where it changed ≥1) and `replacements` (total matches).  
- **FR‑5.2** End‑of‑run **Extra Metrics**: list patterns with `files_touched > 0` showing both counters.  
- **FR‑5.3** Include summary in Pat Log `run_end` event.

### FR‑6 Logging (Pat Log)
- **FR‑6.1** Create `adafmt_<timestamp>_paterns.log` (JSON Lines) once at startup.  
- **FR‑6.2** Emit events: `run_start`, `file`, `pattern`, `pattern_error`, `run_end`.  
- **FR‑6.3** Open once, flush per write, close on shutdown; share the run timestamp with other logs.

### FR‑7 Failure Behavior
- **FR‑7.1** Never block formatting of other files due to pattern errors.  
- **FR‑7.2** Per‑pattern runtime error → red tag `[name]` on TTY + `pattern_error` event; continue to next pattern.

---

## 4. Data Requirements (Schema)

### 4.1 JSON Schema (v1)
Each entry is an object with fields:
- `name` (string, REQUIRED): exactly 10 chars, `^[a-z0-9_-]{10}$`, **unique** in file.  
- `find` (string, REQUIRED): Python regex (sed backrefs permitted).  
- `replace` (string, REQUIRED): replacement (may be empty for deletions).  
- `flags` (array of string, OPTIONAL): subset of `["MULTILINE","IGNORECASE","DOTALL"]`.  
- `comment` (string, OPTIONAL).

### 4.2 Uniqueness Policy
- **Required:** `name` must be unique.  
- **Optional future:** a strict mode may enforce additional uniqueness (e.g., `name+find`).

---

## 5. Non‑Functional Requirements

- **NFR‑1 Performance:** Sequential application of ≤50 rules over small files; must not exceed ALS time materially.  
- **NFR‑2 Determinism:** Order is stable (sorted by `name`).  
- **NFR‑3 Reliability:** Atomic writes on `--write`; skip on failures; logs always flushed.  
- **NFR‑4 Security:** No untrusted patterns; document DoS risks of pathological regexes.  
- **NFR‑5 Portability:** Pure Python `re`; no external `sed` dependency.

---

## 6. Acceptance Criteria

- Missing/empty patterns file ⇒ `patterns=0`, Pat Log produced, no crashes.  
- ALS failure on any file ⇒ patterns skipped for that file; others proceed.  
- Footer shows new **Pat Log** line; TTY prints four paths on exit.  
- End‑of‑run summary lists only patterns with `files_touched > 0`.  
- Pat Log contains `run_start`, per‑file, per‑pattern (when n>0), and `run_end` with summary.

---

## 7. Risks & Mitigations
- **Regex performance traps** → pre‑compile at load; keep patterns simple; document policy.  
- **User confusion on modes** → per‑file line shows `mode=DRY|WRITE`.  
- **Disk errors on write** → atomic replace with error handling; continue run.

---

## 8. Future Enhancements (Non‑binding)
- `--patterns-diff` for CI dry‑run diffs.  
- Per‑rule `applies_to` globs.  
- Strict uniqueness flag.  
- `regex` module with timeouts (opt‑in).

---

## 9. Document History
- 1.0.0 — 2025‑09‑14 — Initial draft for review.