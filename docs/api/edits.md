# edits Module

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `edits` module handles text transformations and edit operations returned by the Ada Language Server.

## Overview

This module provides functionality to:
- Apply LSP TextEdit operations to files
- Validate edit ranges and content
- Generate unified diffs for review
- Handle concurrent edit operations
- Preserve file attributes and encoding

## Classes

### TextEdit

```python
@dataclass
class TextEdit:
    """Represents a text edit operation from LSP.

    This follows the Language Server Protocol specification for
    text edits, representing a change to a text document.

    Attributes:
        range: The range of text to replace
        newText: The replacement text

    Example:
        >>> edit = TextEdit(
        ...     range=Range(
        ...         start=Position(line=5, character=10),
        ...         end=Position(line=5, character=20)
        ...     ),
        ...     newText="new_identifier"
        ... )
    """
```

### Range

```python
@dataclass
class Range:
    """Represents a text range in a document.

    Ranges are half-open: [start, end), meaning the start position
    is inclusive and the end position is exclusive.

    Attributes:
        start: Starting position (inclusive)
        end: Ending position (exclusive)

    Note:
        Line and character positions are 0-based.
    """
```

### Position

```python
@dataclass
class Position:
    """Represents a position in a text document.

    Attributes:
        line: Zero-based line number
        character: Zero-based character offset in UTF-16 code units

    Important:
        The character offset is in UTF-16 code units, not UTF-8 bytes
        or grapheme clusters. This matches VS Code's model.
    """
```

## Functions

### apply_edits()

```python
def apply_edits(
    file_path: Path,
    edits: List[TextEdit],
    dry_run: bool = False,
    encoding: str = "utf-8"
) -> ApplyResult:
    """Apply text edits to a file.

    This function applies a list of text edits to a file, handling
    overlapping edits and maintaining file integrity.

    Args:
        file_path: Path to the file to edit
        edits: List of TextEdit operations to apply
        dry_run: If True, calculate but don't write changes
        encoding: File encoding (default: utf-8)

    Returns:
        ApplyResult containing:
            - success: Whether all edits were applied
            - modified: Whether the file was changed
            - diff: Unified diff of changes (if any)
            - error: Error message (if failed)

    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file can't be written
        ValueError: If edits are invalid or overlapping

    Example:
        >>> edits = parse_als_response(response)
        >>> result = apply_edits(Path("main.adb"), edits)
        >>> if result.modified:
        ...     print(f"Applied {len(edits)} edits")
        >>> if result.diff:
        ...     print(result.diff)
    """
```

### validate_edits()

```python
def validate_edits(
    content: str,
    edits: List[TextEdit]
) -> ValidationResult:
    """Validate that edits can be applied to content.

    Checks for:
    - Valid position ranges
    - Non-overlapping edits
    - Positions within document bounds

    Args:
        content: Original file content
        edits: List of edits to validate

    Returns:
        ValidationResult with:
            - valid: Whether all edits are valid
            - errors: List of validation errors

    Example:
        >>> content = Path("main.adb").read_text()
        >>> result = validate_edits(content, edits)
        >>> if not result.valid:
        ...     for error in result.errors:
        ...         print(f"Invalid edit: {error}")
    """
```

### sort_edits()

```python
def sort_edits(edits: List[TextEdit]) -> List[TextEdit]:
    """Sort edits in reverse order for safe application.

    Edits are sorted from last to first position to avoid
    invalidating positions when applying earlier edits.

    Args:
        edits: Unsorted list of edits

    Returns:
        List of edits sorted for safe application

    Note:
        This function does not modify the input list.
    """
```

### generate_diff()

```python
def generate_diff(
    original: str,
    modified: str,
    file_path: Path,
    context_lines: int = 3
) -> str:
    """Generate a unified diff between original and modified content.

    Args:
        original: Original file content
        modified: Modified file content
        file_path: Path for diff header
        context_lines: Number of context lines (default: 3)

    Returns:
        Unified diff as a string

    Example:
        >>> original = Path("main.adb").read_text()
        >>> modified = apply_edits_to_string(original, edits)
        >>> diff = generate_diff(original, modified, Path("main.adb"))
        >>> print(diff)
        --- main.adb
        +++ main.adb
        @@ -10,7 +10,7 @@
         procedure Main is
        -   X : Integer:= 1;
        +   X : Integer := 1;
         begin
    """
```

### position_to_offset()

```python
def position_to_offset(
    content: str,
    position: Position,
    encoding: str = "utf-16"
) -> int:
    """Convert an LSP position to a byte offset.

    Args:
        content: File content
        position: LSP position
        encoding: Character encoding for position.character

    Returns:
        Byte offset in the content

    Raises:
        ValueError: If position is out of bounds

    Note:
        LSP uses UTF-16 code units for character positions,
        which differs from Python's string indexing.
    """
```

