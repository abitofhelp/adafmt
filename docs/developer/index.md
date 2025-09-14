# Developer Documentation

This section contains comprehensive resources for adafmt contributors, maintainers, and integration developers. Whether you're making your first contribution or building advanced integrations, you'll find what you need here.

## 🚀 Getting Started

### [📖 Getting Started Guide](getting-started.md)
Essential setup for adafmt development:
- Development environment setup (Python 3.11+)
- Repository cloning and virtual environment creation
- Development dependencies installation
- IDE configuration (VS Code, PyCharm)
- First build and test run verification

### [🤝 Contributing Guide](contributing.md)
Everything you need to know about contributing:
- Contribution workflow and branch management
- Code standards and style guidelines
- Pull request process and review criteria
- Commit message conventions (semantic versioning)
- Issue reporting and feature request process

## 🧪 Development Resources

### [🧪 Testing Guide](testing.md)
Comprehensive testing documentation:
- Test suite organization (unit vs integration)
- Writing effective tests with pytest
- Test fixtures and mocking strategies
- Coverage requirements and reporting
- Continuous integration testing
- Performance and benchmark testing

### [🔍 Debugging Guide](debugging.md)
Tools and techniques for debugging adafmt:
- Development debugging tools (`tools/` directory)
- ALS communication debugging
- Protocol-level troubleshooting
- Performance profiling and optimization
- Common debugging scenarios and solutions

## 🏗️ Architecture & Design

### Architecture Documentation
- **[API Reference](../api/index.md)**: Complete technical API documentation
- **[Formal Design](../formal/SDD.md)**: Official software design document
- **[Architecture Overview](../formal/architecture.md)**: High-level system design *(coming soon)*

### Key Design Concepts
- **Modular Architecture**: Clean separation of concerns between components
- **Async Communication**: Non-blocking ALS interaction using asyncio
- **Robust Error Handling**: Comprehensive timeout and retry mechanisms  
- **Multiple UI Modes**: Flexible user interface for different contexts
- **Extensible Design**: Plugin architecture for custom formatting rules

## 📋 Development Workflow

### Standard Development Process
1. **Setup**: Follow [Getting Started Guide](getting-started.md)
2. **Issue**: Create or assign GitHub issue for work
3. **Branch**: Create feature branch from main
4. **Develop**: Implement changes with tests
5. **Quality**: Run linting, testing, and type checking
6. **PR**: Submit pull request following [Contributing Guide](contributing.md)
7. **Review**: Address code review feedback
8. **Merge**: Maintainer merges approved PR

### Quality Assurance Checklist
- ✅ All tests pass (`make test-all`)
- ✅ Code is formatted (`make format`)
- ✅ No lint issues (`make lint`)
- ✅ Type checking passes (`make typecheck`)
- ✅ Documentation updated for API changes
- ✅ Commit messages follow conventional format

## 🛠️ Development Tools

### Make Targets
```bash
# Development setup
make dev          # Install with dev dependencies
make install      # Basic installation

# Code quality
make lint         # Run ruff linting
make format       # Format with black
make typecheck    # Run mypy type checking

# Testing
make test         # Unit tests only (fast)
make test-all     # All tests including integration
make coverage     # Test coverage report

# Ada formatting (requires project.gpr)
make ada-format   # Dry-run format
make ada-write    # Format and write files
make ada-check    # Check if formatting needed

# Distribution
make build        # Build packages
make dist-all     # All distribution formats
```

### Debugging Tools
- **`tools/als_rpc_probe.py`**: High-level ALS testing
- **`tools/als_rpc_probe_stdio.py`**: Low-level LSP protocol testing  
- **`tools/harness_mocked.py`**: Mock testing without ALS
- **Development logging**: JSONL structured logs for debugging

## 🎯 Developer Paths

### **New Contributors**
1. **Start**: [Getting Started Guide](getting-started.md)
2. **Learn**: [Testing Guide](testing.md) - understand the codebase through tests
3. **Practice**: Pick up "good first issue" from GitHub
4. **Contribute**: Follow [Contributing Guide](contributing.md)

### **Regular Contributors**  
1. **Efficiency**: Master the Make targets and development workflow
2. **Quality**: Deep dive into [Testing Guide](testing.md) for advanced patterns
3. **Debug**: Use [Debugging Guide](debugging.md) for complex issues
4. **Design**: Reference [API Documentation](../api/index.md) for architectural decisions

### **Maintainers**
1. **Architecture**: Review [Formal Documentation](../formal/index.md) for design decisions
2. **Process**: Ensure [Contributing Guide](contributing.md) standards are maintained  
3. **Quality**: Monitor test coverage and performance metrics
4. **Community**: Guide new contributors and review complex PRs

### **Integration Developers**
1. **API**: Deep dive into [API Reference](../api/index.md) 
2. **Protocols**: Study [Technical Reference](../reference/index.md) for LSP details
3. **Examples**: Reference existing integrations and tools
4. **Testing**: Create comprehensive integration tests

## 📚 Learning Resources

### **Understanding adafmt**
- **[User Documentation](../user/index.md)**: Understand the user experience
- **[API Reference](../api/index.md)**: Technical implementation details
- **[Formal Requirements](../formal/SRS.md)**: What the system should do

### **Ada Language Server**
- **[ALS Repository](https://github.com/AdaCore/ada_language_server)**: Backend implementation
- **[LSP Specification](https://microsoft.github.io/language-server-protocol/)**: Protocol details
- **[Timeout Guide](../user/timeout-guide.md)**: ALS-specific tuning and troubleshooting

### **Python Development**
- **asyncio**: For understanding ALS client communication
- **pytest**: For writing effective tests
- **Typer**: For CLI development patterns
- **Language Server Protocol**: For protocol-level debugging

## 🔗 Quick References

### **File Organization**
- **`src/adafmt/`**: Main package source code
- **`tests/`**: Comprehensive test suite with fixtures
- **`tools/`**: Development and debugging utilities
- **`docs/`**: Documentation (you are here!)

### **Key Configuration Files**
- **`pyproject.toml`**: Project metadata and build configuration
- **`Makefile`**: Development shortcuts and automation
- **`tests/conftest.py`**: Shared pytest fixtures

### **External Dependencies**
- **Required**: Python 3.11+, Typer
- **Development**: pytest, black, ruff, mypy
- **Runtime**: Ada Language Server (for actual formatting)

---

*Developer documentation evolves with the codebase. Contributions to improve these guides are always welcome! See [Contributing Guide](contributing.md) for how to help.*