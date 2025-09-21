# adafmt Development Tools

This directory contains development and debugging tools for working with adafmt and the Ada Language Server.

## Tools Overview

### als_rpc_probe.py

**Purpose**: High-level ALS testing tool using the adafmt ALSClient

**Description**: This probe tests Ada Language Server communication through the same client interface that adafmt uses. It performs a complete LSP workflow: initialization → file open → hover → formatting → shutdown.

**Usage**:
```bash
# Basic usage - just test ALS initialization
python tools/als_rpc_probe.py --project-path /path/to/project.gpr

# Test with a specific Ada file
python tools/als_rpc_probe.py --project-path /path/to/project.gpr \
    --file /path/to/file.ads

# With Alire project
python tools/als_rpc_probe.py --project-path /path/to/project.gpr \
    --alr-mode yes --crate-dir /path/to/crate

# Verbose output with custom timeouts
python tools/als_rpc_probe.py --project-path /path/to/project.gpr \
    --file test.adb --verbose \
    --als-ready-timeout 30 --format-timeout 90
```

**Options**:
- `--project-path` (required): Path to GNAT project file
- `--file`: Ada file to test (optional)
- `--alr-mode`: Alire mode (auto/yes/no)
- `--crate-dir`: Override Alire crate directory
- `--init-timeout`: ALS initialization timeout (default: 180s)
- `--als-ready-timeout`: Post-init warmup period (default: 10s)
- `--hover-timeout`: Hover request timeout (default: 15s)
- `--format-timeout`: Format request timeout (default: 60s)
- `--verbose`: Enable detailed output

**When to use**: 
- Testing ALS connectivity issues
- Debugging project configuration problems
- Verifying ALS is working before running adafmt
- Investigating timeout issues

### als_rpc_probe_stdio.py

**Purpose**: Low-level ALS testing tool with direct LSP protocol implementation

**Description**: This probe implements the Language Server Protocol directly without using the ALSClient abstraction. It handles raw JSON-RPC message framing and can help debug protocol-level issues.

**Usage**:
```bash
# Basic test
python tools/als_rpc_probe_stdio.py --project-path /path/to/project.gpr

# Test with specific file
python tools/als_rpc_probe_stdio.py --project-path /path/to/project.gpr \
    --file /path/to/test.ads

# With Alire
python tools/als_rpc_probe_stdio.py --project-path /path/to/project.gpr \
    --alr-mode yes
```

**When to use**:
- Debugging ALSClient implementation issues
- Testing raw LSP protocol behavior
- Investigating message framing problems
- When you need to see exact JSON-RPC messages

### harness_mocked.py

**Purpose**: Mock testing harness that simulates formatting without ALS

**Description**: This tool discovers Ada files and simulates a simple formatting operation (adds trailing newlines) without requiring ALS. Useful for testing the file discovery and diff display components of adafmt.

**Usage**:
```bash
# Run in current directory
python tools/harness_mocked.py

# Run from project root
cd /path/to/ada/project && python /path/to/adafmt/tools/harness_mocked.py
```

**Behavior**:
- Discovers Ada files recursively from current directory
- Simulates adding trailing newline if missing
- Shows unified diff output for "changed" files
- Limits output to first 10 files

**When to use**:
- Quick smoke tests without ALS
- Testing file discovery logic
- CI/CD pipeline validation
- Verifying diff output formatting

## Common Debugging Scenarios

### 1. ALS Won't Start

Use `als_rpc_probe.py` with verbose mode:
```bash
python tools/als_rpc_probe.py --project-path project.gpr --verbose
```

### 2. Formatting Timeouts

Test with increased timeouts:
```bash
python tools/als_rpc_probe.py --project-path project.gpr \
    --file problem.ads --format-timeout 120 --verbose
```

### 3. Protocol-Level Issues

Use the stdio probe to see raw messages:
```bash
python tools/als_rpc_probe_stdio.py --project-path project.gpr --file test.ads
```

### 4. File Discovery Testing

Use the mock harness to verify file discovery:
```bash
cd my_project && python path/to/tools/harness_mocked.py
```

## Development Notes

- All tools are standalone Python scripts
- They use the same dependencies as adafmt (no additional requirements)
- Tools should be run from a virtual environment with adafmt installed
- The probes require a working ALS installation
- The mock harness works without ALS

## Contributing

When adding new tools:
1. Follow the existing naming pattern (descriptive_name.py)
2. Include a docstring explaining the tool's purpose
3. Add clear command-line help
4. Update this README with usage information
5. Consider if the tool should be a test instead