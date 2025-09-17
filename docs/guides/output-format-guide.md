# Output Format Guide

**Version:** 0.0.0  
**Last Updated:** September 2025

This guide explains the comprehensive output format displayed after adafmt completes a formatting run, helping you understand the metrics, performance data, and log file information.

---

## Output Modes

adafmt displays different metrics depending on which components are enabled:

### Both ALS and Patterns (Default)

When both ALS and patterns are enabled, you'll see comprehensive metrics from both:

```
================================================================================
ALS METRICS
  Files      303  100%
  Changed    182   60%
  Unchanged  115   37%
  Failed       6    1%
  Started    20250916T013452Z
  Completed  20250916T013518Z
  Elapsed    23.1s
  Rate       11.8 files/s

PATTERN METRICS
  Files           303  100%

  Pattern         Applied    Replaced    Failed
  ------------  ---------  ----------  --------
  assign_set01        130        3092         0
  assoc_arrow1        126        7404         0
  attr_tick_01          4          13         0
  cmt_whole_01        182        6579         0
  comma_space1        180        3066         0
  comment_eol1         85         408         0
  decl_colon01        175        4819         0
  paren_l_sp01          1           3         0
  paren_r_sp01          1           2         0
  range_dots01         78         284         0
  ws_trail_sp1        128        3941         0
  --------        -------    --------    ------
  Totals             1090       29611         0

  Started              20250916T013502Z
  Completed            20250916T013518Z
  Elapsed              2.6s
  Rate (scanned)       117.9 files/s
  Rate (applied)       424.2 patterns/s
  Rate (replacements)  11524.3 replacements/s

ADAFMT RUN
  Started        20250916T013452Z
  Completed      20250916T013518Z
  Total Elapsed  25.7s

LOG FILES
  Main Log     ./adafmt_20250916T013452Z_log.jsonl (default location)
  Pattern Log  ./adafmt_20250916T013452Z_patterns.log (default location)
  Stderr       ./adafmt_20250916T013452Z_stderr.log (default location)
  ALS Log      ~/.als/ada_ls_log.*.log (default location)
================================================================================
```

---

## Section-by-Section Breakdown

### 🔧 ALS METRICS Section

This section shows statistics from the Ada Language Server (ALS) formatting process:

```
ALS METRICS
  Files      303  100%    ← Total files processed by ALS
  Changed    182   60%    ← Files that had formatting changes applied
  Unchanged  115   37%    ← Files that needed no formatting changes
  Failed       6    1%    ← Files that couldn't be formatted (syntax errors, etc.)
  Started    20250916T013452Z  ← When ALS processing began (ISO 8601 UTC)
  Completed  20250916T013518Z  ← When ALS processing finished
  Elapsed    23.1s        ← Total time spent on ALS formatting
  Rate       11.8 files/s ← ALS processing rate (files per second)
```

#### Understanding ALS Metrics

- **Files**: Total number of Ada files discovered and sent to ALS for formatting
- **Changed**: Files where ALS made formatting modifications
- **Unchanged**: Files that were already properly formatted according to ALS
- **Failed**: Files that couldn't be formatted (usually due to syntax errors)
- **Percentages**: Show the distribution of results (should total ~100%)
- **Rate**: Processing speed - higher rates indicate better performance

#### What Good ALS Metrics Look Like

- **High Unchanged %**: Indicates your code is already well-formatted
- **Low Failed %**: Shows most files have correct Ada syntax
- **Reasonable Rate**: 10+ files/s is typical; very large files may be slower

### 🎨 PATTERN METRICS Section

This section shows statistics from the custom pattern formatter system:

```
PATTERN METRICS
  Files           303  100%                       ← Total files scanned for patterns

  Pattern         Applied    Replaced    Failed
  ------------  ---------  ----------  --------
  assign_set01        130        3092         0   ← Each pattern's statistics
  assoc_arrow1        126        7404         0
  ...
  --------        -------    --------    ------
  Totals             1090       29611         0   ← Summary across all patterns
```

#### Column Definitions

- **Pattern**: Name of the pattern rule (from your pattern configuration file)
- **Applied**: Number of files where this pattern found and processed matches
- **Replaced**: Total number of text replacements made by this pattern
- **Failed**: Number of times this pattern encountered errors (timeouts, regex issues)

#### Timing and Performance

```
  Started              20250916T013502Z  ← When pattern processing began
  Completed            20250916T013518Z  ← When pattern processing finished
  Elapsed              2.6s              ← Total time for all pattern processing
  Rate (scanned)       117.9 files/s     ← Files examined per second
  Rate (applied)       424.2 patterns/s  ← Pattern applications per second
  Rate (replacements)  11524.3 replacements/s ← Text replacements per second
```

