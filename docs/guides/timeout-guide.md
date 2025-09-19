# ALS Timeout Improvements Documentation

**Version:** 0.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  

## Overview

This document details the comprehensive timeout improvements implemented in adafmt to handle Ada Language Server (ALS) communication more robustly and provide better user experience when dealing with slow or unresponsive ALS instances.

## Key Improvements

### 1. Configurable Timeout Parameters

#### 1.1 Initialization Timeout (`--init-timeout`)
- **Default**: 180 seconds (3 minutes)
- **Purpose**: Controls how long to wait for ALS to fully initialize
- **Usage**: `adafmt --init-timeout 240 --project-path project.gpr`
- **Rationale**: Large projects with many dependencies can take longer to initialize

#### 1.2 Format Timeout (`--format-timeout`)
- **Default**: 60 seconds (1 minute)
- **Purpose**: Controls timeout for individual file formatting requests
- **Usage**: `adafmt --format-timeout 120 --project-path project.gpr`
- **Rationale**: Complex files or slow systems may need more time

#### 1.3 Hook Timeouts
- **Default**: 60 seconds for both pre-hook and post-hook
- **Purpose**: Prevents hanging on user-defined hook commands
- **Configuration**: Hard-coded but documented in help text
- **Behavior**: Timeout logged as warning, execution continues

### 2. Consecutive Timeout Protection

#### 2.1 Maximum Consecutive Timeouts (`--max-consecutive-timeouts`)
- **Default**: 5 consecutive timeouts
- **Purpose**: Prevents endless hanging on consistently failing ALS instances
- **Usage**: `adafmt --max-consecutive-timeouts 3 --project-path project.gpr`
- **Behavior**: 
  - Counts consecutive timeout failures
  - Resets counter on successful operations
  - Aborts execution when limit is reached
  - Provides diagnostic suggestions

#### 2.2 Timeout Counter Reset
- **Behavior**: Counter is reset to 0 on any successful file formatting
- **Purpose**: Allows recovery from temporary ALS issues
- **Implementation**: Distinguishes between persistent and transient problems

### 3. Enhanced Error Reporting

#### 3.1 Detailed Timeout Messages
```json
{
  "event": "format_timeout",
  "file": "src/complex_package.adb",
  "format_timeout_s": 60,
  "suggestion": "Try lower timeout or increase --init-timeout; check ALS log"
}
```

#### 3.2 Consecutive Timeout Warnings
```json
{
  "event": "consecutive_timeouts",
  "count": 3,
  "max_allowed": 5,
  "action": "Investigate ALS; try --preflight aggressive, increase --init-timeout"
}
```

### 4. Request-Level Timeout Implementation

#### 4.1 `request_with_timeout()` Method
- **Location**: `ALSClient.request_with_timeout()`
- **Purpose**: Implements per-request timeout with proper cleanup
- **Features**:
  - Correlation ID tracking
  - Automatic cleanup on timeout
  - Proper asyncio integration

```python
async def request_with_timeout(self, msg: JsonDict, timeout: float) -> Any:
    """Send a request and wait for response with timeout.
    
    Args:
        msg: JSON-RPC message to send
        timeout: Maximum seconds to wait for response
        
    Returns:
        Response data from ALS
        
    Raises:
        asyncio.TimeoutError: If no response within timeout
        ALSProtocolError: If response contains error
    """
```

#### 4.2 Graceful Timeout Handling
- **Cleanup**: Pending requests are properly cleaned up on timeout
- **Logging**: Timeout events are logged with context
- **Recovery**: System can continue after timeout without corruption

### 5. Process Management Timeouts

#### 5.1 Shutdown Timeouts
- **ALS Process**: 2-second timeout for graceful shutdown
- **stderr Task**: 2-second timeout for stderr processing cleanup
- **Purpose**: Prevents hanging during cleanup operations

#### 5.2 Process Lifecycle Timeouts
- **Initialization**: Configurable via `--init-timeout`
- **Request Processing**: Configurable via `--format-timeout`
- **Shutdown**: Fixed 2-second timeout for cleanup

## Usage Examples

### 1. High-Latency Environments
```bash
# For slow networks or systems
adafmt --init-timeout 300 --format-timeout 120 \
       --project-path project.gpr
```

### 2. Aggressive Timeout for CI/CD
```bash
# For fast failure in automated environments
adafmt --init-timeout 60 --format-timeout 30 \
       --max-consecutive-timeouts 2 \
       --project-path project.gpr
```

### 3. Debugging ALS Issues
```bash
# More lenient settings for troubleshooting
adafmt --init-timeout 600 --format-timeout 180 \
       --max-consecutive-timeouts 10 \
       --preflight aggressive \
       --project-path project.gpr
```

## Timeout Tuning Guidelines

