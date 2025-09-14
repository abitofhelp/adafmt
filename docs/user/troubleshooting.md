# Troubleshooting Guide
# adafmt - Ada Language Formatter

**Version:** 1.0.0  
**Last Updated:** January 2025

## Common Issues and Solutions

### 1. Ada Language Server Issues

> **Note:** For comprehensive timeout configuration and tuning, see [ALS Timeout Improvements](ALS_TIMEOUT_IMPROVEMENTS.md).

#### "Ada Language Server not found"

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
   - **Via package manager:** Check your system's package manager
   - **From source:** Build from [Ada Language Server repository](https://github.com/AdaCore/ada_language_server)

3. Add ALS to your PATH:
   ```bash
   export PATH="/path/to/als/bin:$PATH"
   ```

#### "Existing ALS processes detected"

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

2. Manually kill ALS processes:
   ```bash
   pkill -f ada_language_server
   ```

3. Check for stale lock files:
   ```bash
   find . -name ".als-*" -type d -mmin +10
   ```

### 2. Timeout Issues

> **Note:** For detailed timeout configuration, tuning strategies, and advanced scenarios, see [ALS Timeout Improvements](ALS_TIMEOUT_IMPROVEMENTS.md).

#### Overview

Timeout issues occur when the Ada Language Server (ALS) takes longer than expected to respond to formatting requests. This section covers the most common timeout scenarios and their quick solutions.

#### Common Timeout Scenarios

##### Scenario 1: ALS Initialization Timeout

**Symptoms:**
- Error: "ALS initialization timed out after X seconds"
- Long delay at startup with no formatting progress
- ALS appears to start but never becomes ready

**Quick Solutions:**
```bash
# Increase init timeout (default: 60 seconds)
adafmt --project-path /path/to/project.gpr --init-timeout 180

# Add warmup time for complex projects
adafmt --project-path /path/to/project.gpr --warmup-seconds 30

# Clean startup with preflight
adafmt --project-path /path/to/project.gpr --preflight kill+clean --init-timeout 120
```

**Diagnostic Commands:**
```bash
# Check if ALS is responsive
ada_language_server --version

# Monitor ALS startup
tail -f ~/.als/ada_ls_log.*.log

# Check for competing ALS processes
ps aux | grep ada_language_server
```

##### Scenario 2: File Formatting Timeout

**Symptoms:**
- Error: "Formatting timed out for file X after Y seconds"
- Some files format successfully, others timeout
- Timeout occurs during actual formatting, not initialization

**Quick Solutions:**
```bash
# Increase format timeout for large files (default: 60 seconds)
adafmt --project-path /path/to/project.gpr --format-timeout 180

# Process files in smaller batches
adafmt --project-path /path/to/project.gpr --batch-size 5 --format-timeout 120

# Skip problematic files temporarily
adafmt --project-path /path/to/project.gpr --exclude-path /path/to/slow/files
```

**Diagnostic Commands:**
```bash
# Test formatting a single file
adafmt --project-path /path/to/project.gpr --include-path /path/to/single/file.adb --format-timeout 300

# Check file size and complexity
wc -l /path/to/problematic/file.adb
grep -c "procedure\|function\|package" /path/to/problematic/file.adb
```

##### Scenario 3: Project Loading Timeout

**Symptoms:**
- Timeout occurs immediately after ALS starts
- Error mentions project file or dependencies
- Works for simple projects but fails for complex ones

**Quick Solutions:**
```bash
# Increase both init and warmup for complex projects
adafmt --project-path /path/to/complex.gpr --init-timeout 300 --warmup-seconds 45

# Simplify project temporarily
adafmt --project-path /path/to/simple.gpr --include-path /path/to/subset

# Check project file validity
gprbuild -p -P /path/to/project.gpr --dry-run
```

**Diagnostic Commands:**
```bash
# Validate project file
gprls -P /path/to/project.gpr

# Check project dependencies
gprls -P /path/to/project.gpr -d

# Monitor ALS project loading
ADAFMT_DEBUG=1 adafmt --project-path /path/to/project.gpr --ui plain
```

##### Scenario 4: System Resource Constraints

**Symptoms:**
- Timeouts occur inconsistently
- System appears slow or unresponsive during formatting
- Multiple ALS processes consuming resources

**Quick Solutions:**
```bash
# Reduce concurrent operations
adafmt --project-path /path/to/project.gpr --batch-size 3

# Clean up stale processes
adafmt --project-path /path/to/project.gpr --preflight aggressive

# Increase all timeouts for resource-constrained systems
adafmt --project-path /path/to/project.gpr \
       --init-timeout 180 \
       --format-timeout 120 \
       --warmup-seconds 30
```

**Diagnostic Commands:**
```bash
# Check system resources
top -p $(pgrep ada_language_server)
free -h
df -h

# Count ALS processes
pgrep -c ada_language_server

# Check for zombie processes
ps aux | grep ada_language_server | grep -v grep
```

#### Quick Timeout Resolution Workflow

1. **First, try the standard fix:**
   ```bash
   adafmt --project-path /path/to/project.gpr \
          --preflight kill+clean \
          --init-timeout 120 \
          --format-timeout 90
   ```

2. **If still failing, escalate timeouts:**
   ```bash
   adafmt --project-path /path/to/project.gpr \
          --preflight aggressive \
          --init-timeout 300 \
          --format-timeout 180 \
          --warmup-seconds 45
   ```

3. **For debugging, enable logging:**
   ```bash
   adafmt --project-path /path/to/project.gpr \
          --log-path timeout-debug.jsonl \
          --stderr-path als-timeout.log \
          --ui plain \
          --init-timeout 300 \
          --format-timeout 180
   ```

4. **Check the logs:**
   ```bash
   # Look for timeout-related entries
   grep -i timeout timeout-debug.jsonl
   
   # Check ALS stderr for issues
   tail -20 als-timeout.log
   ```

#### Environment-Specific Solutions

##### CI/CD Environments
```bash
# Conservative timeouts for CI
adafmt --project-path /path/to/project.gpr \
       --ui plain \
       --preflight aggressive \
       --init-timeout 300 \
       --format-timeout 150 \
       --warmup-seconds 60
```

##### Large Projects (>1000 files)
```bash
# Optimized for large codebases
adafmt --project-path /path/to/project.gpr \
       --batch-size 10 \
       --init-timeout 180 \
       --format-timeout 120 \
       --warmup-seconds 45
```

##### Development Machines
```bash
# Fast iteration for development
adafmt --project-path /path/to/project.gpr \
       --preflight safe \
       --init-timeout 90 \
       --format-timeout 60 \
       --warmup-seconds 15
```

#### When to Escalate

Contact support or file an issue if:
- Standard timeout increases (300s init, 180s format) don't resolve the issue
- Timeouts occur on simple, small files
- ALS logs show repeated crashes or errors
- System resources appear adequate but timeouts persist

Include in your report:
- Timeout configuration used
- Project size and complexity
- System specifications
- Relevant log excerpts from both adafmt and ALS

### 3. Formatting Errors

#### Syntax Errors vs Semantic Errors

**Understanding the difference:**
- **Syntax errors**: Malformed code structure that prevents parsing
  - Missing semicolons, unmatched parentheses, invalid keywords
  - These PREVENT formatting - ALS cannot parse the code
  - Error code: -32803
  
- **Semantic errors**: Valid syntax but incorrect meaning
  - Undefined types, missing imports, type mismatches
  - These DO NOT prevent formatting - structure is valid
  - Your code will format successfully but won't compile

**Example - Syntax Error (prevents formatting):**
```ada
procedure Test is
begin
   Put_Line("Hello")  -- Missing semicolon
end Test;
```

**Example - Semantic Error (allows formatting):**
```ada
procedure Test is
   X : Undefined_Type;  -- Type not declared, but syntax is valid
begin
   X.Do_Something;      -- Method doesn't exist, but syntax is valid
end Test;
```

#### "Syntactically invalid code" Error

**Symptoms:**
- Error code -32803 from ALS
- File fails to format
- Message: "(details in the stderr log)"

**Solutions:**
1. Check the stderr log for details:
   ```bash
   # Log location shown in output, e.g.:
   cat ./adafmt_20250115_100000_stderr.log
   ```

2. Look for the specific syntax error:
   ```
   [2025-01-15 10:00:00] SYNTAX_ERROR_CONFIRMED: File failed to format
   File: /path/to/file.adb
   Error: Syntactically invalid code
   Details: Missing semicolon at line 42
   Action: Fix syntax errors in the file and retry
   ```

3. Fix the syntax error and retry formatting

#### GNATFORMAT False Positives

**Symptoms:**
- ALS reports syntax error but file compiles successfully
- Warning shown in yellow: "GNATFORMAT syntax error but compiles OK"

**Understanding:**
- Sometimes GNATFORMAT is overly strict
- adafmt automatically verifies with the compiler
- False positives are tracked but don't prevent other files from formatting

**What to do:**
- These are informational warnings
- Your file compiles fine
- Consider reporting to Ada Language Server project if frequent

### 4. Performance Issues

#### Timeout Errors

**Symptoms:**
- "TimeoutError: ALS did not respond in time"
- Files fail to format after delay

**Solutions:**
1. Increase timeout values:
   ```bash
   adafmt --project-path project.gpr \
          --init-timeout 300 \
          --format-timeout 120 \
          --warmup-seconds 20
   ```

2. Check ALS logs for issues:
   ```bash
   # Default location or path shown in output
   cat ~/.als/ada_ls_log.*.log
   ```

3. For large projects, use preflight cleanup:
   ```bash
   adafmt --project-path project.gpr --preflight kill+clean
   ```

#### Slow Startup

**Symptoms:**
- Long delay before formatting begins
- ALS takes time to initialize

**Solutions:**
1. Adjust warmup time:
   ```bash
   # Reduce if ALS starts quickly
   adafmt --project-path project.gpr --warmup-seconds 5
   
   # Increase for complex projects
   adafmt --project-path project.gpr --warmup-seconds 30
   ```

2. Use aggressive preflight to ensure clean state:
   ```bash
   adafmt --project-path project.gpr --preflight aggressive
   ```

### 5. UI and Display Issues

#### Curses UI Not Working

**Symptoms:**
- No pretty UI despite terminal support
- Falls back to plain text mode

**Solutions:**
1. Check terminal capabilities:
   ```bash
   echo $TERM
   tput colors
   ```

2. Force a specific UI mode:
   ```bash
   # Force pretty mode
   adafmt --project-path project.gpr --ui pretty
   
   # Force plain mode for scripts
   adafmt --project-path project.gpr --ui plain
   ```

3. Debug UI selection:
   ```bash
   export ADAFMT_UI_DEBUG=1
   adafmt --project-path project.gpr
   ```

#### UI Elements "Dancing" or Misaligned

**Issue:** Fixed in version 1.0.0
- Vertical bars now stay aligned
- Percentages use fixed-width formatting

**If still experiencing issues:**
1. Update to latest version:
   ```bash
   pip install --upgrade adafmt
   ```

2. Report issue with screenshot to project repository

### 6. File and Path Issues

#### "Path must be absolute" Error

**Symptoms:**
- Error about relative paths
- Command fails to start

**Solutions:**
1. Use absolute paths:
   ```bash
   # Wrong
   adafmt --project-path project.gpr
   
   # Correct
   adafmt --project-path /home/user/project/project.gpr
   ```

2. Use shell expansion:
   ```bash
   adafmt --project-path $(pwd)/project.gpr
   ```

#### No Files Found

**Symptoms:**
- "No Ada files found in the specified paths"
- Nothing to format

**Solutions:**
1. Check include paths:
   ```bash
   adafmt --project-path /path/to/project.gpr \
          --include-path /path/to/src \
          --include-path /path/to/tests
   ```

2. Verify file extensions (.ads, .adb, .ada)

3. Check exclude paths aren't too broad:
   ```bash
   # This might exclude too much
   --exclude-path /path/to/project
   
   # Better: exclude specific directories
   --exclude-path /path/to/project/build \
   --exclude-path /path/to/project/.git
   ```

### 7. Integration Issues

#### CI/CD Failures

**Symptoms:**
- Works locally but fails in CI
- No output or wrong exit codes

**Solutions:**
1. Use appropriate UI mode:
   ```bash
   adafmt --project-path project.gpr --ui plain --check
   ```

2. Ensure ALS is available in CI environment

3. Use explicit paths:
   ```bash
   adafmt --project-path $CI_PROJECT_DIR/project.gpr \
          --include-path $CI_PROJECT_DIR/src
   ```

4. Check logs are accessible:
   ```bash
   adafmt --project-path project.gpr \
          --log-path $CI_PROJECT_DIR/adafmt.log \
          --stderr-path $CI_PROJECT_DIR/als-stderr.log
   ```

### 8. Debugging Steps

#### Enable Comprehensive Logging

```bash
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       --log-path debug.jsonl \
       --stderr-path als-errors.log \
       --ui plain
```

#### View Structured Logs

```bash
# Pretty print JSON logs
jq . debug.jsonl

# Filter for errors only
jq 'select(.status == "failed")' debug.jsonl

# View ALS stderr
cat als-errors.log
```

#### Check Environment

```bash
# ALS availability
which ada_language_server
ada_language_server --version

# Python version
python --version

# Terminal capabilities
echo $TERM
tput colors
```

### 9. Getting Help

If you're still experiencing issues:

1. **Check the logs:**
   - JSONL log: `./adafmt_TIMESTAMP_log.jsonl`
   - Stderr log: `./adafmt_TIMESTAMP_stderr.log`
   - ALS log: `~/.als/ada_ls_log.*.log`

2. **Report an issue:**
   - Include version: `adafmt --version`
   - Include relevant log excerpts
   - Describe expected vs actual behavior
   - Provide minimal reproduction steps

3. **Community resources:**
   - Project repository: [github.com/abitofhelp/adafmt](https://github.com/abitofhelp/adafmt)
   - Ada Language Server: [github.com/AdaCore/ada_language_server](https://github.com/AdaCore/ada_language_server)

## Appendix: Error Types Reference

| Error Type | Description | User Action |
|------------|-------------|-------------|
| SYNTAX_ERROR_CONFIRMED | Ada syntax errors preventing formatting | Fix syntax errors in the file |
| ALS_PROTOCOL_ERROR | Communication failures with ALS | Check ALS installation, try --preflight kill |
| CONNECTION_ERROR | Network/pipe errors | Retry the operation or restart ALS |
| UNEXPECTED_ERROR | Other errors | Check the log file for details |
| TIMEOUT | Operation exceeded time limit | Increase timeout values |

## Appendix: Preflight Modes

| Mode | Behavior | Use When |
|------|----------|----------|
| off | Skip all checks | You manage ALS manually |
| warn | Report only | Investigating issues |
| safe | Kill old ALS | Default, normal use |
| kill | Same as safe | Backward compatibility |
| kill+clean | Kill + remove locks | ALS hanging issues |
| aggressive | Kill all + clean | Major ALS problems |
| fail | Abort if issues | CI/CD strict mode |