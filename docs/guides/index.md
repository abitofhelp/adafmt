# Developer Resources

**Version:** 1.0.1
**Date:** 2025-09-20T00:23:54.445021Z
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

Welcome to the comprehensive developer documentation for adafmt! This serves as your central hub for all development resources, whether you're making your first contribution, building integrations, or maintaining the project.

## Quick Start Path

For new developers, follow this recommended path:

1. **[Getting Started Guide](getting-started-guide.md)** - Complete usage guide and development setup
2. **[Contributing Guide](contributing-guide.md)** - Learn the development workflow and standards
3. **[Testing Guide](testing-guide.md)** - Understand how to write and run tests
4. **[Troubleshooting Guide](troubleshooting-guide.md)** - Master debugging and issue resolution

## 🚀 Core Guides

### [📖 Getting Started Guide](getting-started-guide.md)
Comprehensive guide covering:
- **User Guide**: Installation, usage patterns, workflows, CI/CD integration
- **Development Setup**: Environment setup, repository structure, first build
- **Prerequisites**: Python 3.11+, ALS installation, project requirements
- **Examples**: Real command combinations and common scenarios

### [🤝 Contributing Guide](contributing-guide.md)
Everything you need to know about contributing:
- Development workflow and branch management
- Code quality standards and style guidelines
- Pull request process and review criteria
- Commit message conventions (semantic versioning)
- Issue reporting and feature request process

## 🧪 Testing & Quality

### [🧪 Testing Guide](testing-guide.md)
Comprehensive testing documentation:
- Test suite organization (unit vs integration)
- Writing effective tests with pytest
- Test fixtures and mocking strategies
- Coverage requirements and reporting
- Continuous integration testing
- Performance and benchmark testing

### [🔧 Troubleshooting Guide](troubleshooting-guide.md)
Comprehensive issue resolution guide:
- **Common Issues**: ALS problems, timeout errors, file formatting issues
- **Environment-Specific**: macOS, Windows, Linux, Docker, CI/CD
- **Debugging Tools**: ALS probes, protocol analysis, logging
- **Performance**: Profiling, optimization, large project handling
- **Getting Help**: Issue reporting, diagnostic collection

## 🔧 Configuration & Tuning

### [⚙️ Configuration Guide](configuration-guide.md)
Complete configuration reference:
- **Command-Line Options**: All flags and parameters
- **Environment Variables**: ALS, development, UI configuration
- **ALS Traces**: Debugging and performance analysis
- **Configuration Patterns**: Development, CI/CD, large projects
- **Best Practices**: Security, performance, troubleshooting

### [📊 Output Format Guide](output-format-guide.md)
Complete guide to understanding adafmt's output:
- **ALS Metrics**: File processing statistics and performance
- **Pattern Metrics**: Custom pattern application results
- **Run Summary**: Overall execution timing and results
- **Log Files**: Understanding and using generated logs
- **Troubleshooting**: Interpreting results for debugging

### [⏱️ Timeout Configuration Guide](timeout-guide.md)
Comprehensive guide to timeout configuration and tuning:
- Understanding adafmt's timeout mechanisms
- Default timeout values and their purposes
- Tuning timeouts for different environments
- Advanced timeout strategies for large projects
- Troubleshooting timeout-related issues

### [🎨 Pattern Formatter Guide](patterns-guide.md)
Complete guide to the pattern formatter system:
- **Usage**: Quick start, configuration, validation
- **Development**: Architecture, API, implementation
- **Extensibility**: Creating custom patterns
- **Testing**: Unit and integration testing
- **Performance**: Optimization and benchmarking
- **Troubleshooting**: Common issues and solutions

## 🏗️ Architecture & Design

### Component Architecture

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

### Architecture Documentation
- **[API Reference](../api/index.md)**: Complete technical API documentation
- **[Formal Design](../formal/SDD.md)**: Official software design document
- **[Requirements](../formal/SRS.md)**: Software requirements specification

## 🛠️ Development Environment

### Repository Structure