#### Understanding Pattern Metrics

**High-Impact Patterns** (many replacements):
- `cmt_whole_01`: 6579 replacements - comment formatting
- `assoc_arrow1`: 7404 replacements - arrow operator spacing
- `decl_colon01`: 4819 replacements - declaration colon formatting

**Selective Patterns** (few applications):
- `paren_l_sp01`: 3 replacements - very specific spacing rules
- `attr_tick_01`: 13 replacements - attribute tick formatting

#### What Good Pattern Metrics Look Like

- **Zero Failed**: All patterns should execute without errors
- **High Rate**: 100+ files/s scanning indicates good performance
- **Appropriate Replacements**: More replacements = more style consistency improvements

### 📊 ADAFMT RUN Section

This section shows the overall execution summary:

```
ADAFMT RUN
  Started        20250916T013452Z  ← Overall adafmt execution start
  Completed      20250916T013518Z  ← Overall adafmt execution end
  Total Elapsed  25.7s             ← End-to-end execution time
```

#### Understanding Run Metrics

- **Total Elapsed**: Complete time from adafmt startup to final output
- **Includes**: File discovery, ALS processing, pattern processing, and cleanup
- **Performance Indicator**: Should scale reasonably with project size

### 📁 LOG FILES Section

This section shows where detailed logs were written:

```
LOG FILES
  Main Log     ./adafmt_20250916T013452Z_log.jsonl (default location)
  Pattern Log  ./adafmt_20250916T013452Z_patterns.log (default location)
  Stderr       ./adafmt_20250916T013452Z_stderr.log (default location)
  ALS Log      ~/.als/ada_ls_log.*.log (default location)
```

#### Log File Types

- **Main Log**: Structured JSON Lines log with detailed per-file results
- **Pattern Log**: Human-readable log of pattern processing activity
- **Stderr**: ALS error output and diagnostic information
- **ALS Log**: Ada Language Server's internal debug logs

#### Log File Locations

- **Default Location**: Same directory where adafmt was run
- **Timestamp**: All logs share the same timestamp (start time of the run)
- **Custom Paths**: Can be overridden with `--log-path`, `--stderr-path` flags

### ALS-Only Mode (--no-patterns)

When patterns are disabled with `--no-patterns`, only ALS metrics are shown:

```
================================================================================
ALS METRICS
  Files      303  100%
  Changed    182   60%
  Unchanged  115   37%
  Failed       6    1%
  Started    20250916T013452Z
  Completed  20250916T013518Z
  Elapsed    23.1s
  Rate       11.8 files/s

ADFMT RUN
  Started        20250916T013452Z
  Completed      20250916T013518Z
  Total Elapsed  23.1s

LOG FILES
  Main Log     ./adafmt_20250916T013452Z_log.jsonl (default location)
  Pattern Log  ./adafmt_20250916T013452Z_patterns.log (default location)
  Stderr       ./adafmt_20250916T013452Z_stderr.log (default location)
  ALS Log      ~/.als/ada_ls_log.*.log (default location)
================================================================================
```

### Patterns-Only Mode (--no-als)

When ALS is disabled with `--no-als`, only pattern metrics are shown:

```
================================================================================
PATTERN METRICS
  Files           303  100%

  Pattern         Applied    Replaced    Failed
  ------------  ---------  ----------  --------
  assign_set01        130        3092         0
  assoc_arrow1        126        7404         0
  attr_tick_01          4          13         0
  cmt_whole_01        182        6579         0
  comma_space1        180        3066         0
  comment_eol1         85         408         0
  decl_colon01        175        4819         0
  paren_l_sp01          1           3         0
  paren_r_sp01          1           2         0
  range_dots01         78         284         0
  ws_trail_sp1        128        3941         0
  --------        -------    --------    ------
  Totals             1090       29611         0

  Started              20250916T013452Z
  Completed            20250916T013456Z
  Elapsed              4.1s
  Rate (scanned)       73.9 files/s
  Rate (applied)       265.9 patterns/s
  Rate (replacements)  7221.7 replacements/s

ADFMT RUN
  Started        20250916T013452Z
  Completed      20250916T013456Z
  Total Elapsed  4.1s

LOG FILES
  Main Log     ./adafmt_20250916T013452Z_log.jsonl (default location)
  Pattern Log  ./adafmt_20250916T013452Z_patterns.log (default location)
  Stderr       ./adafmt_20250916T013452Z_stderr.log (default location)
================================================================================
```

---

## Understanding Metrics Differences

When using both ALS and patterns together, you'll notice that pattern metrics differ from patterns-only mode:

### Why Pattern Counts Differ

1. **Patterns-Only Mode (`--no-als`)**:
   - Patterns fix all formatting issues they can find
   - Higher pattern application count
   - More replacements made