### offset_to_position()

```python
def offset_to_position(
    content: str,
    offset: int,
    encoding: str = "utf-16"
) -> Position:
    """Convert a byte offset to an LSP position.

    Args:
        content: File content
        offset: Byte offset
        encoding: Character encoding for position.character

    Returns:
        LSP Position

    Raises:
        ValueError: If offset is out of bounds
    """
```

## Edit Application Algorithm

The module uses a robust algorithm for applying edits:

1. **Validation**: Check all edits are valid
2. **Sorting**: Sort edits in reverse order
3. **Conversion**: Convert positions to byte offsets
4. **Application**: Apply edits from last to first
5. **Verification**: Validate the result

```python
def apply_edits_to_string(content: str, edits: List[TextEdit]) -> str:
    """Apply edits to a string and return the result."""
    # Sort edits in reverse order
    sorted_edits = sort_edits(edits)

    # Convert to byte offsets
    result = content
    for edit in sorted_edits:
        start = position_to_offset(result, edit.range.start)
        end = position_to_offset(result, edit.range.end)
        result = result[:start] + edit.newText + result[end:]

    return result
```

## Encoding Considerations

### UTF-16 vs UTF-8

LSP uses UTF-16 code units for positions, while Python typically uses UTF-8:

```python
# Example: Emoji handling
content = "Hello 👋 World"  # 👋 is 2 UTF-16 code units

# UTF-8 byte position of 'W'
utf8_pos = len("Hello 👋 ".encode('utf-8'))  # 10 bytes

# UTF-16 code unit position of 'W'
utf16_pos = len("Hello 👋 ".encode('utf-16-le')) // 2  # 8 code units
```

### Character Encoding Detection

```python
def detect_encoding(file_path: Path) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding'] or 'utf-8'
```

## Error Handling

### Common Errors

1. **Invalid Range**: Position outside document
2. **Overlapping Edits**: Edits that conflict
3. **Encoding Errors**: Invalid UTF-8/UTF-16 sequences
4. **File System Errors**: Permission, disk space

### Error Recovery

```python
try:
    result = apply_edits(file_path, edits)
except ValueError as e:
    # Invalid edit - log and skip file
    logger.error(f"Invalid edit for {file_path}: {e}")
except PermissionError as e:
    # Can't write - report to user
    ui.error(f"Permission denied: {file_path}")
except Exception as e:
    # Unexpected error - preserve original file
    logger.exception(f"Failed to apply edits to {file_path}")
    raise
```

## Performance Optimization

### Large File Handling

For files over 1MB, the module uses streaming:

```python
def apply_edits_streaming(
    file_path: Path,
    edits: List[TextEdit],
    chunk_size: int = 8192
) -> None:
    """Apply edits to large files efficiently."""
    with open(file_path, 'r+', encoding='utf-8') as f:
        # Memory-mapped file for efficient access
        with mmap.mmap(f.fileno(), 0) as mmapped:
            apply_edits_to_mmap(mmapped, edits)
```

### Batch Operations

Process multiple files efficiently:

```python
async def apply_edits_batch(
    edits_map: Dict[Path, List[TextEdit]],
    max_concurrent: int = 10
) -> Dict[Path, ApplyResult]:
    """Apply edits to multiple files concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def apply_one(path, edits):
        async with semaphore:
            return await asyncio.to_thread(apply_edits, path, edits)

    tasks = [apply_one(p, e) for p, e in edits_map.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return dict(zip(edits_map.keys(), results))
```

## Testing

### Unit Test Example

```python
def test_apply_single_edit():
    """Test applying a single edit."""
    content = "Hello World"
    edit = TextEdit(
        range=Range(
            start=Position(0, 6),
            end=Position(0, 11)
        ),
        newText="Python"
    )

    result = apply_edits_to_string(content, [edit])
    assert result == "Hello Python"
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    content=st.text(),
    line=st.integers(min_value=0),
    char=st.integers(min_value=0),
    new_text=st.text()
)
def test_edit_properties(content, line, char, new_text):
    """Test edit properties with random inputs."""
    # Ensure position is valid
    lines = content.split('\n')
    if line >= len(lines):
        return

    # Apply edit
    edit = TextEdit(
        range=Range(
            start=Position(line, char),
            end=Position(line, char)
        ),
        newText=new_text
    )

    # Verify properties
    result = apply_edits_to_string(content, [edit])
    assert new_text in result
    assert len(result) == len(content) + len(new_text)
```

## See Also

- [Language Server Protocol - Text Edits](https://microsoft.github.io/language-server-protocol/specifications/specification-current/#textEdit)
- [ALS Client Module](./als_client.md) - Source of edits
- [CLI Module](./cli.md) - Edit application control
