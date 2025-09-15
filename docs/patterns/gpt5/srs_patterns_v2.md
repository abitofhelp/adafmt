# Software Requirements Specification (SRS)
# adafmt — Pattern Formatter Layer

**Document Version:** 1.1.0  
**Date:** September 14, 2025  
**Status:** Draft (post-Claude review)  
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

### 1.3 Definitions
- **ALS** – Ada Language Server (formatting engine).  
- **Pattern** – a (find, replace[, flags]) rule applied sequentially to text.  
- **Pat Log** – dedicated JSONL log file for pattern activity: `adafmt_<timestamp>_patterns.log`.

---

## 2. Overall Description

### 2.1 Perspective
The Pattern Formatter is a **post‑processing** stage in the adafmt pipeline, independent of ALS. It consumes ALS output and produces a possibly further‑normalized buffer according to project rules.

### 2.2 Users
- **CLI Users** (developers, CI).  
- **Maintainers** authoring rules and auditing logs.

### 2.3 Assumptions
- ALS is reachable and returns edits for formatted text.  
- Ada files are small enough to process in memory.  
- Patterns are authored by trusted users (no untrusted input).

---

## 3. Functional Requirements

### FR‑1 CLI & Discovery
- **FR‑1.1** Default path: `./adafmt_patterns.json` (CWD).  
- **FR‑1.2** Override with `--patterns-path <FILE>`.  
- **FR‑1.3** Bypass with **`--no-patterns`** (still show `patterns=0` and emit Pat Log).

### FR‑2 Loading, Validation & Safety
- **FR‑2.1** On launch, load the patterns JSON into memory and **close** the file handle immediately (also on exception or signal).  
- **FR‑2.2** Validate each rule against schema (see §4). Invalid rules are **skipped** with TTY warning and Pat Log `pattern_error`.  
- **FR‑2.3** Compile regexes at load time; any compile error marks the rule invalid.  
- **FR‑2.4** If file missing or zero valid rules: Pattern Formatter is **enabled=false** with **`patterns=0`** display.  
- **FR‑2.5** **Regex timeout protection:** All regex substitutions MUST use a timeout to mitigate ReDoS (see §5, §6). A timeout results in a `pattern_timeout` event; the offending rule is skipped for that file, and the run continues.  
- **FR‑2.6** **File size limit:** If the ALS‑formatted buffer or source exceeds **10 MiB** (configurable), **skip** patterns for that file and emit `file_skipped_large` in Pat Log.

### FR‑3 Per‑File Execution
- **FR‑3.1** If ALS fails: **skip** patterns for that file; record in logs; continue.  
- **FR‑3.2** If ALS succeeds: apply patterns **sequentially**, sorted by `name` ascending.  
- **FR‑3.3** Count replacements per pattern using substitution with timeout; collect per‑file applied pattern list and total replacements.  
- **FR‑3.4** Respect **dry run** vs **write**: without `--write`, do not persist file changes.

### FR‑4 UI / TTY
- **FR‑4.1** Per‑file status line (after ALS info):  
  `… | Patterns: patterns=<N> applied=<K> (+<R>) | mode=DRY|WRITE`  
- **FR‑4.2** Footer adds a new line **under “Log”** labeled **“Pat Log”** showing `adafmt_<timestamp>_patterns.log`.  
- **FR‑4.3** On process exit, print **four** paths in order: `Log`, `Pat Log`, `Stderr`, `ALS`.  
- **FR‑4.4** Display `patterns=0` whenever no patterns are active.

### FR‑5 Metrics
- **FR‑5.1** Track per pattern: `files_touched` and `replacements`.  
- **FR‑5.2** End‑of‑run **Extra Metrics**: list patterns with `files_touched > 0` showing both counters.  
- **FR‑5.3** Include summary in Pat Log `run_end` event.

### FR‑6 Logging (Pat Log)
- **FR‑6.1** Create `adafmt_<timestamp>_patterns.log` (JSONL) once at startup.  
- **FR‑6.2** Emit events: `run_start`, `file`, `file_skipped_large`, `pattern`, `pattern_error`, `pattern_timeout`, `run_end`.  
- **FR‑6.3** Open once, flush per write, close on shutdown; share the run timestamp with other logs.

### FR‑7 Fault Isolation
- **FR‑7.1** Pattern errors/timeouts must **not** break the formatting pipeline.  
- **FR‑7.2** Always continue with the next pattern/file as applicable.

---

## 4. Data Requirements (Schema)

### 4.1 JSON Schema (v1)
Each entry is an object with fields:
- `name` (string, REQUIRED): exactly 10 chars, `^[a-z0-9_-]{10}$`, **unique**.  
- `find` (string, REQUIRED): regex pattern.  
- `replace` (string, REQUIRED): replacement (may be empty for deletions).  
- `flags` (array of string, OPTIONAL): subset of `["MULTILINE","IGNORECASE","DOTALL"]`.  
- `comment` (string, OPTIONAL).

### 4.2 Uniqueness
- **Required:** `name` must be unique.

---

## 5. Non‑Functional Requirements

- **NFR‑1 Performance:** ≤50 rules; sequential application; must not materially exceed ALS time.  
- **NFR‑2 Determinism:** Sorted by `name`.  
- **NFR‑3 Reliability:** Atomic writes on `--write`; logs always flushed.  
- **NFR‑4 Security:** **Regex timeout enforced** to prevent ReDoS; pattern file is trusted input.  
- **NFR‑5 Portability:** Prefer pure Python; use third‑party `regex` library to provide timeout (fallback documented).

---

## 6. Configurability

- `--pattern-timeout-ms` (default **50 ms**) — timeout per rule application against a file.  
- `--patterns-max-bytes` (default **10485760 bytes / 10 MiB**) — skip patterns for larger files.

---

## 7. Acceptance Criteria

- Missing/empty patterns file ⇒ `patterns=0`, Pat Log produced.  
- ALS failure on a file ⇒ patterns skipped for that file.  
- Footer shows **Pat Log** line; TTY prints four paths on exit.  
- Pattern timeouts generate `pattern_timeout` and do not stop the run.  
- Files over 10 MiB generate `file_skipped_large` and continue.  
- End‑of‑run summary lists only patterns with `files_touched > 0`.

---

## 8. Risks & Mitigations
- **Regex performance traps** → mandatory timeout; pre‑compile; keep patterns simple.  
- **Large files** → max‑bytes guard with skip event.  
- **Disk errors** → atomic write and continue.

---

## 9. History
- 1.1.0 — 2025‑09‑14 — Incorporated Claude’s safeguards (timeout, filename fix, size cap, validation).  
- 1.0.0 — 2025‑09‑14 — Initial draft.