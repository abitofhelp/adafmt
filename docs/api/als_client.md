# als_client Module

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `als_client` module provides the core functionality for communicating with the Ada Language Server (ALS) using the Language Server Protocol (LSP).

## Overview

This module implements a robust client for the Ada Language Server that handles:
- Process lifecycle management
- LSP protocol communication
- Request/response correlation
- Error recovery and retry logic
- Graceful shutdown procedures

## Classes

### ALSClient

```python
class ALSClient:
    """Asynchronous client for communicating with the Ada Language Server.

    This client manages the lifecycle of an ALS process and provides methods
    for formatting Ada source files using the Language Server Protocol.

    Attributes:
        project_path (Path): Path to the GNAT project file
        logger (JsonlLogger): Logger instance for debugging
        process (subprocess.Popen): ALS process handle
        reader (asyncio.StreamReader): Async reader for ALS stdout
        writer (asyncio.StreamWriter): Async writer for ALS stdin

    Example:
        >>> async with ALSClient(project_path="project.gpr") as client:
        ...     edits = await client.format_file("src/main.adb")
        ...     print(f"Got {len(edits)} edits")
    """
```

#### Methods

##### `__init__(self, project_path: Path, logger: JsonlLogger, stderr_writer=None)`

Initialize the ALS client.

**Parameters:**
- `project_path` (Path): Path to the GNAT project file (.gpr)
- `logger` (JsonlLogger): Logger instance for structured logging
- `stderr_writer` (Optional): File handle for capturing ALS stderr

**Raises:**
- `ValueError`: If project_path is not a valid .gpr file

##### `async start(self) -> None`

Start the ALS process and initialize LSP connection.

**Process:**
1. Launch ALS subprocess
2. Set up async I/O streams
3. Send initialize request
4. Wait for server capabilities
5. Send initialized notification

**Raises:**
- `ALSStartupError`: If ALS fails to start
- `ALSProtocolError`: If initialization fails

##### `async format_file(self, file_path: Path) -> List[TextEdit]`

Format a single Ada file and return edit operations.

**Parameters:**
- `file_path` (Path): Path to the Ada file to format

**Returns:**
- List[TextEdit]: List of text edits to apply

**Raises:**
- `ALSProtocolError`: If formatting request fails
- `asyncio.TimeoutError`: If request times out

**Example:**
```python
edits = await client.format_file("src/package.ads")
for edit in edits:
    print(f"Replace {edit.range} with {edit.newText}")
```

##### `async shutdown(self) -> None`

Gracefully shut down the ALS process.

**Process:**
1. Send shutdown request
2. Send exit notification
3. Wait for process termination
4. Clean up resources

### ALSProtocolError

```python
class ALSProtocolError(Exception):
    """Raised when LSP protocol communication fails.

    Attributes:
        message (str): Error description
        code (int): LSP error code if available
        data (Any): Additional error data
    """
```

### ALSStartupError

```python
class ALSStartupError(Exception):
    """Raised when ALS process fails to start.

    Attributes:
        command (List[str]): The command that failed
        stderr (str): Captured stderr output
    """
```

## Functions

### build_als_command(project_path: Path, config: Dict) -> List[str]

Build the command line for launching ALS.

**Parameters:**
- `project_path` (Path): Path to the project file
- `config` (Dict): Configuration options

**Returns:**
- List[str]: Command line arguments

**Example:**
```python
cmd = build_als_command(Path("project.gpr"), {"traces": "debug"})
# Returns: ["ada_language_server", "--project", "project.gpr", "--trace=debug"]
```

### create_format_request(file_uri: str, content: str) -> Dict

Create an LSP textDocument/formatting request.

**Parameters:**
- `file_uri` (str): File URI (file:///path/to/file)
- `content` (str): File content

**Returns:**
- Dict: LSP request message

### parse_lsp_message(data: bytes) -> Dict

Parse an LSP message from raw bytes.

**Parameters:**
- `data` (bytes): Raw message data

**Returns:**
- Dict: Parsed JSON-RPC message

**Raises:**
- `ALSProtocolError`: If message is malformed

## Protocol Details

### Message Format

LSP messages follow the format:
```
Content-Length: <length>\r\n
\r\n
<JSON-RPC content>
```

### Request/Response Correlation

Requests include an ID for correlation:
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "textDocument/formatting",
    "params": {...}
}
```

Responses reference the request ID:
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": [...]
}
```

## Error Handling

The module implements comprehensive error handling:

1. **Startup Errors**: Detected during process launch
2. **Protocol Errors**: Invalid messages or responses
3. **Timeout Errors**: Requests exceeding time limits
4. **Process Errors**: ALS crashes or hangs

### Retry Logic

Failed operations are retried with exponential backoff:
```python
for attempt in range(max_retries):
    try:
        return await operation()
    except ALSProtocolError as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
        else:
            raise
```

## Performance Considerations

1. **Connection Reuse**: Single ALS process for multiple files
2. **Async I/O**: Non-blocking communication
3. **Streaming**: Large files processed in chunks
4. **Resource Cleanup**: Automatic process termination

## Debugging

Enable detailed logging:
```python
logger = JsonlLogger("debug.jsonl")
client = ALSClient(project_path, logger)
```

Log entries include:
- Request/response payloads
- Timing information
- Error details
- Process lifecycle events

## Thread Safety

The ALSClient is not thread-safe. Use separate instances for concurrent operations or protect with locks:
```python
import asyncio

lock = asyncio.Lock()

async with lock:
    result = await client.format_file(path)
```

## See Also

- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [Ada Language Server Documentation](https://github.com/AdaCore/ada_language_server)
- [edits Module](./edits.md) - Apply formatting results
