# User Documentation

This section contains essential guides for adafmt end users, system administrators, and DevOps engineers.

## 📋 User Guides

### [🚀 Getting Started Guide](getting-started.md)
Step-by-step instructions for new users:
- Installation and setup verification
- First formatting commands with examples
- Common workflow patterns and flag combinations
- Environment-specific usage (development, CI/CD, large projects)
- Complete command reference with real examples
- Common mistakes and solutions

### [🔧 Troubleshooting Guide](troubleshooting.md)
Comprehensive solutions for common adafmt issues:
- Ada Language Server problems
- Timeout issues and resolution
- Formatting errors and syntax vs semantic errors
- File permission and discovery issues
- Performance optimization tips
- Environment-specific troubleshooting

### [⏱️ Timeout Configuration Guide](timeout-guide.md)
Complete guide to ALS timeout management:
- Configurable timeout parameters
- Consecutive timeout protection
- Environment-specific tuning guidelines
- Performance monitoring and diagnostics
- Troubleshooting timeout issues
- Best practices for different scenarios

### [⚙️ Configuration Reference](configuration.md) *(Coming Soon)*
Complete reference for all adafmt configuration options:
- Command-line arguments
- Environment variables
- Configuration files
- Project-specific settings

## 🎯 Quick Navigation

### Common Tasks
- **Fixing ALS Issues**: [Troubleshooting → ALS Issues](troubleshooting.md#1-ada-language-server-issues)
- **Resolving Timeouts**: [Timeout Guide → Common Scenarios](timeout-guide.md#usage-examples)
- **Performance Tuning**: [Timeout Guide → Tuning Guidelines](timeout-guide.md#timeout-tuning-guidelines)
- **CI/CD Integration**: [Timeout Guide → CI/CD Examples](timeout-guide.md#usage-examples)

### By User Type

#### **System Administrators**
- [ALS Installation Issues](troubleshooting.md#ada-language-server-not-found)
- [Process Management](troubleshooting.md#existing-als-processes-detected)  
- [Timeout Configuration for Systems](timeout-guide.md#environment-specific-solutions)

#### **DevOps Engineers**
- [CI/CD Timeout Settings](timeout-guide.md#aggressive-timeout-for-cicd)
- [Automated Troubleshooting](troubleshooting.md#quick-timeout-resolution-workflow)
- [Performance Monitoring](timeout-guide.md#monitoring-and-diagnostics)

#### **End Users**
- [Getting Started Guide](getting-started.md) - **Start here if you're new to adafmt**
- [Basic Troubleshooting](troubleshooting.md#common-issues-and-solutions)
- [Understanding Error Messages](troubleshooting.md#syntax-errors-vs-semantic-errors)
- [Configuration Options](configuration.md)

## 🔗 Related Documentation

- **[API Reference](../api/index.md)** - Technical implementation details
- **[Developer Guide](../developer/index.md)** - Contributing and development
- **[Formal Documentation](../formal/index.md)** - Requirements and design specifications

## 💡 Getting Help

If you can't find what you're looking for:

1. **Check the [Troubleshooting Guide](troubleshooting.md)** first
2. **Search the [GitHub Issues](https://github.com/abitofhelp/adafmt/issues)**
3. **Create a new issue** with:
   - Your adafmt version (`adafmt --version`)
   - Your operating system
   - Complete error messages
   - Steps to reproduce the issue

---

*User documentation is kept up-to-date with each release. For technical implementation details, see the [Developer Documentation](../developer/index.md).*