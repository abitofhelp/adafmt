# ALS Initialization and Readiness Guide

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This guide explains how adafmt initializes the Ada Language Server (ALS) and ensures it's ready for formatting operations, including the readiness probe mechanism and timeout configuration.

## Table of Contents

1. [Overview](#overview)
2. [The First-File Hanging Problem](#the-first-file-hanging-problem)
3. [The Readiness Probe Solution](#the-readiness-probe-solution)
4. [Configuring --als-ready-timeout](#configuring---als-ready-timeout)
5. [Troubleshooting](#troubleshooting)
6. [Performance Considerations](#performance-considerations)

## Overview

When adafmt starts, it must initialize the Ada Language Server (ALS) before formatting files. This initialization involves:

1. **Process Launch**: Starting the ada_language_server process
2. **LSP Handshake**: Sending `initialize` request and receiving capabilities
3. **Project Loading**: ALS loads the GPR project file and analyzes dependencies
4. **Internal Initialization**: ALS prepares its internal state for formatting requests

The challenge is that even after the LSP handshake completes, ALS may need additional time to fully initialize its internal state before it can process formatting requests efficiently.

## The First-File Hanging Problem

### Symptoms

Users may experience hanging when formatting the first file, characterized by:
- The formatter appears to freeze on the first file
- A timeout error occurs after 30 seconds: "Timeout writing to ALS stdin - process may be hung"
- Subsequent runs may also hang, even with preflight cleanup
- The issue is most pronounced with large Ada projects

### Root Cause

The hanging occurs because:
1. ALS performs additional initialization when it receives its first real formatting request
2. This initialization includes loading Ada libraries, parsing the full project, and building internal caches
3. During this time, ALS may not read from stdin quickly enough, causing the stdin buffer to fill
4. The `asyncio` drain operation blocks, waiting for ALS to read the buffered data

### Why Fixed Delays Don't Work

A simple sleep delay (the old `--warmup-seconds` approach) is insufficient because:
- Fast systems waste time waiting unnecessarily
- Slow systems may still timeout if the delay is too short
- The required initialization time varies greatly based on project size and system performance
- There's no way to know if ALS is actually ready without testing it

## The Readiness Probe Solution

### How It Works

Adafmt now uses an active readiness probe that:

1. **Sends a Dummy Request**: After LSP initialization, sends a minimal Ada package for formatting
2. **Waits for Response**: Uses an extended timeout (60 seconds) for this first request
3. **Retries on Failure**: If the request fails, retries with exponential backoff
4. **Confirms Readiness**: Once successful, ALS is confirmed ready for real formatting

### Implementation Details

```python
# Simplified readiness probe logic
dummy_ada_source = """package Dummy is
   procedure Test;
end Dummy;"""

max_retries = max(1, als_ready_timeout // 5)  # e.g., 10 seconds = 2 retries
retry_delay = 2.0  # Start with 2 second delay

for attempt in range(max_retries):
    try:
        # Send dummy formatting request
        await format_dummy_file()
        print("ALS is ready for formatting")
        break
    except Exception:
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 10.0)  # Exponential backoff
```

### Benefits

- **No Wasted Time**: Fast systems proceed as soon as ALS is ready
- **Adaptive**: Slow systems get multiple attempts with increasing delays
- **Reliable**: Actual readiness is verified, not assumed
- **Graceful Degradation**: If probe fails, formatting continues with warnings

## Configuring --als-ready-timeout

### Default Value

The default timeout is 10 seconds, which provides:
- 2 retry attempts (10 seconds / 5)
- Initial retry after 2 seconds, second after 3 seconds
- Suitable for most small to medium Ada projects

### Recommended Values

Choose your timeout based on project size and system performance:

#### Small Projects (< 50 files)
```bash
adafmt format --project-path project.gpr --als-ready-timeout 5
```
- 1 retry attempt
- Good for simple projects with few dependencies

#### Medium Projects (50-500 files)
```bash
adafmt format --project-path project.gpr --als-ready-timeout 10  # Default
```
- 2 retry attempts
- Balanced for most use cases

#### Large Projects (> 500 files)
```bash
adafmt format --project-path project.gpr --als-ready-timeout 30
```
- 6 retry attempts
- Allows more time for complex project analysis

#### Very Large Projects or Slow Systems
```bash
adafmt format --project-path project.gpr --als-ready-timeout 60
```
- 12 retry attempts
- Maximum flexibility for challenging environments

### How Retries Work

The timeout value determines the number of retries:
- **Retries** = timeout / 5 (minimum 1)
- **Delays**: 2s, 3s, 4.5s, 6.75s, 10s, 10s... (capped at 10s)

Examples:
- `--als-ready-timeout 5`: 1 retry after 2s
- `--als-ready-timeout 15`: 3 retries after 2s, 3s, 4.5s
- `--als-ready-timeout 30`: 6 retries, total wait up to ~35s

### Performance Impact

Setting a higher timeout has minimal performance impact:
- If ALS is ready quickly, no time is wasted
- Only affects startup time, not per-file formatting
- Most overhead occurs only on failed attempts

## Troubleshooting

### ALS Still Not Ready

If you see "Warning: Readiness check failed after N attempts", try:

1. **Increase Timeout**:
   ```bash
   adafmt format --project-path project.gpr --als-ready-timeout 60
   ```

2. **Check ALS Logs**:
   ```bash
   # Enable ALS debug logging
   adafmt format --project-path project.gpr --debug-als
   ```

3. **Verify Project Configuration**:
   - Ensure the GPR file is valid
   - Check that all project dependencies are available
   - Verify GNAT installation is complete

4. **System Resources**:
   - Check available memory (ALS can be memory-intensive)
   - Ensure no CPU throttling during initialization
   - Close other memory-intensive applications

### Persistent Hanging

If hanging persists even with increased timeouts:

1. **Aggressive Preflight**:
   ```bash
   adafmt format --project-path project.gpr --preflight aggressive
   ```

2. **Manual ALS Cleanup**:
   ```bash
   pkill -f ada_language_server
   rm -rf .als-alire .als-lock
   ```

3. **Check for Corrupted State**:
   - Delete `~/.als/` directory
   - Clear any project-specific caches
   - Reinstall ALS if necessary

### Debug Mode

For detailed diagnostics:
```bash
adafmt format --project-path project.gpr \
  --als-ready-timeout 30 \
  --debug-als \
  --stderr-path als-stderr.log
```

This provides:
- Detailed ALS communication logs
- Stderr output from ALS process
- Timing information for each phase

### Terminal State Issues

If adafmt continues to hang despite all troubleshooting steps:

**Close and restart your terminal session**. This resolves issues caused by:
- Corrupted terminal state or environment variables
- Orphaned background processes
- Stale file descriptors or process groups
- Shell-specific issues that persist across commands

This "clean slate" approach has proven effective when all other solutions fail.

## Performance Considerations

### Startup Overhead

The readiness probe adds minimal overhead:
- Successful probe: ~100-500ms on fast systems
- Failed attempts: 2s + retry delays
- Only occurs once per formatting session

### Optimization Tips

1. **Persistent ALS Mode** (future feature):
   - Keep ALS running between formatting sessions
   - Eliminate initialization overhead entirely

2. **Project Optimization**:
   - Minimize project dependencies
   - Use project subsetting for large codebases
   - Consider splitting very large projects

3. **System Optimization**:
   - Use SSDs for source code storage
   - Ensure adequate RAM (4GB+ recommended)
   - Disable CPU power saving during formatting

### Benchmarking

To measure ALS initialization time:
```bash
time adafmt format --project-path project.gpr \
  --include-path src \
  --no-patterns \
  --check \
  --als-ready-timeout 60
```

Look for the "ALS is ready for formatting" message timing.

## Best Practices

1. **Start Conservative**: Begin with default timeout and increase if needed
2. **Monitor Logs**: Use `--debug-als` to understand initialization patterns
3. **Document Project Needs**: Add recommended timeout to project README
4. **CI/CD Configuration**: Use appropriate timeouts for build environments

Example project documentation:
```markdown
## Formatting

This project uses adafmt for formatting. Due to the project size,
we recommend using an extended ALS timeout:

```bash
adafmt format --project-path project.gpr --als-ready-timeout 30
```
```

## Future Improvements

Planned enhancements to the readiness mechanism:
- Persistent ALS daemon mode to eliminate repeated initialization
- Smarter retry strategies based on project characteristics
- Parallel readiness probes for multi-project workspaces
- Caching of initialization state across runs

## Conclusion

The ALS readiness probe mechanism ensures reliable formatting by actively verifying that ALS is ready before processing files. By replacing fixed delays with dynamic probing, adafmt adapts to various system speeds and project sizes while minimizing wait times. Proper configuration of `--als-ready-timeout` based on your project's needs will ensure smooth, efficient formatting operations.