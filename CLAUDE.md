# Claude Development Standards for adafmt

This document contains project-specific rules, standards, and context for Claude when working on the adafmt project.

## Documentation Standards

### Markdown File Headers

All markdown files under `/docs` must include the following header pattern:

```markdown
# <Title>

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

<Description paragraph>
```

## Code Standards

### Core Principles

- **No backward compatibility required** - We can use latest Python features and break APIs as needed
- **Professional software engineering** - No hacks, workarounds, or quick fixes without explicit authorization
- **Quality over speed** - Take time to implement solutions properly rather than rushing

### Datetime Formatting Standards

- **Always use ISO 8601 BASIC format** for datetime strings: `YYYYMMDDTHHMMSSZ`
- **Use uppercase Z** for UTC timezone indicator (not lowercase 'z')
- **Use the `to_iso8601_basic()` utility function** from `utils.py` for all datetime formatting
- **Always create timezone-aware datetimes** using `timezone.utc` before formatting
- Example: `20250920T143045Z` (not `2025-09-20T14:30:45Z` or other variants)

### File Headers

All Python source files must include the following header:

```python
# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

Each group must be alphabetically sorted.

### Testing Standards

- All new modules must have comprehensive tests (integration tests preferred for CLI projects)
- Test files must be named `test_<module_name>.py`
- Use pytest for all tests
- Follow AAA pattern: Arrange, Act, Assert
- Include docstrings describing test scenarios
- Unit tests where beneficial, performance tests where performance matters

### Async Code Standards

- Use `asyncio` for all asynchronous operations
- Prefer `async`/`await` over callbacks
- Use `aiofiles` for async file operations
- All async functions must have `_async` suffix or be clearly async from context

## Project-Specific Context

### Current Work: Parallel Worker Implementation

We are implementing a worker pool for parallel post-ALS processing with the following design:
- Queue-based architecture with bounded size (default 100 items)
- Queue memory limit: ~640KB (10 items * 64KB max file size)
- 3 workers by default (configurable via `--num-workers`)
- Thread-safe metrics collection
- Buffered async file I/O (8KB buffer size)
- Out-of-order completion is acceptable

**File Size Context**: Based on Ada project analysis, typical Ada source files are under 64KB, with most being much smaller. 1MB would be excessive.

### Key Commands

Before committing code changes, always run:
- `make lint` - Run linting checks
- `make typecheck` - Run type checking
- `make test` - Run unit tests
- `make test-all` - Run all tests including integration

### Git Workflow

- Work on feature branches (e.g., `parallel-workers`)
- Commit messages must be descriptive and follow conventional commits
- Include Claude attribution in commits:
  ```
  🤖 Generated with [Claude Code](https://claude.ai/code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### Version Management

- Documentation version is fixed at `1.0.0`
- `pyproject.toml` version is managed by python-semantic-release
- Do not manually update version numbers

## Architecture Decisions

### Worker Pool Design

1. **AsyncIO-based**: Use Python's native asyncio for concurrency
2. **Bounded Queue**: Prevent memory issues with maxsize=100
3. **Worker Health Monitoring**: 30-second timeout for health checks
4. **Atomic File Writes**: Use temp file + rename pattern
5. **Graceful Shutdown**: Handle signals and cleanup properly

### Error Handling

- **Comprehensive error handling required** for all error types:
  - Regular exceptions (file I/O, permissions, etc.)
  - Exceptional errors (out of memory, system failures)
  - OS signals (SIGTERM, SIGINT, etc.)
- Log all errors with full context
- Continue processing other files on single file failure
- Collect error messages in metrics (limit 100)
- Report errors to UI via queue
- Graceful degradation where possible
- Clean resource cleanup on all error paths

## Performance Considerations

- File I/O buffer size: 8KB (optimal for typical Ada source files)
- Queue size: 10 items (with 64KB max file size = ~640KB memory)
- Worker count must not exceed (0.6 * CPU cores)
- Monitor queue wait times in metrics
- Track pattern processing vs I/O time separately
- Consider `uvloop` for improved async performance (especially for ALS communication)

## Future Considerations

- **uvloop integration**: Strong candidate for performance improvement given ALS network bottleneck
- May need to implement backpressure if queue fills frequently  
- Could add priority queue for certain file types
- Might benefit from connection pooling for ALS

## Notes for Claude

When working on this project:
1. Always check existing patterns before implementing new features
2. Maintain consistency with established code style
3. Consider Windows compatibility for file operations
4. Test with both small and large Ada projects
5. Keep UI updates non-blocking
6. Preserve existing CLI behavior while adding new features

## Queue Size Recommendations

Based on Ada file size analysis:
- **Queue item limit**: 10 items (down from 100)
- **Max file size assumption**: 64KB per file
- **Total queue memory**: ~640KB maximum
- **Rationale**: Most Ada source files are well under 64KB, and limiting queue size prevents memory bloat while still allowing good parallelism
