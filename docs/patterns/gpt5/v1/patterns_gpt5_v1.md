got it—here’s the updated, copy-pasteable spec that folds in your **Pat Log** line, the **`--no-patterns`** flag, the **`patterns=0`** display tweak, and the exact filename you chose: **`adafmt_<timestamp>_paterns.log`** (note spelling). I read your SRS/SDD and kept everything consistent with the single shared timestamp, footer layout, and logging discipline (open once, flush each write, close on shutdown). &#x20;

# Pattern Formatter — Design v3 (updates)

## What changed (delta from v2)

* **New flag:** `--no-patterns` to bypass the Pattern Formatter layer entirely (still shows `patterns=0` and emits the Pat Log line/path, but no rules are loaded or run).
* **Footer UI:** Insert a **new 4th line** directly **under “Log”** labeled **“Pat Log”** showing the pattern log path. The remaining lines shift down:

  1. Stats
  2. Timing
  3. **Log:** JSONL application log (unchanged)
  4. **Pat Log:** pattern activity JSONL log (**new**)
  5. **Stderr:** stderr capture log (unchanged)
  6. **ALS Log:** server log location hint (unchanged)
     (SDD previously showed 5 lines; we extend to 6 to accommodate Pat Log per your instruction.)&#x20;
* **TTY on exit:** print **four paths** in order: `Log`, `Pat Log`, `Stderr`, `ALS` (previously three).
* **Pat Log filename:** `./adafmt_<timestamp>_paterns.log` (created once per run; same startup timestamp as the other logs). Keep the same open/flush/close lifecycle and “(default location)” suffix semantics as your JSONL/stderr logs.&#x20;
* **Per-file status line tweak:** where v2 said `Patterns: loaded=N …`, now display **`Patterns: patterns=N applied=K (+R)`**. When no file is found or `--no-patterns` is set, show **`patterns=0`** (exact wording you asked for).
* **Startup banner tweak:** after ALS status, show **`patterns=N`** (not “loaded=…”).

---

## CLI & Config (with new flags)

* **Default patterns file:** `./adafmt_patterns.json`
* **Override:** `--patterns-path <FILE>`
* **Bypass:** **`--no-patterns`** (skip loading/applying patterns; UI still shows `patterns=0` and prints Pat Log path)
* **Write behavior:** no `--write` → **DRY RUN**; with `--write` → apply ALS edits + pattern changes (unchanged from SRS).&#x20;

---

## Logs (now 3 files with shared timestamp)

All logs use the **single run timestamp** generated once at startup and share the same lifecycle (opened once, flush each write, closed on shutdown).&#x20;

1. **JSONL app log** (existing): `./adafmt_<timestamp>_log.jsonl`
2. **Pat Log** (**new**): `./adafmt_<timestamp>_paterns.log`

   * **Format:** JSON Lines
   * **Events:** `run_start`, `file`, `pattern`, `pattern_error`, `run_end` (as in v2; unchanged)
   * **Created** even if `--no-patterns` is set (so the path is stable for UIs/automation; contents will be a minimal `run_start`/`run_end`)
3. **Stderr log** (existing): `./adafmt_<timestamp>_stderr.log`

ALS’ own log path hint remains in the footer/TTY as before.&#x20;

---

## UI / TTY

### Footer (Pretty/Basic/Plain UIs)

* Keep your **fixed-width**, **multi-line** footer style and ordering, adding one new line:

```
Line 1: Files: <totals> | … (unchanged)
Line 2: Elapsed: … | Rate: … (unchanged)
Line 3: Log:     ./adafmt_<ts>_log.jsonl (default location)          (unchanged)
Line 4: Pat Log: ./adafmt_<ts>_paterns.log (default location)        (**new**)
Line 5: Stderr:  ./adafmt_<ts>_stderr.log (default location)         (unchanged)
Line 6: ALS Log: ~/.als/ada_ls_log.*.log (default location)          (unchanged)
```

* Where v2 printed `loaded=0`, now print **`patterns=0`** in **all** modes.
* Immediately after ALS status in per-file lines, print:

  ```
  <file> — ALS: ✓ edits=<n> | Patterns: patterns=<N> applied=<K> (+<R>) | mode=DRY|WRITE
  ```

  (If `--no-patterns`, show `patterns=0 applied=0 (+0)`.)

These adjustments preserve your **fixed positions** and **default path formatting** conventions, aligning with SRS/SDD footer rules.&#x20;

### TTY “final paths” (just before exit)

Print the four lines (in this order):

```
Log:     ./adafmt_<ts>_log.jsonl (default location)
Pat Log: ./adafmt_<ts>_paterns.log (default location)
Stderr:  ./adafmt_<ts>_stderr.log (default location)
ALS Log: ~/.als/ada_ls_log.*.log (default location)
```

