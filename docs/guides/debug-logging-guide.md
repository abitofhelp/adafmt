# Debug Logging Guide

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This guide explains how to use adafmt's debug logging features to diagnose issues with pattern processing and ALS communication.

## Table of Contents

1. [Overview](#overview)
2. [Debug Pattern Logging](#debug-pattern-logging)
3. [Debug ALS Logging](#debug-als-logging)
4. [Analyzing Debug Logs](#analyzing-debug-logs)
5. [Common Debugging Scenarios](#common-debugging-scenarios)
6. [Performance Considerations](#performance-considerations)

## Overview

adafmt provides two specialized debug logging systems:
- **Pattern Debug Logging**: Detailed information about pattern matching and replacement
- **ALS Debug Logging**: Complete ALS communication traces including requests and responses

These debug logs are separate from the standard JSONL log and provide much more detailed information for troubleshooting.

### Debug Flag Design

Each debug system uses a two-flag approach:
1. **Enable flag**: Turns on debug logging with default output location
2. **Path flag**: Specifies custom output location (requires enable flag)

Example:
```bash
# Enable with default location
adafmt format --debug-patterns ...

# Enable with custom location
adafmt format --debug-patterns --debug-patterns-path /tmp/patterns.jsonl ...
```

## Debug Pattern Logging

### Enabling Pattern Debug Logs

```bash
# Default location: ./adafmt_<timestamp>_debug-patterns.jsonl
adafmt format --project-path project.gpr \
              --include-path src \
              --debug-patterns

# Custom location
adafmt format --project-path project.gpr \
              --include-path src \
              --debug-patterns \
              --debug-patterns-path ~/logs/patterns-debug.jsonl
```

### Pattern Debug Events

The pattern debug log captures detailed information about pattern processing:

#### Pattern Application Event
```json
{
  "ev": "pattern_application",
  "path": "/src/main.adb",
  "pattern": "comment-normalize",
  "regex": "\\s*--\\s+",
  "replacement": " -- ",
  "matches": 3,
  "timing_ms": 2.5
}
```

#### Pattern Skip Event
```json
{
  "ev": "pattern_skip",
  "path": "/src/large_file.adb",
  "reason": "file_too_large",
  "size_bytes": 11534336,
  "max_bytes": 10485760
}
```

#### Pattern Complete Event
```json
{
  "ev": "pattern_complete",
  "path": "/src/main.adb",
  "patterns_applied": 5,
  "total_replacements": 12,
  "total_time_ms": 15.3
}
```

### Use Cases

Pattern debug logging is useful for:
- Verifying pattern regex matches
- Checking replacement counts
- Performance tuning (identifying slow patterns)
- Debugging pattern conflicts
- Understanding why patterns aren't applying

## Debug ALS Logging

### Enabling ALS Debug Logs

```bash
# Default location: ./adafmt_<timestamp>_debug-als.jsonl
adafmt format --project-path project.gpr \
              --include-path src \
              --debug-als

# Custom location
adafmt format --project-path project.gpr \
              --include-path src \
              --debug-als \
              --debug-als-path ~/logs/als-debug.jsonl
```

### ALS Debug Events

The ALS debug log captures Language Server Protocol communication:

#### Format Request Event
```json
{
  "ev": "als_format_request",
  "path": "/src/main.adb",
  "method": "textDocument/formatting",
  "uri": "file:///src/main.adb",
  "tab_size": 3,
  "insert_spaces": true
}
```

#### Format Response Event
```json
{
  "ev": "als_format_response",
  "path": "/src/main.adb",
  "has_edits": true,
  "edit_count": 5,
  "response_time_ms": 125
}
```

#### File Complete Event
```json
{
  "ev": "als_file_complete",
  "path": "/src/main.adb",
  "changed": true,
  "original_size": 1024,
  "formatted_size": 1035
}
```

#### Timeout Event
```json
{
  "ev": "als_format_timeout",
  "path": "/src/slow_file.adb",
  "timeout_seconds": 60
}
```

### Use Cases

ALS debug logging is useful for:
- Diagnosing ALS communication issues
- Understanding formatting changes
- Performance analysis (response times)
- Debugging timeout problems
- Verifying ALS is receiving correct parameters

## Analyzing Debug Logs

### Using jq for Analysis

Debug logs are JSONL format, making them easy to analyze with `jq`:

```bash
# Count pattern applications by pattern name
jq -r 'select(.ev == "pattern_application") | .pattern' adafmt_*_debug-patterns.jsonl | sort | uniq -c

# Find slowest patterns
jq 'select(.ev == "pattern_application") | {pattern: .pattern, time: .timing_ms}' adafmt_*_debug-patterns.jsonl | sort -k4 -n

# Find ALS timeouts
jq 'select(.ev == "als_format_timeout")' adafmt_*_debug-als.jsonl

# Calculate average ALS response time
jq -s 'map(select(.ev == "als_format_response") | .response_time_ms) | add/length' adafmt_*_debug-als.jsonl
```

### Correlating with Main Logs

All log files from the same run share the same timestamp, making correlation easy:

```bash
# If timestamp is 20250115_143022
ls -la adafmt_20250115_143022_*.jsonl
# Shows: log.jsonl, patterns.log, debug-patterns.jsonl, debug-als.jsonl, stderr.log
```

## Common Debugging Scenarios

### Scenario 1: Pattern Not Applying

Enable pattern debug logging and check for:
1. Pattern skip events (file too large?)
2. Zero matches in pattern_application events
3. Pattern not in the loaded patterns list

```bash
# Check if pattern is loaded
jq 'select(.ev == "run_start") | .patterns_loaded' adafmt_*_patterns.log

# Check for skips
jq 'select(.ev == "pattern_skip")' adafmt_*_debug-patterns.jsonl
```

### Scenario 2: ALS Hanging

Enable ALS debug logging and check for:
1. Missing responses after requests
2. Long response times
3. Timeout events

```bash
# Find requests without responses
jq -r 'select(.ev == "als_format_request") | .path' adafmt_*_debug-als.jsonl > requests.txt
jq -r 'select(.ev == "als_format_response") | .path' adafmt_*_debug-als.jsonl > responses.txt
diff requests.txt responses.txt
```

### Scenario 3: Performance Issues

Enable both debug logs and analyze timing:

```bash
# Pattern processing time per file
jq 'select(.ev == "pattern_complete") | {path: .path, time: .total_time_ms}' adafmt_*_debug-patterns.jsonl

# ALS response time distribution
jq 'select(.ev == "als_format_response") | .response_time_ms' adafmt_*_debug-als.jsonl | sort -n
```

## Performance Considerations

### Debug Logging Overhead

Debug logging has minimal performance impact:
- Pattern debug: ~1-2% overhead (regex string serialization)
- ALS debug: <1% overhead (event logging only)
- Both enabled: ~2-3% total overhead

### Log File Sizes

Debug logs can be large for big projects:
- Pattern debug: ~500 bytes per file with patterns
- ALS debug: ~300 bytes per file
- Example: 1000 files ≈ 800KB total debug logs

### Best Practices

1. **Enable selectively**: Only enable the debug log you need
2. **Use custom paths**: Direct debug logs to fast storage
3. **Clean up**: Debug logs can accumulate quickly
4. **Compress**: Debug logs compress well (90%+ reduction)

Example cleanup script:
```bash
#!/bin/bash
# Compress debug logs older than 7 days
find . -name "adafmt_*_debug-*.jsonl" -mtime +7 -exec gzip {} \;

# Delete compressed logs older than 30 days
find . -name "adafmt_*_debug-*.jsonl.gz" -mtime +30 -delete
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Format Ada code with debug logging
  run: |
    adafmt format \
      --project-path project.gpr \
      --include-path src \
      --write \
      --debug-als \
      --debug-patterns
  continue-on-error: true

- name: Upload debug logs on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: adafmt-debug-logs
    path: |
      adafmt_*_debug-*.jsonl
      adafmt_*_stderr.log
```

### Jenkins Example

```groovy
stage('Format') {
    steps {
        sh '''
            adafmt format \
              --project-path project.gpr \
              --include-path src \
              --check \
              --debug-als \
              --debug-patterns
        '''
    }
    post {
        failure {
            archiveArtifacts artifacts: 'adafmt_*_debug-*.jsonl, adafmt_*_stderr.log'
        }
    }
}
```

## Conclusion

Debug logging provides deep insights into adafmt's pattern processing and ALS communication. Use these logs to:
- Diagnose issues quickly
- Optimize performance
- Understand formatting behavior
- Debug integration problems

Remember to clean up debug logs periodically as they can accumulate over time.