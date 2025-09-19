# Contributing to adafmt

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This guide covers the development workflow, how to add new features, and the contribution process for adafmt.

## Development Workflow

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Run tests frequently**:
   ```bash
   # Quick unit tests
   make test
   
   # Full test suite
   make test-all
   
   # With coverage
   make coverage
   ```

4. **Check code quality**:
   ```bash
   make lint
   make typecheck
   make format
   ```

### Testing Strategy

The project uses a comprehensive testing approach:

#### Unit Tests (Fast)
```bash
# Run only unit tests (no ALS required)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=adafmt
```

#### Integration Tests (Slower)
```bash
# Run integration tests (requires ALS)
pytest tests/integration/ -v

# Skip ALS-dependent tests
pytest tests/integration/ -m "not requires_als"
```

#### All Tests
```bash
# Run everything
pytest -v

# With coverage and HTML report
pytest --cov=adafmt --cov-report=html
```

### Code Quality

The project maintains high code quality through:

#### Linting with Ruff
```bash
make lint
# Or directly: ruff check src/ tests/
```

#### Type Checking with MyPy
```bash
make typecheck
# Or directly: mypy src/adafmt/
```

#### Code Formatting with Black
```bash
make format
# Or directly: black src/ tests/ tools/
```

### Pre-commit Checklist

Before committing, ensure:

1. ✅ All tests pass: `make test-all`
2. ✅ Code is formatted: `make format`
3. ✅ No lint issues: `make lint`
4. ✅ Type checking passes: `make typecheck`
5. ✅ Documentation is updated if needed
6. ✅ Commit message follows conventional format

## Adding New Features

### Design Principles

- **Modularity**: Clear separation of concerns
- **Testability**: Easy to unit test with minimal mocking
- **Performance**: Efficient file processing and ALS communication
- **Reliability**: Robust error handling and recovery
- **Extensibility**: Plugin architecture for custom formatters

### Core Components

#### ALSClient (`als_client.py`)
- Manages Ada Language Server process lifecycle
- Implements LSP protocol communication
- Handles timeouts and error recovery
- Provides async interface for formatting requests

#### CLI (`cli.py`)
- Modern CLI built with Typer
- Multiple UI modes (pretty, plain, JSON, quiet)
- Configuration management
- Progress reporting and user feedback

#### Text Editing (`edits.py`)
- Applies LSP TextEdit operations
- Handles Unicode correctly (UTF-16 vs UTF-8)
- Generates unified diffs
- Validates edit operations

#### File Discovery (`file_discovery.py`)
- Discovers Ada files recursively
- Supports include/exclude patterns
- Handles symlinks and permissions
- Optimized for large codebases

#### Terminal UI (`tui.py`)
- Multiple UI modes for different contexts
- Progress bars and live updates
- Color support with automatic fallback
- JSON output for programmatic use

### Data Flow

```
CLI Input → File Discovery → ALS Client → Text Edits → File Writing
     ↓            ↓              ↓           ↓           ↓
   Config    File List    Format Requests  Edit Ops   Results
     ↓            ↓              ↓           ↓           ↓
    UI      Progress UI   Protocol Msgs   Diff Gen    Summary
```

### Adding a New CLI Option

1. **Update CLI definition** in `cli.py`:
   ```python
   def main(
       # ... existing options ...
       new_option: bool = typer.Option(False, help="Description")
   ):
   ```

2. **Add tests** in `tests/unit/test_cli.py`:
   ```python
   def test_new_option_handling():
       """Test new CLI option behavior."""
       # Test implementation
   ```

3. **Update documentation** in relevant files

### Adding a New UI Mode

1. **Create UI class** in `tui.py`:
   ```python
   class NewUI(UserInterface):
       """New UI implementation."""
       
       def start(self): ...
       def update_file(self, path): ...
       def report_result(self, path, changed, error): ...
       def finish(self): ...
   ```

2. **Update UI factory** in `make_ui()` function

3. **Add comprehensive tests**

### Extending ALS Communication

1. **Add new methods** to `ALSClient`:
   ```python
   async def new_request(self, params):
       """New LSP request."""
       return await self._send_request("method", params)
   ```

2. **Add protocol definitions** if needed

3. **Comprehensive testing** with mocks

## Contributing Process

### Contribution Workflow

1. **Fork** the repository
2. **Create** feature branch
3. **Make** changes with tests
4. **Submit** pull request
5. **Address** review feedback

### Pull Request Guidelines

- **Clear title**: Describe the change
- **Detailed description**: What and why
- **Tests included**: New functionality must have tests
- **Documentation updated**: If API changes
- **Linear history**: Rebase before merging

### Code Review Checklist

- ✅ Code follows style guidelines
- ✅ Tests cover new functionality
- ✅ Documentation is updated
- ✅ No breaking changes without justification
- ✅ Performance impact is considered

## Release Process

### Semantic Release

The project uses semantic release with conventional commits:

```bash
# Feature
feat: add new formatting option

# Bug fix
fix: handle empty files correctly

# Breaking change
feat!: change CLI argument format
```

### Version Management

- **Single source**: Version in `pyproject.toml`
- **Dynamic loading**: Runtime version from package metadata
- **Automatic release**: GitHub Actions handles releases

### Release Checklist

1. ✅ All tests pass
2. ✅ Documentation is updated
3. ✅ CHANGELOG is updated (automatic)
4. ✅ Version is bumped (automatic)
5. ✅ Release notes are complete
6. ✅ Distribution packages are built

## Getting Help

If you need assistance with contributions:

- **Issues**: [GitHub Issues](https://github.com/abitofhelp/adafmt/issues)
- **Discussions**: [GitHub Discussions](https://github.com/abitofhelp/adafmt/discussions)
- **Testing Guide**: [testing.md](testing-guide.md)
- **Debugging Guide**: [troubleshooting-guide.md](troubleshooting-guide.md)

---

*This guide is a living document. Please update it as the project evolves.*