---

## Runtime flow (unchanged, with wording tweaks)

* **ALS fails for a file:** mark failed; **skip** patterns; continue.
* **ALS succeeds:** apply patterns **sequentially** (sorted by `name`), collect `replacements`.
* **Dry-run vs write:** honors **`--write`** exactly as ALS does today—Pattern Formatter is gated by the same flag. (Matches SRS FR-5 output modes.)&#x20;
* **End-of-run “Extra Metrics”:** list patterns with `files_touched > 0`, showing `files` and `replacements` (same as v2).

---

## Where it plugs into your current code (by file)

* **`cli.py`**

  * **Args:** add `--patterns-path` and **`--no-patterns`**.
  * **Startup:** compute the shared `<timestamp>` (already in your SDD); derive **`pat_log_path = ./adafmt_<ts>_paterns.log`**; open a second JSONL logger instance for patterns using the same open/flush/close discipline as the main logger.&#x20;
  * **Load:** if `--no-patterns` → skip load, record `patterns=0`, still emit `run_start` in Pat Log with `patterns_loaded:0`.
  * **Per file:** after ALS + `apply_text_edits`, call Pattern Formatter (unless `--no-patterns` or `patterns=0`); pass **per-file** stats to the UI line.
  * **Footer calls:** extend your `update_footer_stats(…, jsonl_log, als_log, stderr_log)` to also accept `pattern_log`, and pass **Pat Log** path.
  * **Exit:** print **four** path lines (Log, Pat Log, Stderr, ALS) instead of three.

* **`tui.py`**

  * Extend UI state to hold **`footer_pattern_log`**.
  * Update **`update_footer_stats`** signature to accept `pattern_log: str`.
  * Render the **new 4th line** (“Pat Log: …”) consistently in Pretty/Basic/Plain modes, using the same color rules as “Log/Stderr/ALS”.

* **`logging_jsonl.py`**

  * **No functional change needed.** Instantiate the existing `JsonlLogger` a second time for Pat Log; same behavior (open once, flush each write, close at shutdown), aligned with SDD/SRS logging guarantees.&#x20;

* **`pattern_formatter.py`** (from v2 skeleton)

  * No structural changes; only the UI strings (“patterns=N”) and per-file/summary JSONL events feed into the **Pat Log**.

---

## Pat Log — JSONL events (unchanged from v2)

Examples (same structure, just to confirm):

* **run\_start**

  ```json
  {"ev":"run_start","ts":"…","patterns_path":"./adafmt_patterns.json","patterns_loaded":7,"mode":"DRY"}
  ```
* **file**

  ```json
  {"ev":"file","ts":"…","path":"src/foo.adb","als_ok":true,"als_edits":12,"patterns_applied":["cmntspc01","cmnteol02"],"replacements":14}
  ```
* **pattern** / **pattern\_error**

  ```json
  {"ev":"pattern","ts":"…","path":"src/foo.adb","name":"cmntspc01","replacements":3}
  {"ev":"pattern_error","ts":"…","path":"src/foo.adb","name":"cmnteol02","error":"replacement group out of range"}
  ```
* **run\_end**

  ```json
  {"ev":"run_end","ts":"…","files_total":64,"files_als_ok":62,"patterns_loaded":7,
   "patterns_summary":{"cmntspc01":{"files_touched":12,"replacements":37}, "cmnteol02":{"files_touched":8,"replacements":19}}}
  ```

---

## Why this aligns with your SRS/SDD

* **Single shared timestamp** for all log files per run → easy correlation.&#x20;
* **Logs opened once, flushed per write, closed on shutdown** → performance + crash safety.&#x20;
* **Footer layout** remains fixed/stable; we’ve just inserted “Pat Log” under “Log” without disturbing your formatting guarantees.&#x20;
* **Dry-run default** and **`--write`** semantics preserved; **`--check`** remains meaningful.&#x20;
* **Fail-safe:** errors never block other files; ALS failure skips patterns for that file (as before).&#x20;

---

## Next concrete steps (if you want me to wire it)

1. Add CLI flags (`--patterns-path`, `--no-patterns`), derive `pat_log_path = ./adafmt_<ts>_paterns.log` (default).
2. Instantiate a second `JsonlLogger` for the Pat Log.
3. Extend `tui.update_footer_stats(…, pattern_log)` and render the **“Pat Log:”** line.
4. Swap all user-facing `loaded=0` strings to **`patterns=0`**.
5. Print the four final log paths (Log, Pat Log, Stderr, ALS) before exit.

If you want, I can produce minimal diffs against your current `cli.py` and `tui.py` to make this 100% turnkey.
