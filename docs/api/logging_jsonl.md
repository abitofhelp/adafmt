# logging_jsonl Module

**Version:** 1.0.1
**Date:** 2025-09-20T00:34:23.357320Z
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `logging_jsonl` module provides structured logging in JSON Lines format for debugging and analysis.

## Overview

This module implements:
- Thread-safe JSONL (JSON Lines) logging
- Automatic timestamp generation
- Structured event logging
- Performance metrics
- Log rotation and compression
- Real-time log streaming

## Classes

### JsonlLogger

```python
class JsonlLogger:
    """Thread-safe logger that writes JSON Lines format.

    JSONL format writes one JSON object per line, making it easy to
    process with standard tools like jq, grep, and Python.

    Attributes:
        file_path: Path to the log file
        file_handle: Open file handle
        lock: Threading lock for concurrent access
        start_time: Logger creation timestamp

    Example:
        >>> logger = JsonlLogger("debug.jsonl")
        >>> logger.info("Starting formatting", file="main.adb")
        >>> logger.error("Format failed", file="utils.ads", reason="Syntax error")
        >>> logger.close()

    Output:
        {"timestamp":"2025-01-14T10:30:45.123Z","level":"INFO","message":"Starting formatting","file":"main.adb"}
        {"timestamp":"2025-01-14T10:30:45.234Z","level":"ERROR","message":"Format failed","file":"utils.ads","reason":"Syntax error"}
    """
```

#### Methods

##### `__init__(self, file_path: Union[str, Path], mode: str = "a", buffer_size: int = 8192)`

Initialize the JSONL logger.

**Parameters:**
- `file_path`: Path to the log file
- `mode`: File open mode ("a" for append, "w" for write)
- `buffer_size`: Buffer size for file I/O

**Example:**
```python
# Append to existing log
logger = JsonlLogger("app.jsonl")

# Create new log (overwrite)
logger = JsonlLogger("debug.jsonl", mode="w")

# Large buffer for high-volume logging
logger = JsonlLogger("trace.jsonl", buffer_size=65536)
```

##### `log(self, level: str, message: str, **kwargs) -> None`

Log a message with arbitrary fields.

**Parameters:**
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Main log message
- `**kwargs`: Additional fields to include

**Example:**
```python
logger.log("INFO", "Processing file",
    file="main.adb",
    size=1024,
    edits=5
)
```

##### `info(self, message: str, **kwargs) -> None`

Log an informational message.

**Example:**
```python
logger.info("File formatted successfully",
    file="main.adb",
    duration_ms=125,
    edits_applied=3
)
```

##### `error(self, message: str, **kwargs) -> None`

Log an error message.

**Example:**
```python
logger.error("Failed to connect to ALS",
    command=["ada_language_server"],
    exit_code=1,
    stderr="Connection refused"
)
```

##### `debug(self, message: str, **kwargs) -> None`

Log a debug message.

**Example:**
```python
logger.debug("LSP request",
    method="textDocument/formatting",
    params={"textDocument": {"uri": "file:///src/main.adb"}}
)
```

##### `metric(self, name: str, value: float, unit: str = None, **kwargs) -> None`

Log a performance metric.

**Parameters:**
- `name`: Metric name
- `value`: Numeric value
- `unit`: Optional unit of measurement
- `**kwargs`: Additional context

**Example:**
```python
logger.metric("format_duration", 125.5, unit="ms", file="main.adb")
logger.metric("memory_usage", 45.2, unit="MB")
logger.metric("files_processed", 150)
```

##### `exception(self, message: str, exc_info: Exception = None, **kwargs) -> None`

Log an exception with traceback.

**Parameters:**
- `message`: Error description
- `exc_info`: Exception object or sys.exc_info()
- `**kwargs`: Additional context

**Example:**
```python
try:
    result = process_file(path)
except Exception as e:
    logger.exception("File processing failed",
        exc_info=e,
        file=str(path)
    )
```

##### `start_operation(self, operation: str, **kwargs) -> str`

Start tracking an operation with timing.

**Returns:**
- Operation ID for correlation

**Example:**
```python
op_id = logger.start_operation("format_file", file="main.adb")
# ... do work ...
logger.end_operation(op_id, success=True, edits=5)
```

##### `end_operation(self, operation_id: str, success: bool = True, **kwargs) -> None`

End a tracked operation and log duration.

**Example:**
```python
op_id = logger.start_operation("als_request", method="textDocument/formatting")
try:
    result = await client.format()
    logger.end_operation(op_id, success=True, edits=len(result))
except Exception as e:
    logger.end_operation(op_id, success=False, error=str(e))
```

## Log Entry Format

### Standard Fields

Every log entry includes:

```json
{
    "timestamp": "2025-01-14T10:30:45.123Z",
    "level": "INFO",
    "message": "Log message",
    "logger": "adafmt",
    "thread": "MainThread",
    "process": 12345
}
```

### Custom Fields

Add domain-specific fields:

```json
{
    "timestamp": "2025-01-14T10:30:45.123Z",
    "level": "INFO",
    "message": "File formatted",
    "file": "src/main.adb",
    "duration_ms": 125,
    "edits": 5,
    "changed": true
}
```

## Log Analysis

### Using jq

Query logs with jq:

```bash
# All errors
jq 'select(.level == "ERROR")' debug.jsonl

# Files that took over 1 second
jq 'select(.duration_ms > 1000)' debug.jsonl

# Summary statistics
jq -s 'group_by(.level) | map({level: .[0].level, count: length})' debug.jsonl

# Average formatting time
jq -s 'map(select(.metric == "format_duration")) | add / length' debug.jsonl
```

### Using Python

Process logs programmatically:

```python
import json
from pathlib import Path

def analyze_logs(log_path: Path):
    """Analyze JSONL logs."""
    errors = []
    metrics = []

    with open(log_path) as f:
        for line in f:
            entry = json.loads(line)

            if entry['level'] == 'ERROR':
                errors.append(entry)

            if 'metric' in entry:
                metrics.append(entry)

    print(f"Found {len(errors)} errors")
    print(f"Collected {len(metrics)} metrics")

    # Calculate average formatting time
    format_times = [m['value'] for m in metrics
                    if m.get('metric') == 'format_duration']
    if format_times:
        avg_time = sum(format_times) / len(format_times)
        print(f"Average format time: {avg_time:.2f}ms")
```

## Performance

### Buffered Writing

The logger uses buffered I/O for performance:

```python
logger = JsonlLogger("high_volume.jsonl", buffer_size=65536)

# Buffer is flushed:
# - When buffer is full
# - On logger.flush()
# - On logger.close()
# - On program exit
```

### Async Logging

For high-performance async logging:

```python
class AsyncJsonlLogger:
    """Asynchronous JSONL logger using asyncio."""

    def __init__(self, file_path: Path):
        self.queue = asyncio.Queue()
        self.file_path = file_path
        self.writer_task = asyncio.create_task(self._writer())

    async def log(self, level: str, message: str, **kwargs):
        """Queue a log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            **kwargs
        }
        await self.queue.put(entry)

    async def _writer(self):
        """Background writer task."""
        async with aiofiles.open(self.file_path, 'a') as f:
            while True:
                entry = await self.queue.get()
                if entry is None:  # Shutdown signal
                    break
                await f.write(json.dumps(entry) + '\n')
```

## Log Rotation

### Size-Based Rotation

```python
class RotatingJsonlLogger(JsonlLogger):
    """JSONL logger with size-based rotation."""

    def __init__(self, file_path: Path, max_bytes: int = 10_000_000):
        self.max_bytes = max_bytes
        super().__init__(file_path)

    def _check_rotation(self):
        """Check if rotation is needed."""
        if self.file_path.stat().st_size > self.max_bytes:
            self._rotate()

    def _rotate(self):
        """Rotate the log file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = self.file_path.with_suffix(f".{timestamp}.jsonl")
        self.file_path.rename(rotated_path)

        # Optionally compress
        import gzip
        with open(rotated_path, 'rb') as f_in:
            with gzip.open(f"{rotated_path}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        rotated_path.unlink()
```

### Time-Based Rotation

```python
def get_daily_logger() -> JsonlLogger:
    """Get a logger that creates daily log files."""
    today = datetime.now().strftime("%Y%m%d")
    log_path = Path(f"logs/adafmt_{today}.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    return JsonlLogger(log_path)
```

## Real-Time Monitoring

### Log Streaming

Stream logs as they're written:

```python
def stream_logs(log_path: Path, follow: bool = True):
    """Stream log entries in real-time."""
    import time

    with open(log_path, 'r') as f:
        if follow:
            # Go to end of file
            f.seek(0, 2)

        while True:
            line = f.readline()
            if line:
                entry = json.loads(line)
                yield entry
            elif follow:
                time.sleep(0.1)
            else:
                break

# Usage
for entry in stream_logs(Path("debug.jsonl")):
    if entry['level'] == 'ERROR':
        print(f"ERROR: {entry['message']}")
```

### Dashboard Integration

Export metrics for monitoring:

```python
def export_prometheus_metrics(log_path: Path):
    """Export metrics in Prometheus format."""
    from prometheus_client import Counter, Histogram, start_http_server

    # Define metrics
    files_processed = Counter('adafmt_files_processed_total',
                             'Total files processed')
    format_duration = Histogram('adafmt_format_duration_seconds',
                               'Time to format file')

    # Process logs
    with open(log_path) as f:
        for line in f:
            entry = json.loads(line)

            if entry.get('event') == 'file_formatted':
                files_processed.inc()
                if 'duration_ms' in entry:
                    format_duration.observe(entry['duration_ms'] / 1000)

    # Start metrics server
    start_http_server(8000)
```

## Security Considerations

### Sensitive Data

Avoid logging sensitive information:

```python
def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive fields from log data."""
    sensitive_keys = {'password', 'token', 'api_key', 'secret'}

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
```

### Log Injection

Prevent log injection attacks:

```python
def safe_log_value(value: Any) -> Any:
    """Sanitize values to prevent log injection."""
    if isinstance(value, str):
        # Remove newlines and control characters
        return value.replace('\n', '\\n').replace('\r', '\\r')
    return value
```

## Best Practices

1. **Use Structured Fields**: Add semantic fields rather than embedding in messages
2. **Include Context**: Always include relevant context (file, operation, etc.)
3. **Log Levels**: Use appropriate log levels consistently
4. **Performance Metrics**: Track key performance indicators
5. **Error Details**: Include full error context and stack traces
6. **Correlation IDs**: Use operation IDs to correlate related log entries

## Testing

### Mock Logger

For testing without file I/O:

```python
class MockJsonlLogger(JsonlLogger):
    """In-memory logger for testing."""

    def __init__(self):
        self.entries = []
        self.lock = threading.Lock()

    def _write_entry(self, entry: dict):
        """Store entry in memory instead of file."""
        with self.lock:
            self.entries.append(entry)

    def get_entries(self, level: str = None) -> List[dict]:
        """Get logged entries, optionally filtered by level."""
        if level:
            return [e for e in self.entries if e['level'] == level]
        return self.entries.copy()
```

## See Also

- [JSON Lines Format](https://jsonlines.org/)
- [jq Manual](https://stedolan.github.io/jq/manual/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [CLI Module](./cli.md) - Logger initialization