### 1. Initialization Timeout Tuning

| Project Size | Recommended Init Timeout | Rationale |
|-------------|-------------------------|-----------|
| Small (< 100 files) | 60-120 seconds | Quick startup |
| Medium (100-1000 files) | 180-300 seconds | Standard projects |
| Large (> 1000 files) | 300-600 seconds | Complex dependencies |

### 2. Format Timeout Tuning

| File Complexity | Recommended Format Timeout | Rationale |
|----------------|---------------------------|-----------|
| Simple procedures | 30-60 seconds | Basic formatting |
| Package specs | 60-120 seconds | More complex analysis |
| Large packages | 120-300 seconds | Extensive processing |

### 3. Consecutive Timeout Limits

| Environment | Recommended Limit | Rationale |
|------------|-------------------|-----------|
| CI/CD | 2-3 | Fail fast |
| Development | 5-10 | Allow debugging |
| Large batch operations | 10-20 | Handle transient issues |

## Troubleshooting Timeout Issues

### 1. Persistent Initialization Timeouts

**Symptoms**: ALS never fully initializes
**Solutions**:
1. Increase `--init-timeout`
2. Use `--preflight aggressive` to clean up stale processes
3. Check ALS stderr output
4. Verify project file is valid

### 2. Frequent Format Timeouts

**Symptoms**: Individual files consistently timeout
**Solutions**:
1. Increase `--format-timeout`
2. Check for very large or complex files
3. Verify ALS is responding (use debug tools)
4. Consider excluding problematic files temporarily

### 3. Intermittent Timeouts

**Symptoms**: Occasional timeouts, system recovers
**Solutions**:
1. Monitor system resources
2. Increase timeout margins
3. Check for background processes affecting performance
4. Use timeout protection (increase `--max-consecutive-timeouts`)

## Implementation Details

### 1. Timeout Architecture

```
CLI Parameters → Configuration → ALSClient → asyncio.wait_for()
     ↓               ↓              ↓              ↓
  User Intent → Runtime Config → Request Mgmt → OS-Level Timeout
```

### 2. State Management

- **Timeout Counters**: Thread-safe tracking of consecutive failures
- **Request Correlation**: Proper cleanup of timed-out requests
- **Process State**: Monitoring of ALS process health

### 3. Error Recovery

- **Graceful Degradation**: System continues after timeouts when possible
- **Resource Cleanup**: Prevents resource leaks on timeout
- **User Feedback**: Clear messages about timeout causes and solutions

## Monitoring and Diagnostics

### 1. Timeout Logging

All timeout events are logged in JSONL format:
```json
{"timestamp": "2025-01-14T10:30:45.123Z", "level": "ERROR", "event": "format_timeout", "file": "src/main.adb", "timeout_seconds": 60}
{"timestamp": "2025-01-14T10:30:45.234Z", "level": "WARNING", "event": "consecutive_timeout", "count": 3, "max": 5}
{"timestamp": "2025-01-14T10:30:45.345Z", "level": "ERROR", "event": "timeout_limit_exceeded", "consecutive_count": 5}
```

### 2. Performance Metrics

Monitor timeout-related metrics:
- Average initialization time
- Per-file format time distribution
- Timeout frequency by file type
- Consecutive timeout patterns

### 3. Health Checks

Use development tools for ALS health checking:
```bash
# Test ALS responsiveness
python tools/als_rpc_probe.py --project-path project.gpr --verbose

# Test with custom timeouts
python tools/als_rpc_probe.py --project-path project.gpr \
    --init-timeout 120 --format-timeout 30
```

## Future Improvements

### 1. Adaptive Timeouts
- **Dynamic adjustment** based on file complexity
- **Learning system** that adapts to project characteristics
- **Performance history** to optimize timeout values

### 2. Advanced Recovery
- **ALS restart** on persistent timeouts
- **Partial processing** for large files
- **Intelligent retry** with backoff strategies

### 3. Enhanced Diagnostics
- **Performance profiling** of ALS operations
- **Resource usage monitoring** during timeouts
- **Predictive timeout warnings** based on system state

## Best Practices

1. **Start Conservative**: Begin with default timeouts and adjust based on experience
2. **Monitor Patterns**: Watch for timeout patterns that indicate systemic issues
3. **Environment-Specific**: Tune timeouts for specific deployment environments
4. **Document Settings**: Record timeout settings and rationale for team use
5. **Regular Review**: Periodically review and adjust timeout settings as projects evolve

## See Also

- [Troubleshooting Guide](TROUBLESHOOTING.md) - General troubleshooting information
- [Developer Guide](DEVELOPER_GUIDE.md) - Implementation details
- [Tools Documentation](../tools/README.md) - Debugging tools
- [ALS Client API](api/als_client.md) - Technical implementation details