2. **Combined Mode (default)**:
   - ALS formats files first
   - Patterns only fix what ALS missed or doesn't handle
   - Lower pattern application count
   - Fewer replacements needed

### Example Comparison

**Patterns-Only Mode:**
```
Pattern         Applied    Replaced
assign_set01         16          48
comment_eol1         12          24
decl_colon01         15          30
Totals               43         102
```

**Combined Mode (ALS + Patterns):**
```
Pattern         Applied    Replaced
assign_set01          3           9
comment_eol1          2           4
decl_colon01          1           2
Totals                6          15
```

This is expected behavior - ALS handles most standard formatting, leaving specialized pattern rules to handle specific cases or team preferences.

---

## Interpreting Results

### ✅ Successful Run Indicators

- **Low Failed %**: < 5% of files failed to format
- **Reasonable Rates**: ALS rate > 5 files/s, Pattern rate > 50 files/s
- **Zero Pattern Failures**: All patterns executed successfully
- **Consistent Timing**: Pattern processing much faster than ALS processing

### ⚠️ Warning Signs

- **High Failed %**: > 10% failures suggest syntax errors in your codebase
- **Very Low Rates**: < 1 file/s suggests performance issues or very large files
- **Pattern Failures**: Non-zero pattern failures indicate configuration issues
- **Very Long Elapsed**: Total time much longer than ALS + Pattern time

### 🚨 Troubleshooting Indicators

**When you see high failures:**
1. Check the Stderr log for syntax error details
2. Review failed files listed in the Main log
3. Consider excluding generated or problematic files

**When you see poor performance:**
1. Check system resources during the run
2. Review ALS log for performance warnings
3. Consider increasing timeout values
4. Look for very large files that might need special handling

**When patterns fail:**
1. Review Pattern log for specific error messages
2. Check pattern file syntax and regex validity
3. Verify pattern timeout settings

---

## Different UI Modes

The output format varies depending on the UI mode selected:

### Pretty UI Mode (`--ui pretty`)
- Shows the complete formatted output above
- Includes progress bars during processing
- Uses colors and formatting for better readability

### Plain UI Mode (`--ui plain`)
- Shows the same sections but with minimal formatting
- Suitable for CI/CD environments and log files
- No colors or special characters

### JSON UI Mode (`--ui json`)
- Outputs structured JSON Lines instead of formatted text
- Each section becomes a separate JSON event
- Suitable for programmatic processing

### Quiet UI Mode (`--ui quiet`)
- Minimal output focusing only on critical information
- Shows only failures and final summary
- Useful for automated scripts

---

## Using Output for Monitoring

### Performance Monitoring

Track these metrics over time to monitor your project's formatting health:

```bash
# Extract key metrics from JSON logs
cat adafmt_*_log.jsonl | jq '.summary | {files, changed, failed, elapsed_s, rate_files_per_s}'
```

### Quality Metrics

Monitor formatting consistency:
- **Decreasing Changed %**: Code is becoming more consistently formatted
- **Stable Pattern Applications**: Consistent style across the project
- **Low Failed %**: Good code quality and syntax correctness

### CI/CD Integration

Use the output format for automated quality gates:

```bash
# Example: Fail CI if too many files need changes
adafmt --project-path project.gpr --check --ui json | \
  jq -e '.summary.changed_pct < 10'  # Fail if >10% changed
```

---

## Log File Usage

### Main Log Analysis

```bash
# View failed files
cat adafmt_*_log.jsonl | jq 'select(.status == "failed") | {path, error}'

# View processing times
cat adafmt_*_log.jsonl | jq 'select(.duration_ms) | {path, duration_ms}' | \
  sort -k2 -nr | head -10  # Slowest files
```

### Pattern Log Analysis

```bash
# View pattern activity
grep "APPLIED" adafmt_*_patterns.log | head -20

# Find pattern errors
grep "ERROR" adafmt_*_patterns.log
```

### ALS Error Investigation

```bash
# Check ALS stderr for issues
cat adafmt_*_stderr.log | grep -i error

# Review ALS debug logs
tail -100 ~/.als/ada_ls_log.*.log | grep -i error
```

---

## See Also

- [Getting Started Guide](getting-started-guide.md) - Basic adafmt usage and examples
- [Troubleshooting Guide](troubleshooting-guide.md) - Solutions to common output issues
- [Configuration Guide](configuration-guide.md) - Customizing log paths and UI modes
- [Pattern Guide](patterns-guide.md) - Understanding and configuring pattern formatting

---

*This guide covers the standard output format. For debugging specific issues or understanding edge cases, see the [Troubleshooting Guide](troubleshooting-guide.md).*