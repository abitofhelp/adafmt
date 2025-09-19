# file_discovery Module

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

The `file_discovery` module provides functionality for discovering and filtering Ada source files.

## Overview

This module handles:
- Recursive directory traversal
- Ada file type detection
- Path inclusion/exclusion filtering
- Gitignore-style pattern matching
- Symlink handling
- Performance optimization for large codebases

## Functions

### collect_files()

```python
def collect_files(
    include_paths: List[Path],
    exclude_paths: Optional[List[Path]] = None,
    follow_symlinks: bool = False,
    max_depth: Optional[int] = None
) -> List[Path]:
    """Collect all Ada source files from specified paths.

    This function recursively searches directories for Ada files,
    applying inclusion and exclusion filters.

    Args:
        include_paths: List of paths to search (files or directories)
        exclude_paths: List of paths to exclude from search
        follow_symlinks: Whether to follow symbolic links
        max_depth: Maximum directory depth to search

    Returns:
        List of Path objects for discovered Ada files

    Raises:
        ValueError: If no include paths are provided
        PermissionError: If a directory can't be accessed

    Example:
        >>> files = collect_files(
        ...     include_paths=[Path("src/"), Path("lib/")],
        ...     exclude_paths=[Path("src/generated/")]
        ... )
        >>> print(f"Found {len(files)} Ada files")

    Note:
        - Files are returned in sorted order for consistency
        - Hidden directories (starting with .) are skipped by default
        - Duplicate paths are automatically removed
    """
```

### is_ada_file()

```python
def is_ada_file(path: Path) -> bool:
    """Check if a file is an Ada source file.

    Recognizes the following extensions:
    - .ads (Ada specification)
    - .adb (Ada body)
    - .ada (Generic Ada file)

    Args:
        path: File path to check

    Returns:
        True if the file is an Ada source file

    Example:
        >>> is_ada_file(Path("main.adb"))
        True
        >>> is_ada_file(Path("README.md"))
        False

    Note:
        The check is case-insensitive on case-insensitive filesystems.
    """
```

### should_exclude()

```python
def should_exclude(
    path: Path,
    exclude_paths: List[Path],
    exclude_patterns: Optional[List[str]] = None
) -> bool:
    """Check if a path should be excluded from processing.

    Args:
        path: Path to check
        exclude_paths: List of paths to exclude
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if the path should be excluded

    Example:
        >>> should_exclude(
        ...     Path("src/generated/bindings.ads"),
        ...     exclude_paths=[Path("src/generated")],
        ...     exclude_patterns=["*_test.ad?"]
        ... )
        True
    """
```

### find_project_root()

```python
def find_project_root(start_path: Path) -> Optional[Path]:
    """Find the project root by looking for marker files.

    Searches upward from start_path for:
    - .git directory
    - alire.toml file
    - *.gpr files

    Args:
        start_path: Starting directory for search

    Returns:
        Path to project root or None if not found

    Example:
        >>> root = find_project_root(Path("src/nested/deep/"))
        >>> print(root)
        /home/user/my_project
    """
```

## Pattern Matching

### Gitignore-Style Patterns

The module supports gitignore-style patterns:

```python
patterns = [
    "*.tmp",          # Match all .tmp files
    "test_*.ad?",     # Match test files
    "**/generated/",  # Match generated dirs at any level
    "!important.adb", # Negative pattern (don't exclude)
]

files = collect_files_with_patterns(
    include_paths=[Path(".")],
    exclude_patterns=patterns
)
```

### Pattern Syntax

| Pattern | Matches |
|---------|---------|
| `*.ads` | Any .ads file |
| `test_*` | Files starting with test_ |
| `**/bin/` | bin directories at any level |
| `src/**/test.adb` | test.adb in any subdirectory of src |
| `!keep.ads` | Negation - don't exclude keep.ads |

## Performance Optimization

### Parallel Directory Traversal

For large codebases, use parallel traversal:

```python
async def collect_files_async(
    include_paths: List[Path],
    exclude_paths: Optional[List[Path]] = None,
    max_workers: int = 4
) -> List[Path]:
    """Collect files using parallel directory traversal.

    Args:
        include_paths: Paths to search
        exclude_paths: Paths to exclude
        max_workers: Number of concurrent workers

    Returns:
        List of discovered Ada files

    Example:
        >>> files = await collect_files_async(
        ...     include_paths=[Path("large_project/")],
        ...     max_workers=8
        ... )
    """
```

### Caching

Cache discovered files for repeated runs:

```python
class FileCache:
    """Cache for discovered files with modification tracking."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self._cache = self._load_cache()

    def get_files(
        self,
        include_paths: List[Path],
        exclude_paths: List[Path]
    ) -> Optional[List[Path]]:
        """Get cached files if still valid."""
        key = self._make_key(include_paths, exclude_paths)
        if key in self._cache:
            entry = self._cache[key]
            if self._is_valid(entry):
                return entry['files']
        return None
```

## Advanced Usage

### Custom Filters

Add custom filtering logic:

```python
def collect_files_with_filter(
    include_paths: List[Path],
    filter_func: Callable[[Path], bool]
) -> List[Path]:
    """Collect files with custom filter function.

    Args:
        include_paths: Paths to search
        filter_func: Function to filter files

    Example:
        >>> # Only files modified in last 24 hours
        >>> import time
        >>> cutoff = time.time() - 86400
        >>>
        >>> def recently_modified(path: Path) -> bool:
        ...     return path.stat().st_mtime > cutoff
        >>>
        >>> files = collect_files_with_filter(
        ...     include_paths=[Path("src/")],
        ...     filter_func=recently_modified
        ... )
    """
```

### Project-Aware Discovery

Discover files based on project configuration:

```python
def collect_project_files(project_file: Path) -> List[Path]:
    """Collect files referenced by a GNAT project file.

    Parses the .gpr file and discovers:
    - Source directories
    - Excluded directories
    - Source file patterns

    Args:
        project_file: Path to .gpr file

    Returns:
        List of Ada files in the project

    Example:
        >>> files = collect_project_files(Path("my_project.gpr"))
        >>> # Automatically uses project's source dirs
    """
```

## Integration with Build Systems

### Alire Integration

```python
def collect_alire_files(crate_dir: Path) -> List[Path]:
    """Collect files from an Alire crate.

    Reads alire.toml and discovers:
    - Source directories
    - Dependencies' source files
    - Generated code locations

    Args:
        crate_dir: Path to Alire crate

    Returns:
        List of Ada files in the crate
    """
```

### GPRbuild Integration

```python
def collect_gprbuild_files(
    project_file: Path,
    scenario_variables: Optional[Dict[str, str]] = None
) -> List[Path]:
    """Collect files using GPRbuild's source resolution.

    Args:
        project_file: Path to .gpr file
        scenario_variables: Project scenario variables

    Example:
        >>> files = collect_gprbuild_files(
        ...     Path("project.gpr"),
        ...     scenario_variables={"BUILD_MODE": "debug"}
        ... )
    """
```

## Error Handling

### Permission Errors

Handle directories without read permissions:

```python
def collect_files_safe(
    include_paths: List[Path],
    on_error: Callable[[Path, Exception], None] = None
) -> List[Path]:
    """Collect files with error handling.

    Args:
        include_paths: Paths to search
        on_error: Callback for handling errors

    Example:
        >>> def log_error(path: Path, error: Exception):
        ...     print(f"Warning: Can't read {path}: {error}")
        >>>
        >>> files = collect_files_safe(
        ...     include_paths=[Path("/")],
        ...     on_error=log_error
        ... )
    """
```

### Filesystem Limits

Handle filesystem limitations:

```python
def collect_files_chunked(
    include_paths: List[Path],
    chunk_size: int = 1000
) -> Iterator[List[Path]]:
    """Collect files in chunks to avoid memory issues.

    Yields:
        Chunks of discovered files

    Example:
        >>> for chunk in collect_files_chunked(Path("huge_project/")):
        ...     process_files(chunk)  # Process chunk
        ...     del chunk  # Free memory
    """
```

## Platform Considerations

### Windows Support

Handle Windows-specific issues:

```python
def normalize_path(path: Path) -> Path:
    """Normalize path for cross-platform compatibility.

    Handles:
    - Drive letters
    - UNC paths
    - Path separators
    - Case sensitivity
    """
    if sys.platform == "win32":
        # Normalize drive letters
        path = Path(str(path).replace('/', '\\'))
    return path.resolve()
```

### Case Sensitivity

Handle case-insensitive filesystems:

```python
def is_ada_file_ci(path: Path) -> bool:
    """Case-insensitive Ada file detection."""
    suffix = path.suffix.lower()
    return suffix in {'.ads', '.adb', '.ada'}
```

## Best Practices

1. **Use Explicit Paths**: Prefer explicit include paths over broad searches
2. **Exclude Early**: Filter out unwanted paths as early as possible
3. **Cache Results**: Cache discoveries for large projects
4. **Handle Errors**: Always handle permission and access errors
5. **Follow Standards**: Respect .gitignore and similar conventions

## Testing

### Unit Tests

```python
def test_collect_files_basic(tmp_path):
    """Test basic file collection."""
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.adb").touch()
    (tmp_path / "src" / "utils.ads").touch()
    (tmp_path / "README.md").touch()

    # Collect files
    files = collect_files(include_paths=[tmp_path])

    # Verify
    assert len(files) == 2
    assert all(is_ada_file(f) for f in files)
```

### Performance Tests

```python
def test_collect_files_performance(benchmark, large_project):
    """Benchmark file collection performance."""
    result = benchmark(collect_files, include_paths=[large_project])
    assert len(result) > 1000  # Large project
    assert benchmark.stats['mean'] < 1.0  # Under 1 second
```

## See Also

- [CLI Module](./cli.md) - Uses file discovery
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html)
- [Gitignore Specification](https://git-scm.com/docs/gitignore)
