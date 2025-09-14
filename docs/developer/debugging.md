# Debugging and Development Tools

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This guide covers debugging techniques, development tools, and troubleshooting common issues when developing adafmt.

## Development Tools

### ALS Debugging Tools

The `tools/` directory contains specialized debugging utilities for working with the Ada Language Server:

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
- Debugging ALSClient implementation issues
- Testing raw LSP protocol behavior
- Investigating message framing problems
- When you need to see exact JSON-RPC messages

#### Mock Testing Harness (`harness_mocked.py`)

Test without ALS dependency:

```bash
# Test without ALS
python tools/harness_mocked.py
```

**When to use**:
- Quick smoke tests without ALS
- Testing file discovery logic
- CI/CD pipeline validation
- Verifying diff output formatting

For complete tool documentation, see [tools/README.md](../../tools/README.md).

### Development Commands

```bash
# Development
make dev          # Install with dev dependencies
make test         # Run unit tests
make test-all     # Run all tests
make coverage     # Test coverage
make lint         # Code linting
make format       # Code formatting
make typecheck    # Type checking
make clean        # Clean build artifacts

# Ada formatting
make ada-format   # Format Ada files (dry-run)
make ada-write    # Format and write Ada files
make ada-check    # Check if files need formatting

# Distribution
make build        # Build packages
make dist-all     # Create all distributions
```

## Debugging and Troubleshooting

### Common Issues and Solutions

#### ALS Won't Start

1. **Check ALS installation**: `which ada_language_server`
2. **Verify project file**: `gprbuild -P project.gpr -c`
3. **Use verbose debugging**: `--verbose` flag
4. **Test with probe tool**:
   ```bash
   python tools/als_rpc_probe.py --project-path project.gpr --verbose
   ```

#### Tests Failing

1. **Run specific test**: `pytest tests/unit/test_als_client.py::TestClass::test_method -v`
2. **Use debugger**: `pytest --pdb`
3. **Check fixtures**: Verify test data setup
4. **Show local variables**: `pytest -l`

#### Performance Issues

1. **Profile with**: `python -m cProfile -s cumulative`
2. **Use async profiling** for ALS communication
3. **Check file discovery patterns**
4. **Test with increased timeouts**:
   ```bash
   python tools/als_rpc_probe.py --project-path project.gpr \
       --init-timeout 300 --warmup-seconds 20 --format-timeout 120
   ```

#### Timeout Errors

- **Increase timeouts**: `--init-timeout 300 --warmup-seconds 20 --format-timeout 120`
- **Check ALS stderr**: `--stderr-file-path als-debug.log`
- **Test with probe tools** to isolate the issue

#### Protocol-Level Issues

Use the stdio probe to see raw messages:
```bash
python tools/als_rpc_probe_stdio.py --project-path project.gpr --file test.ads
```

### Debugging Scenarios

#### 1. ALS Communication Problems

```bash
# Test ALS connectivity
python tools/als_rpc_probe.py --project-path project.gpr --verbose

# Check raw protocol messages
python tools/als_rpc_probe_stdio.py --project-path project.gpr --file test.ads

# Capture ALS stderr output
adafmt --project-path project.gpr \
       --include-path src \
       --stderr-file-path als-debug.log \
       --log-file-path adafmt-debug.jsonl
```

#### 2. File Discovery Issues

```bash
# Test file discovery without ALS
python tools/harness_mocked.py

# Debug file patterns
adafmt --project-path project.gpr \
       --include-path src \
       --log-file-path debug.jsonl \
       --ui plain
```

#### 3. Test Debugging

```bash
# Run with maximum verbosity
pytest -vvs

# Drop into debugger on failure
pytest --pdb

# Run specific failing test
pytest tests/unit/test_als_client.py::test_specific_case -vvs --pdb
```

### Logging and Debug Output

#### Structured Logging

Enable comprehensive logging to diagnose issues:

```bash
adafmt --project-path /path/to/project.gpr \
       --include-path /path/to/src \
       --log-file-path adafmt-debug.jsonl \
       --stderr-file-path als-stderr.log \
       --ui plain
```

View logs:
```bash
# View structured logs
jq . adafmt-debug.jsonl

# View ALS errors
cat als-stderr.log

# Filter specific events
jq 'select(.event_type == "format_file")' adafmt-debug.jsonl
```

#### Environment Variables

```bash
# ALS configuration
export ALS_HOME=/path/to/als
export GPR_PROJECT_PATH=/path/to/projects

# Development
export PYTHONPATH=/path/to/adafmt/src
export DEBUG=1

# UI debugging
export ADAFMT_UI_FORCE=plain
export ADAFMT_UI_DEBUG=1
```

## IDE Configuration

### VS Code

Configure Python development environment:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

Debug configuration:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Current Test",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${file}::${selectedText}",
                "-vvs"
            ],
            "console": "integratedTerminal"
        },
        {
            "name": "Debug adafmt",
            "type": "python",
            "request": "launch",
            "module": "adafmt",
            "args": [
                "--project-path", "project.gpr",
                "--include-path", "src",
                "--verbose"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

### PyCharm

- Set interpreter to `.venv/bin/python`
- Enable pytest as test runner
- Configure Black as formatter
- Set up run configurations for common tasks

## Advanced Debugging Techniques

### Memory Profiling

```bash
# Profile memory usage
python -m memory_profiler adafmt_script.py

# Generate memory reports
mprof run python -m adafmt --project-path project.gpr --include-path src
mprof plot
```

### Async Debugging

```python
import asyncio
import logging

# Enable asyncio debug mode
logging.basicConfig(level=logging.DEBUG)
asyncio.get_event_loop().set_debug(True)
```

### Network Debugging

```bash
# Monitor ALS subprocess communication
strace -e trace=read,write -p $(pgrep ada_language_server)

# Monitor file system access
strace -e trace=file adafmt --project-path project.gpr --include-path src
```

## Troubleshooting Checklist

When encountering issues:

1. ✅ **ALS Installation**: Verify `ada_language_server` is in PATH
2. ✅ **Project File**: Test with `gprbuild -P project.gpr -c`
3. ✅ **Permissions**: Check file/directory permissions
4. ✅ **Dependencies**: Ensure all Python dependencies are installed
5. ✅ **Virtual Environment**: Activate correct virtual environment
6. ✅ **Logs**: Check structured logs and ALS stderr output
7. ✅ **Probes**: Use debugging tools to isolate issues
8. ✅ **Tests**: Run relevant test suite to verify functionality

## Getting Help

If you encounter issues not covered here:

1. **Check existing issues**: [GitHub Issues](https://github.com/abitofhelp/adafmt/issues)
2. **Enable debug logging**: Capture logs for analysis
3. **Use probe tools**: Isolate the problem area
4. **Create minimal reproduction**: Simplify the failing case
5. **Submit detailed bug report**: Include logs, environment info, and reproduction steps

## Related Documentation

- [Development Tools README](../../tools/README.md) - Complete tool documentation
- [Contributing Guide](contributing.md) - Development workflow
- [Testing Guide](testing.md) - Test debugging techniques
- [Troubleshooting Guide](../TROUBLESHOOTING.md) - User-facing troubleshooting

---

*Effective debugging is about systematic investigation. Use the tools available and document your findings.*