# Troubleshooting and Debugging Guide

**Version:** 0.0.0  
**Last Updated:** September 2025

This comprehensive guide covers solutions to common adafmt issues, debugging techniques, and development tools.

---

## Table of Contents

### Common Issues
1. [Ada Language Server Issues](#1-ada-language-server-issues)
2. [Timeout Issues](#2-timeout-issues)
3. [Project File Issues](#3-project-file-issues)
4. [File Formatting Issues](#4-file-formatting-issues)
5. [Performance Issues](#5-performance-issues)

### Debugging Tools
6. [Development Debugging Tools](#6-development-debugging-tools)
7. [ALS Communication Debugging](#7-als-communication-debugging)
8. [Protocol-Level Debugging](#8-protocol-level-debugging)
9. [Logging and Analysis](#9-logging-and-analysis)

### Advanced Troubleshooting
10. [Environment-Specific Issues](#10-environment-specific-issues)
11. [CI/CD Issues](#11-cicd-issues)
12. [Performance Debugging](#12-performance-debugging)

---

## 1. Ada Language Server Issues

> **Note:** For comprehensive timeout configuration and tuning, see [Timeout Configuration Guide](timeout-guide.md).

### "Ada Language Server not found"

**Symptoms:**
- Error message: `ada_language_server: command not found`
- adafmt fails to start

**Solutions:**
1. Verify ALS is installed:
   ```bash
   which ada_language_server
   ```

2. If not found, install ALS:
   - **Via GNAT:** Install GNAT Community or Pro with ALS component
   - **Via Alire:** `alr install ada_language_server`
   - **Via package manager:** Check your system's package manager
   - **From source:** Build from [Ada Language Server repository](https://github.com/AdaCore/ada_language_server)

3. Add ALS to your PATH:
   ```bash
   export PATH="/path/to/als/bin:$PATH"
   ```

### "Existing ALS processes detected"

**Symptoms:**
- Warning about existing ALS processes
- Formatting may fail or hang

**Solutions:**
1. Use preflight mode to clean up:
   ```bash
   # Kill stale ALS processes (older than 30 minutes)
   adafmt --project-path project.gpr --preflight kill
   
   # Kill all ALS processes for current user
   adafmt --project-path project.gpr --preflight aggressive
   ```

2. Manual cleanup:
   ```bash
   # Find ALS processes
   ps aux | grep ada_language_server
   
   # Kill specific process
   kill <PID>
   
   # Kill all ALS processes
   pkill ada_language_server
   ```

### "ALS initialization timeout"

**Symptoms:**
- adafmt hangs during startup
- Timeout error during ALS initialization

**Solutions:**
1. Increase initialization timeout:
   ```bash
   adafmt --project-path project.gpr --init-timeout 300
   ```

2. Check project file validity:
   ```bash
   gprbuild -P project.gpr -c
   ```

3. Use debugging tools:
   ```bash
   python tools/als_rpc_probe.py --project-path project.gpr --verbose
   ```

## 2. Timeout Issues

> **Note:** For detailed timeout configuration, tuning strategies, and advanced scenarios, see [Timeout Configuration Guide](timeout-guide.md).

### Overview

Timeouts protect against hanging operations and can be tuned for different environments:
- **Init timeout**: ALS startup (default: 180s)
- **Format timeout**: Per-file formatting (default: 60s)
- **Max consecutive timeouts**: Safety limit (default: 5)

### Quick Timeout Resolution Workflow

```bash
# 1. Check if issue is specific to certain files
adafmt --project-path project.gpr --log-path debug.jsonl

# 2. Analyze timeout patterns
cat debug.jsonl | jq 'select(.status == "timeout")'

# 3. Try increased timeouts
adafmt --project-path project.gpr --format-timeout 120

# 4. If still failing, investigate specific files
python tools/als_rpc_probe.py --project-path project.gpr --file problem_file.adb
```

### Common Timeout Scenarios

#### Large Files
```bash
# Increase per-file timeout
adafmt --project-path project.gpr --format-timeout 180
```

#### Complex Projects
```bash
# Increase initialization timeout
adafmt --project-path project.gpr --init-timeout 300 --format-timeout 120
```

#### CI/CD Environments
```bash
# Aggressive timeouts for fast feedback
adafmt --project-path project.gpr --init-timeout 60 --format-timeout 30 --max-consecutive-timeouts 2
```

## 3. Project File Issues

### "Invalid project file"

**Symptoms:**
- Error about project file not found
- ALS fails to load project

**Solutions:**
1. Verify project file exists and is valid:
   ```bash
   ls -la project.gpr
   gprbuild -P project.gpr -c
   ```

2. Check project file syntax:
   ```ada
   project My_Project is
      for Source_Dirs use ("src");
      for Object_Dir use "obj";
   end My_Project;
   ```

3. Use absolute paths:
   ```bash
   adafmt --project-path /full/path/to/project.gpr
   ```

### "Source directories not found"

**Solutions:**
1. Verify source directories exist:
   ```bash
   cat project.gpr | grep -i source_dirs
   ls -la src/
   ```

2. Check include/exclude paths:
   ```bash
   adafmt --project-path project.gpr --include-path src/ --exclude-path build/
   ```

## 4. File Formatting Issues

### Syntax Errors vs Semantic Errors

**Syntax Errors** (prevent formatting):
- Malformed Ada code
- Missing semicolons, unmatched parentheses
- ALS returns error code -32803

**Semantic Errors** (allow formatting):
- Undefined types or variables
- Missing imports
- Code compiles syntactically but has meaning errors

### "File failed to format"

**Debugging steps:**
1. Check the specific error:
   ```bash
   adafmt --project-path project.gpr --log-path debug.jsonl
   cat debug.jsonl | jq 'select(.status == "failed")'
   ```

2. Test file in isolation:
   ```bash
   python tools/als_rpc_probe.py --project-path project.gpr --file problem_file.adb
   ```

3. Check Ada syntax:
   ```bash
   gnatmake -c problem_file.adb
   ```

## 5. Performance Issues

### Slow Formatting

**Investigation:**
1. Enable timing analysis:
   ```bash
   adafmt --project-path project.gpr --log-path perf.jsonl
   cat perf.jsonl | jq '.duration_ms' | sort -nr | head -10
   ```

2. Check file sizes:
   ```bash
   find src/ -name "*.ad*" -exec wc -l {} + | sort -nr | head -10
   ```

3. Profile ALS performance:
   ```bash
   adafmt --project-path project.gpr --stderr-path als_debug.log
   ```

## 6. Development Debugging Tools

### ALS Debugging Tools

The `tools/` directory contains specialized debugging utilities:

#### ALS RPC Probe (`als_rpc_probe.py`)

High-level ALS testing tool using the adafmt ALSClient:

```bash
# High-level ALS testing
python tools/als_rpc_probe.py --project-path project.gpr --verbose

# Test specific file with custom timeouts
python tools/als_rpc_probe.py --project-path project.gpr \
    --file test.adb --format-timeout 120 --verbose

# With Alire project
python tools/als_rpc_probe.py --project-path project.gpr \
    --alr-mode yes --crate-dir /path/to/crate
```

**When to use**:
- Testing ALS connectivity issues
- Debugging project configuration problems
- Verifying ALS is working before running adafmt
- Investigating timeout issues

#### Low-Level Protocol Probe (`als_rpc_probe_stdio.py`)

Direct LSP protocol implementation for protocol-level debugging:

```bash
# Low-level protocol testing
python tools/als_rpc_probe_stdio.py --project-path project.gpr

# Test with specific file
python tools/als_rpc_probe_stdio.py --project-path project.gpr \
    --file /path/to/test.ads
```

**When to use**:
- Protocol-level debugging
- Understanding LSP message flow
- Investigating communication issues
- Testing custom LSP implementations

### Mock Testing Harness (`harness_mocked.py`)

Test adafmt without requiring a real ALS installation:

```bash
# Test with mocked ALS responses
python tools/harness_mocked.py --test-scenario basic
```

**When to use**:
- Testing in environments without ALS
- Isolating adafmt logic from ALS behavior
- Regression testing
- CI environments with limited dependencies

## 7. ALS Communication Debugging

### LSP Message Debugging

Enable detailed LSP communication logging:

```bash
# Capture all ALS communication
adafmt --project-path project.gpr \
    --stderr-path als_communication.log \
    --log-path debug.jsonl
```

### Common LSP Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| -32803 | Syntax Error | Fix Ada syntax in source file |
| -32700 | Parse Error | Check JSON-RPC message format |
| -32600 | Invalid Request | Verify LSP request structure |
| -32601 | Method Not Found | Check ALS version compatibility |

### Protocol Analysis

```bash
# Analyze LSP request/response patterns
python tools/als_rpc_probe_stdio.py --project-path project.gpr \
    --verbose --log-requests
```

## 8. Protocol-Level Debugging

### Request Correlation

Track LSP request/response correlation:

```bash
# Monitor request IDs
cat als_communication.log | grep -E "(id.*request|id.*response)"
```

### Message Timing

Analyze LSP message timing:

```bash
# Extract timing information
cat debug.jsonl | jq 'select(.type == "als_request") | {method: .method, duration: .duration_ms}'
```

### Connection Issues

Debug LSP connection problems:

```bash
# Test basic connectivity
python tools/als_rpc_probe_stdio.py --project-path project.gpr --test-connection
```

## 9. Logging and Analysis

### Structured Logging

adafmt produces structured JSONL logs for analysis:

```bash
# Basic log analysis
cat adafmt_*.jsonl | jq .

# Filter by status
cat adafmt_*.jsonl | jq 'select(.status == "failed")'

# Analyze timing
cat adafmt_*.jsonl | jq '.duration_ms' | sort -nr | head -10
```

### Log File Types

- **Main log** (`adafmt_*_log.jsonl`): File processing status and timing
- **Stderr log** (`adafmt_*_stderr.log`): ALS error output
- **Pattern log** (`adafmt_*_patterns.log`): Pattern processing activity

### Log Analysis Scripts

```bash
# Failed files summary
cat adafmt_*_log.jsonl | jq -r 'select(.status == "failed") | .path' | sort

# Average processing time
cat adafmt_*_log.jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'

# Timeout analysis
cat adafmt_*_log.jsonl | jq 'select(.status == "timeout") | {path: .path, duration: .duration_ms}'
```

## 10. Environment-Specific Issues

### macOS Issues

**Permission problems:**
```bash
# Check Gatekeeper
spctl --assess --type execute /path/to/ada_language_server

# Reset permissions
xattr -d com.apple.quarantine /path/to/ada_language_server
```

### Windows Issues

**Path separator problems:**
```bash
# Use forward slashes or escaped backslashes
adafmt --project-path "C:/path/to/project.gpr"
```

### Linux Issues

**Library dependencies:**
```bash
# Check missing libraries
ldd /path/to/ada_language_server

# Install missing dependencies
sudo apt-get install libgmp10 libgnatutil9-dev
```

### Docker/Container Issues

```bash
# Ensure sufficient memory
docker run --memory=2g adafmt_image

# Mount project correctly
docker run -v $(pwd):/workspace adafmt_image
```

## 11. CI/CD Issues

### GitHub Actions

**Common issues:**
- Timeout in CI environment
- Missing ALS installation
- Permission problems

**Solutions:**
```yaml
# Install ALS in CI
- name: Install ALS
  run: |
    curl -L https://github.com/AdaCore/ada_language_server/releases/latest/download/als-linux.tar.gz | tar xz
    echo "$(pwd)/als/bin" >> $GITHUB_PATH

# Use appropriate timeouts
- name: Format code
  run: |
    adafmt --project-path project.gpr \
           --init-timeout 60 \
           --format-timeout 30 \
           --ui plain
```

### GitLab CI

```yaml
adafmt_check:
  script:
    - adafmt --project-path project.gpr --check --ui plain
  timeout: 10m
```

## 12. Performance Debugging

### Profiling File Processing

```bash
# Identify slow files
adafmt --project-path project.gpr --log-path timing.jsonl
cat timing.jsonl | jq 'select(.duration_ms > 5000) | {path: .path, duration: .duration_ms}' | sort_by(.duration)
```

### Memory Usage

```bash
# Monitor memory usage
time -v adafmt --project-path project.gpr

# Check for memory leaks
valgrind --tool=massif python -m adafmt --project-path project.gpr
```

### ALS Performance

```bash
# Profile ALS performance with traces
adafmt --project-path project.gpr --stderr-path als_trace.log
# See traces-config.md for detailed ALS profiling
```

### Large Project Optimization

```bash
# Optimize for large projects
adafmt --project-path large_project.gpr \
       --init-timeout 300 \
       --format-timeout 120 \
       --max-consecutive-timeouts 10 \
       --ui plain
```

## Getting Help

If these troubleshooting steps don't resolve your issue:

1. **Collect diagnostic information:**
   ```bash
   adafmt --project-path project.gpr \
          --log-path diagnostic.jsonl \
          --stderr-path diagnostic_stderr.log
   ```

2. **Test with debugging tools:**
   ```bash
   python tools/als_rpc_probe.py --project-path project.gpr --verbose
   ```

3. **Create a GitHub issue** with:
   - Your adafmt version (`adafmt --version`)
   - Your operating system
   - ALS version information
   - Complete error messages
   - Diagnostic logs
   - Steps to reproduce the issue

4. **For urgent issues:**
   - Try aggressive preflight cleanup: `--preflight aggressive`
   - Use conservative timeouts: `--format-timeout 180`
   - Test with minimal project

## See Also

- [Timeout Configuration Guide](timeout-guide.md) - Detailed timeout tuning
- [Configuration Guide](configuration-guide.md) - Complete configuration reference
- [Getting Started Guide](getting-started-guide.md) - Basic usage
- [API Reference](../api/index.md) - Technical implementation details