# Developer Resource Overview

**Document Version:** 1.0.0  
**Date:** January 2025  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This document provides a comprehensive overview of all developer resources for adafmt. It serves as a central hub linking to focused documentation for different aspects of development.

## Quick Start Path

For new developers, follow this recommended path:

1. **[Getting Started Guide](getting-started.md)** - Set up your development environment
2. **[Contributing Guide](contributing.md)** - Learn the development workflow and standards
3. **[Testing Guide](testing.md)** - Understand how to write and run tests
4. **[Debugging Guide](debugging.md)** - Master development tools and troubleshooting

## Document Structure

### 📚 Core Development Guides

| Document | Purpose | Key Topics |
|----------|---------|------------|
| **[Getting Started](getting-started.md)** | Initial setup and orientation | Environment setup, repository structure, prerequisites |
| **[Contributing](contributing.md)** | Development workflow and contribution process | Git workflow, code quality, feature development, PR process |
| **[Testing](testing.md)** | Testing strategies and best practices | Unit/integration tests, mocking, coverage, performance testing |
| **[Debugging](debugging.md)** | Troubleshooting and development tools | ALS debugging, performance profiling, common issues |

### 🔧 Technical Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **[Test Suite Documentation](../../tests/README.md)** | Complete testing reference | `tests/README.md` |
| **[Development Tools](../../tools/README.md)** | Debugging utilities documentation | `tools/README.md` |
| **[API Documentation](../api/index.md)** | Code reference and examples | `docs/api/` |

### 📋 Project Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **[Software Requirements Specification](../SRS.md)** | Project requirements and specifications | `docs/SRS.md` |
| **[Software Design Document](../SDD.md)** | Architecture and design decisions | `docs/SDD.md` |
| **[Troubleshooting Guide](../TROUBLESHOOTING.md)** | User-facing issue resolution | `docs/TROUBLESHOOTING.md` |

## Development Workflow Summary

### Essential Commands

```bash
# Environment Setup
make dev                    # Install with dev dependencies
adafmt --version           # Verify installation

# Development Cycle
make test                  # Quick unit tests
make test-all             # Full test suite
make lint                 # Code linting
make typecheck            # Type checking
make format               # Code formatting

# Quality Assurance
make coverage             # Test coverage report
make check                # Run all checks
```

### Code Quality Standards

- **Testing**: Minimum 80% line coverage, comprehensive unit and integration tests
- **Linting**: Ruff for code quality and style enforcement
- **Type Checking**: MyPy for static type analysis
- **Formatting**: Black for consistent code formatting
- **Documentation**: Docstrings for all public APIs

## Architecture Overview

### Component Interaction

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     CLI     │────▶│  ALS Client │────▶│     ALS     │
│   (cli.py)  │     │(als_client) │     │  (subprocess│
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐     ┌─────────────┐
│     TUI     │     │    Edits    │
│  (tui.py)   │     │ (edits.py)  │
└─────────────┘     └─────────────┘
```

### Key Design Principles

- **Modularity**: Clear separation of concerns between components
- **Testability**: Easy to unit test with minimal external dependencies
- **Performance**: Efficient file processing and ALS communication
- **Reliability**: Robust error handling and recovery mechanisms
- **Extensibility**: Plugin architecture for future enhancements

## Testing Strategy

### Test Categories

- **Unit Tests**: Fast, isolated tests with mocking (`tests/unit/`)
- **Integration Tests**: End-to-end tests with real dependencies (`tests/integration/`)
- **Performance Tests**: Benchmarking and load testing
- **Mock Tests**: Testing without external dependencies

### Test Organization

```
tests/
├── unit/                   # Fast, isolated unit tests
├── integration/           # Slower, end-to-end tests
├── conftest.py           # Shared pytest fixtures
└── test_utils.py         # Utility function tests
```

## Development Tools

### ALS Debugging Suite

| Tool | Purpose | Use Case |
|------|---------|----------|
| `als_rpc_probe.py` | High-level ALS testing | Connectivity issues, timeout debugging |
| `als_rpc_probe_stdio.py` | Low-level protocol testing | Protocol debugging, message inspection |
| `harness_mocked.py` | Mock testing without ALS | File discovery testing, CI validation |

### IDE Configuration

**VS Code**: Python interpreter, pytest integration, Black formatting
**PyCharm**: Virtual environment setup, test runner configuration

## Common Development Tasks

### Adding New Features

1. **Design**: Review architecture and design principles
2. **Implement**: Follow coding standards and patterns
3. **Test**: Write comprehensive unit and integration tests  
4. **Document**: Update relevant documentation
5. **Review**: Submit PR following contribution guidelines

### Debugging Issues

1. **Reproduce**: Create minimal failing case
2. **Isolate**: Use debugging tools to narrow scope
3. **Analyze**: Check logs and use profiling tools
4. **Fix**: Implement solution with tests
5. **Verify**: Ensure fix doesn't break existing functionality

### Release Process

The project uses semantic versioning with conventional commits:
- `feat:` for new features
- `fix:` for bug fixes  
- `feat!:` for breaking changes

## Resource Quick Reference

### Documentation Links

- **Project Repository**: [GitHub](https://github.com/abitofhelp/adafmt)
- **Issue Tracker**: [GitHub Issues](https://github.com/abitofhelp/adafmt/issues)
- **Discussions**: [GitHub Discussions](https://github.com/abitofhelp/adafmt/discussions)

### Development Commands

```bash
# Setup
git clone https://github.com/abitofhelp/adafmt.git
cd adafmt && make dev

# Development
make test && make lint && make typecheck

# Debug ALS issues
python tools/als_rpc_probe.py --project-path project.gpr --verbose

# Full quality check
make test-all coverage lint typecheck format
```

### Environment Variables

```bash
# Development
export DEBUG=1
export PYTHONPATH=/path/to/adafmt/src

# ALS Configuration  
export ALS_HOME=/path/to/als
export GPR_PROJECT_PATH=/path/to/projects

# UI Debugging
export ADAFMT_UI_DEBUG=1
export ADAFMT_UI_FORCE=plain
```

## Next Steps

### For New Contributors

1. Read [Getting Started](getting-started.md) to set up your environment
2. Explore the codebase and run the test suite
3. Check out [good first issues](https://github.com/abitofhelp/adafmt/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
4. Review [Contributing Guide](contributing.md) before making changes

### For Experienced Developers

1. Review [architecture documentation](../SDD.md) for design context
2. Explore [API documentation](../api/index.md) for implementation details
3. Check [debugging tools](debugging.md) for development efficiency
4. Consider [enhancement opportunities](https://github.com/abitofhelp/adafmt/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

---

*This overview is maintained as the central hub for all developer resources. Please keep it updated as new documentation is added.*