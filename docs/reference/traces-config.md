# Default Traces Config Implementation Summary

## Problem Solved
As confirmed by GPT-5, ALS does not emit its log file path to stderr in any predictable way. This meant that without using `--als-traces-config-path`, users would always see "ALS Log: Not configured" in the UI summary.

## Solution Implemented
When `--als-traces-config-path` is not provided, adafmt now automatically:

1. Creates a temporary directory with prefix `adafmt_als_`
2. Generates a default GNATCOLL traces configuration file in that directory
3. Configures ALS to log to `<temp_dir>/als.log`
4. Passes the config to ALS using `--tracefile=<config>`
5. Displays the ALS log path in the UI
6. Cleans up the temporary directory on exit

## Code Changes

### cli.py
- Added logic to create default traces config when not provided by user
- Uses Python's `tempfile.mkdtemp()` for safe temporary directory creation
- Registers cleanup function with `atexit` to remove temp files
- Default config enables `ALS.MAIN=yes` for main logging

### als_client.py
- Removed code that attempted to parse ALS log path from stderr (confirmed by GPT-5 to not work)

### Help Text
- Updated `--als-traces-config-path` help to mention: "If not provided, a default config is created in a temp directory"

## Testing
Created comprehensive test suite in `tests/test_traces_config.py`:

1. **TestTracesConfigParsing**: Tests the config file parser
   - Simple absolute paths
   - Relative paths (resolved against config file directory)
   - Paths with spaces
   - Windows-style paths
   - Missing/invalid configs

2. **TestDefaultTracesConfig**: Tests the default config creation
   - Verifies temp config is created when flag not provided
   - Verifies user-provided config is respected when given
   - Checks correct paths are passed to ALSClient

## User Experience
Before: "ALS Log: Not configured"
After: "ALS Log: /var/folders/.../adafmt_als_xyz/als.log"

Users can now always see where ALS logs are being written, making debugging easier.