```
adafmt/
├── src/
│   └── adafmt/              # Main package
│       ├── cli.py           # CLI entry point (Typer-based)
│       ├── als_client.py    # ALS communication
│       ├── tui.py           # Terminal UI components
│       ├── file_discovery.py # File finding and filtering
│       ├── edits.py         # Text editing operations
│       └── utils.py         # Utility functions
├── tests/                   # Comprehensive test suite
│   ├── unit/               # Fast, isolated unit tests
│   ├── integration/        # End-to-end integration tests
│   └── conftest.py         # Shared pytest fixtures
├── tools/                  # Development and debugging tools
├── docs/                   # Documentation (you are here!)
└── Makefile               # Development shortcuts
```

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

## 🔍 Debugging & Analysis

### ALS Debugging Suite

| Tool | Purpose | Use Case |
|------|---------|----------|
| `als_rpc_probe.py` | High-level ALS testing | Connectivity issues, timeout debugging |
| `als_rpc_probe_stdio.py` | Low-level protocol testing | Protocol debugging, message inspection |
| `harness_mocked.py` | Mock testing without ALS | File discovery testing, CI validation |

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

## 🎯 Learning Paths

### **New Contributors**
1. **Start**: [Getting Started Guide](getting-started-guide.md) - setup and basic usage
2. **Learn**: [Testing Guide](testing-guide.md) - understand the codebase through tests
3. **Practice**: Pick up "good first issue" from GitHub
4. **Contribute**: Follow [Contributing Guide](contributing-guide.md)

### **Regular Contributors**
1. **Efficiency**: Master the Make targets and development workflow
2. **Quality**: Deep dive into [Testing Guide](testing-guide.md) for advanced patterns
3. **Debug**: Use [Troubleshooting Guide](troubleshooting-guide.md) for complex issues
4. **Design**: Reference [API Documentation](../api/index.md) for architectural decisions

### **Maintainers**
1. **Architecture**: Review [Formal Documentation](../formal/index.md) for design decisions
2. **Process**: Ensure [Contributing Guide](contributing-guide.md) standards are maintained
3. **Quality**: Monitor test coverage and performance metrics
4. **Community**: Guide new contributors and review complex PRs

### **Integration Developers**
1. **API**: Deep dive into [API Reference](../api/index.md)
2. **Configuration**: Study [Configuration Guide](configuration-guide.md) for integration options
3. **Examples**: Reference existing integrations and tools
4. **Testing**: Create comprehensive integration tests

## 📚 External Resources

### **Understanding adafmt**
- **[Getting Started](getting-started-guide.md)**: Complete usage and development guide
- **[API Reference](../api/index.md)**: Technical implementation details
- **[Formal Requirements](../formal/SRS.md)**: What the system should do

### **Ada Language Server**
- **[ALS Repository](https://github.com/AdaCore/ada_language_server)**: Backend implementation
- **[LSP Specification](https://microsoft.github.io/language-server-protocol/)**: Protocol details
- **[Timeout Guide](timeout-guide.md)**: ALS-specific tuning and troubleshooting

### **Python Development**
- **asyncio**: For understanding ALS client communication
- **pytest**: For writing effective tests
- **Typer**: For CLI development patterns
- **Language Server Protocol**: For protocol-level debugging

## 🔗 Quick Reference

### **Resource Links**

- **Project Repository**: [GitHub](https://github.com/abitofhelp/adafmt)
- **Issue Tracker**: [GitHub Issues](https://github.com/abitofhelp/adafmt/issues)
- **Discussions**: [GitHub Discussions](https://github.com/abitofhelp/adafmt/discussions)

### **Environment Variables**

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

### **Next Steps**

#### For New Contributors
1. Read [Getting Started](getting-started-guide.md) to set up your environment
2. Explore the codebase and run the test suite
3. Check out [good first issues](https://github.com/abitofhelp/adafmt/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
4. Review [Contributing Guide](contributing-guide.md) before making changes

#### For Experienced Developers
1. Review [architecture documentation](../formal/SDD.md) for design context
2. Explore [API documentation](../api/index.md) for implementation details
3. Check [troubleshooting guide](troubleshooting-guide.md) for debugging efficiency
4. Consider [enhancement opportunities](https://github.com/abitofhelp/adafmt/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

---

*This documentation hub is maintained as the central resource for all developer needs. Please keep it updated as new documentation is added.*
