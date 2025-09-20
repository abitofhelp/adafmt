# Pattern Formatter Guide

**Version:** 1.0.1
**Date:** 2025-09-20T00:34:23.357320Z
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

This comprehensive guide covers everything about adafmt's pattern formatter system - from basic usage to advanced development and extensibility.

---

## Table of Contents

### Usage
1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Using Patterns](#3-using-patterns)
4. [Pattern File Format](#4-pattern-file-format)
5. [Command-Line Options](#5-command-line-options)
6. [Validating Patterns](#6-validating-patterns)
7. [Common Use Cases](#7-common-use-cases)

### Development
8. [Architecture Overview](#8-architecture-overview)
9. [Implementation Details](#9-implementation-details)
10. [API Reference](#10-api-reference)
11. [Testing Patterns](#11-testing-patterns)
12. [Performance Considerations](#12-performance-considerations)

### Extensibility
13. [Creating Custom Patterns](#13-creating-custom-patterns)
14. [Pattern Categories and Best Practices](#14-pattern-categories-and-best-practices)
15. [Advanced Pattern Features](#15-advanced-pattern-features)
16. [Contributing Patterns](#16-contributing-patterns)

### Reference
17. [Troubleshooting](#17-troubleshooting)
18. [Examples](#18-examples)

---

## 1. Overview

The pattern formatter is a post-processing stage that runs after the Ada Language Server (ALS) formats your code. It applies additional formatting rules using regular expressions to ensure consistent style across your codebase.

### Key Features

- **Sequential Processing**: Patterns are applied in alphabetical order by name
- **Safety**: Only runs on syntactically valid Ada code (after ALS succeeds)
- **Performance**: Built-in timeout protection prevents hanging on complex patterns
- **Logging**: Detailed pattern activity log for debugging and auditing
- **Validation**: Test patterns to ensure they don't conflict with ALS formatting

### Architecture

```
File Discovery → ALS Formatting → Pattern Formatter → File Write
                                         ↓
                                  Pattern Log (JSONL)
```

## 2. Quick Start

### Step 1: Create a Patterns File

Create `adafmt_patterns.json` in your project root:

```json
[
  {
    "name": "comment-norm",
    "title": "Normalize comment spacing",
    "category": "comment",
    "find": " -- ",
    "replace": " --  "
  }
]
```

### Step 2: Run adafmt

Patterns are applied automatically:

```bash
adafmt --project-path project.gpr
```

### Step 3: Check the Pattern Log

See what was applied:

```bash
cat adafmt_*_patterns.log | jq .
```

## 3. Using Patterns

### Default Behavior

By default, adafmt looks for `./adafmt_patterns.json` in the current directory. If found, patterns are loaded and applied after ALS formatting.

### Specifying a Pattern File

Use the `--patterns-path` option to specify a different pattern file:

```bash
adafmt --project-path project.gpr --patterns-path my_patterns.json
```

### Disabling Patterns

To disable pattern processing entirely:

```bash
adafmt --project-path project.gpr --no-patterns
```

### Pattern Timeout Configuration

Control pattern execution timeout with `--patterns-timeout-ms`:

```bash
# Set 200ms timeout per pattern (default: 100ms)
adafmt --project-path project.gpr --patterns-timeout-ms 200
```

### File Size Limits

Skip patterns for large files with `--patterns-max-bytes`:

```bash
# Skip patterns for files larger than 1MB (default: 10MB)
adafmt --project-path project.gpr --patterns-max-bytes 1048576
```

## 4. Pattern File Format

Patterns are defined in a JSON array. Each pattern must have:

### Required Fields

- **name**: Exactly 12 characters, using only `[a-z0-9_-]`
- **title**: Human-readable description (1-80 characters)
- **category**: One of: `comment`, `operator`, `delimiter`, `declaration`, `attribute`, `hygiene`
- **find**: Regular expression pattern to match
- **replace**: Replacement text

### Optional Fields

- **flags**: Array of regex flags: `["MULTILINE"]`, `["IGNORECASE"]`, `["DOTALL"]`
- **timeout**: Timeout in seconds for this pattern (default: 1.0)
- **comment**: Additional notes about the pattern

### Schema Validation

Pattern names must:
- Be exactly 12 characters long
- Use only lowercase letters, numbers, hyphens, and underscores
- Be unique within the pattern file

### Example Pattern File

```json
[
  {
    "name": "comment-norm",
    "title": "Normalize comment spacing",
    "category": "comment",
    "find": " -- ",
    "replace": " --  "
  },
  {
    "name": "operator-add",
    "title": "Space around addition operator",
    "category": "operator",
    "find": "(?<![\\w)])\\+(?![\\w(])",
    "replace": " + "
  },
  {
    "name": "hygiene-eol",
    "title": "Remove trailing whitespace",
    "category": "hygiene",
    "find": "[ \\t]+$",
    "replace": "",
    "flags": ["MULTILINE"]
  }
]
```

## 5. Command-Line Options

### Pattern-Related Options

```bash
--patterns-path PATH         # Pattern file location (default: ./adafmt_patterns.json)
--no-patterns               # Disable pattern processing
--patterns-timeout-ms MS    # Timeout per pattern in milliseconds (default: 100)
--patterns-max-bytes BYTES  # Skip patterns for files larger than this (default: 10MB)
--validate-patterns         # Validate patterns don't break ALS formatting
```

### Examples

```bash
# Use custom patterns with extended timeout
adafmt --project-path project.gpr \
       --patterns-path style/ada_patterns.json \
       --patterns-timeout-ms 100

# Validate patterns before committing
adafmt --project-path project.gpr \
       --validate-patterns \
       --patterns-path new_patterns.json

# Format without patterns (ALS only)
adafmt --project-path project.gpr --no-patterns
```

## 6. Validating Patterns

Before adding new patterns to your project, validate them to ensure they don't conflict with ALS formatting:

```bash
adafmt --project-path project.gpr --validate-patterns
```

This will:
1. Apply your patterns to each file
2. Run the result through ALS again
3. Report any files where ALS wants to make additional changes
4. Exit with code 1 if conflicts are found

### Example Validation Output

```
[validate] Starting pattern validation...
[   1/10] [  OK  ] src/main.adb
[   2/10] [ERROR] src/utils.adb - patterns conflict with ALS
[   3/10] [  OK  ] src/types.ads
...
[validate] Found 1 pattern conflicts:
  - src/utils.adb: Patterns break ALS formatting (ALS wants 3 edits)
```

## 7. Common Use Cases

### Enforcing Comment Style

```json
{
  "name": "comment-norm",
  "title": "Normalize comment spacing",
  "category": "comment",
  "find": " -- ",
  "replace": " --  "
}
```

### Standardizing Operator Spacing

```json
{
  "name": "operator-asg",
  "title": "Space around assignment",
  "category": "operator",
  "find": ":=",
  "replace": " := "
}
```

### Removing Trailing Whitespace

```json
{
  "name": "hygiene-eol",
  "title": "Remove trailing whitespace",
  "category": "hygiene",
  "find": "[ \\t]+$",
  "replace": "",
  "flags": ["MULTILINE"]
}
```

### Fixing TODO Comments

```json
{
  "name": "comment-todo",
  "title": "Standardize TODO format",
  "category": "comment",
  "find": "--\\s*todo:?",
  "replace": "-- TODO:",
  "flags": ["IGNORECASE"]
}
```

## 8. Architecture Overview

The pattern formatter is implemented as a post-processing stage that runs after successful ALS formatting:

### Key Components

1. **PatternFormatter** (`src/adafmt/pattern_formatter.py`)
   - Loads and validates patterns from JSON
   - Manages pattern compilation and caching
   - Applies patterns sequentially with timeout protection

2. **PatternLogger** (`src/adafmt/pattern_formatter.py`)
   - Adapter for JsonlLogger
   - Logs pattern activity to dedicated log file
   - Tracks metrics per pattern

3. **Pattern Validation** (`--validate-patterns` flag)
   - Verifies patterns don't conflict with ALS
   - Runs pattern output through ALS again
   - Reports any formatting conflicts

### Processing Flow

```python
# 1. Pattern Loading (startup)
patterns = PatternFormatter.load_from_json(path)

# 2. Pattern Application (per file)
if als_success:
    text, stats = patterns.apply(file_path, formatted_text)

# 3. Pattern Logging
logger.log_file_patterns(file_path, stats)

# 4. Pattern Summary (shutdown)
summary = patterns.get_summary()
logger.log_run_end(summary)
```

## 9. Implementation Details

### Pattern Structure

```python
@dataclass
class CompiledRule:
    """A compiled pattern rule ready for application."""
    name: str           # 12-character identifier
    title: str          # Human-readable description
    category: str       # Classification
    find: Pattern       # Compiled regex pattern
    replace: str        # Replacement string
    flags: int          # Regex flags
    timeout: float      # Timeout in seconds
```

### Pattern Loading

Patterns are loaded once at startup and compiled into an immutable structure:

```python
@classmethod
def load_from_json(cls, path: Path, logger=None, ui=None) -> 'PatternFormatter':
    """Load patterns from JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)

        # Validate and compile each rule
        compiled_rules = []
        for rule in rules_data:
            if cls._validate_rule(rule):
                compiled = cls._compile_rule(rule)
                compiled_rules.append(compiled)

        return cls(tuple(compiled_rules))
    except Exception as e:
        # Log error and return disabled formatter
        return cls(())
```

### Pattern Application

Patterns are applied sequentially with timeout protection:

```python
def apply(self, path: Path, text: str, timeout_ms: int = 100,
          logger=None, ui=None) -> Tuple[str, FileApplyResult]:
    """Apply all patterns to text."""
    result = text
    metrics = FileApplyResult()

    for rule in self.rules:
        try:
            with timeout_context(timeout_ms / 1000):
                new_result, count = rule.find.subn(
                    rule.replace, result
                )
                if count > 0:
                    result = new_result
                    metrics.record_application(rule.name, count)
        except TimeoutError:
            # Log timeout and continue
            logger.log({'ev': 'pattern_timeout', 'name': rule.name})

    return result, metrics
```

## 10. API Reference

### PatternFormatter Class

```python
class PatternFormatter:
    """Manages pattern-based text transformations."""

    def __init__(self, rules: Tuple[CompiledRule, ...]):
        """Initialize with compiled rules."""

    @classmethod
    def load_from_json(cls, path: Path, logger=None, ui=None) -> 'PatternFormatter':
        """Load patterns from JSON file."""

    def apply(self, path: Path, text: str, timeout_ms: int = 50,
              logger=None, ui=None) -> Tuple[str, FileApplyResult]:
        """Apply all patterns to text."""

    def get_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary statistics for all patterns."""

    @property
    def enabled(self) -> bool:
        """Check if formatter has patterns and is enabled."""

    @property
    def loaded_count(self) -> int:
        """Number of loaded patterns."""
```

### FileApplyResult Class

```python
@dataclass
class FileApplyResult:
    """Results from applying patterns to a single file."""
    applied_names: List[str]     # Patterns that made changes
    replacements_sum: int        # Total replacements

    def record_application(self, name: str, count: int):
        """Record that a pattern was applied."""
```

## 11. Testing Patterns

### Unit Testing

Test individual patterns in isolation:

```python
def test_comment_normalization():
    """Test comment spacing normalization."""
    patterns = [
        {
            "name": "comment-norm",
            "title": "Normalize comment spacing",
            "category": "comment",
            "find": " -- ",
            "replace": " --  "
        }
    ]

    formatter = PatternFormatter.load_from_test_data(patterns)
    result, stats = formatter.apply(
        Path("test.adb"),
        "X : Integer; -- Comment"
    )

    assert result == "X : Integer; --  Comment"
    assert stats.replacements_sum == 1
    assert "comment-norm" in stats.applied_names
```

### Integration Testing

Test patterns with actual ALS formatting:

```python
@pytest.mark.integration
def test_patterns_with_als(temp_project):
    """Test patterns don't conflict with ALS."""
    # Create test file
    test_file = temp_project / "test.adb"
    test_file.write_text("procedure Test is begin null; end Test;")

    # Run adafmt with patterns
    result = subprocess.run(
        ["adafmt", "--project-path", str(temp_project / "test.gpr"),
         "--patterns-path", "patterns.json"],
        capture_output=True
    )

    assert result.returncode == 0
```

### Pattern Validation Testing

```python
def test_validate_patterns_flag(temp_project):
    """Test --validate-patterns functionality."""
    # Create patterns that conflict with ALS
    patterns = [{
        "name": "bad-spacing1",
        "title": "Remove assignment spacing",
        "category": "operator",
        "find": " := ",
        "replace": ":="  # ALS will add spaces back
    }]

    # Run validation
    result = run_adafmt(["--validate-patterns", "--patterns-path", "bad.json"])

    assert result.returncode == 1
    assert "patterns conflict with ALS" in result.stdout
```

## 12. Performance Considerations

### Regex Module

The pattern formatter prefers the third-party `regex` module over Python's built-in `re` module for timeout support:

```python
try:
    import regex
    HAS_REGEX = True
except ImportError:
    import re as regex
    HAS_REGEX = False
```

### Timeout Protection

Each pattern application is protected by a timeout (default 100ms):

```python
# With regex module
pattern.sub(replacement, text, timeout=0.05)

# Without regex module (uses signal-based timeout)
with timeout_context(0.05):
    pattern.sub(replacement, text)
```

### Performance Tips

1. **Avoid catastrophic backtracking**: Use specific patterns
2. **Limit pattern count**: Each pattern adds overhead
3. **Be specific**: Narrow patterns are faster than broad ones
4. **Test performance**: Monitor pattern execution time in logs

### Benchmarking

```bash
# Extract pattern performance data
cat adafmt_*_patterns.log | \
  jq -r 'select(.ev == "pattern_applied") |
         "\(.name): \(.elapsed_ms)ms on \(.path)"' | \
  sort -k2 -nr | head -20
```

## 13. Creating Custom Patterns

### Pattern Design Process

1. **Identify the formatting issue** - What needs to be standardized?
2. **Write the regex pattern** - Match the current format
3. **Define the replacement** - Specify the desired format
4. **Choose a category** - Classify the pattern appropriately
5. **Test thoroughly** - Ensure no unintended matches

### Pattern Naming Convention

Pattern names must be exactly 12 characters:

```
comment-norm    ✓ Valid (12 chars)
op-space        ✗ Invalid (8 chars)
operator-spacing ✗ Invalid (16 chars)
```

Suggested naming patterns:
- `comment-xxxx` - Comment formatting
- `operator-xxx` - Operator spacing
- `hygiene-xxxx` - Code cleanliness
- `delimit-xxxx` - Delimiter formatting

### Testing Custom Patterns

1. Create a test file with examples:
```ada
-- test_patterns.adb
procedure Test is
   X : Integer; -- Test comment
   Y : Integer:=5;  -- Should have spaces
begin
   null;
end Test;
```

2. Run with your pattern file:
```bash
adafmt --project-path test.gpr --patterns-path custom_patterns.json
```

3. Validate against ALS:
```bash
adafmt --project-path test.gpr --validate-patterns
```

## 14. Pattern Categories and Best Practices

### Comment Patterns

Standardize comment formatting:

```json
{
  "name": "comment-norm",
  "title": "Normalize comment spacing",
  "category": "comment",
  "find": " -- ",
  "replace": " --  "
}
```

Best practices:
- Preserve comment content
- Focus on spacing and alignment
- Be careful with multi-line comments

### Operator Patterns

Ensure consistent spacing around operators:

```json
{
  "name": "operator-add",
  "title": "Space around plus",
  "category": "operator",
  "find": "(?<![\\w)])\\+(?![\\w(])",
  "replace": " + "
}
```

Best practices:
- Use lookahead/lookbehind to avoid false matches
- Consider operator precedence
- Test with complex expressions

### Hygiene Patterns

General code cleanliness:

```json
{
  "name": "hygiene-eol",
  "title": "Remove trailing whitespace",
  "category": "hygiene",
  "find": "[ \\t]+$",
  "replace": "",
  "flags": ["MULTILINE"]
}
```

Best practices:
- Use MULTILINE flag for line-based patterns
- Be conservative with deletions
- Consider impact on diffs

### Delimiter Patterns

Standardize punctuation:

```json
{
  "name": "delimit-comma",
  "title": "Space after comma",
  "category": "delimiter",
  "find": ",(?! )",
  "replace": ", "
}
```

Best practices:
- Handle edge cases (end of line, strings)
- Consider context (generic parameters vs lists)
- Preserve semantic meaning

## 15. Advanced Pattern Features

### Using Regex Flags

Control pattern matching behavior:

```json
{
  "name": "comment-todo",
  "title": "Standardize TODO format",
  "category": "comment",
  "find": "--\\s*todo:?",
  "replace": "-- TODO:",
  "flags": ["IGNORECASE", "MULTILINE"]
}
```

Available flags:
- `IGNORECASE` - Case-insensitive matching
- `MULTILINE` - ^ and $ match line boundaries
- `DOTALL` - . matches newlines

### Capture Groups

Use capture groups for complex replacements:

```json
{
  "name": "comment-sect",
  "title": "Format section comments",
  "category": "comment",
  "find": "--\\s*=+\\s*(\\w+)\\s*=+",
  "replace": "-- ===== \\1 ====="
}
```

### Custom Timeouts

Override default timeout for complex patterns:

```json
{
  "name": "complex-pat1",
  "title": "Complex pattern needing more time",
  "category": "hygiene",
  "find": "very complex regex here",
  "replace": "replacement",
  "timeout": 0.2
}
```

### Pattern Dependencies

While patterns are independent, order matters:

```json
[
  {
    "name": "operator-001",  // Runs first
    "find": ":=",
    "replace": " := "
  },
  {
    "name": "operator-002",  // Runs second
    "find": " :=  ",        // Won't match if first pattern ran
    "replace": " := "
  }
]
```

## 16. Contributing Patterns

### Adding Default Patterns

1. Edit `adafmt_patterns.json` in the project root
2. Follow the naming convention and categories
3. Add comprehensive tests
4. Update documentation

### Submission Process

1. Create a pull request with:
   - Pattern definition in JSON
   - Unit tests for the pattern
   - Integration test with ALS
   - Documentation updates

2. Include rationale:
   - Why is this pattern needed?
   - What problem does it solve?
   - Are there any edge cases?

### Pattern Quality Guidelines

- **Specific**: Target precise formatting issues
- **Safe**: Don't break valid Ada code
- **Tested**: Include comprehensive test cases
- **Documented**: Clear description and examples
- **Compatible**: Validate against ALS

### Versioning

Pattern changes follow semantic versioning:

1. Adding patterns: Minor version bump
2. Breaking changes need:
   - Major version bump
   - Migration guide
   - Deprecation period

## 17. Troubleshooting

### Patterns Not Being Applied

1. **Check pattern file exists**:
   ```bash
   ls -la adafmt_patterns.json
   ```

2. **Verify JSON syntax**:
   ```bash
   jq . adafmt_patterns.json
   ```

3. **Check pattern log**:
   ```bash
   cat adafmt_*_patterns.log | jq '.ev'
   ```

4. **Look for errors**:
   ```bash
   cat adafmt_*_patterns.log | jq 'select(.ev == "load_error")'
   ```

### Pattern Timeout Issues

If patterns are timing out:

1. **Check for catastrophic backtracking**:
   - Avoid patterns like `(a+)+b`
   - Use more specific patterns

2. **Increase timeout**:
   ```bash
   adafmt --patterns-timeout-ms 200
   ```

3. **Install regex module** for better performance:
   ```bash
   pip install regex
   ```

### Patterns Breaking ALS Formatting

Use `--validate-patterns` to identify problematic patterns:

```bash
adafmt --validate-patterns --patterns-path patterns.json
```

Common issues:
- Removing spaces that ALS requires
- Changing operator precedence formatting
- Breaking indentation rules

### Performance Issues

For large codebases:

1. **Limit file size** for pattern processing:
   ```bash
   adafmt --patterns-max-bytes 1048576  # 1MB limit
   ```

2. **Use specific patterns** instead of broad ones

3. **Monitor pattern performance**:
   ```bash
   cat adafmt_*_patterns.log | \
     jq -r 'select(.ev == "pattern_applied") |
            "\(.name): \(.elapsed_ms)ms"' | \
     sort -k2 -nr
   ```

## 18. Examples

### Comment Normalization

```json
{
  "name": "comment-norm",
  "title": "Two spaces after --",
  "category": "comment",
  "find": " -- ",
  "replace": " --  "
}
```

### Operator Spacing

```json
{
  "name": "operator-asg",
  "title": "Assignment spacing",
  "category": "operator",
  "find": ":=",
  "replace": " := "
}
```

### Trailing Whitespace Removal

```json
{
  "name": "hygiene-eol",
  "title": "Remove trailing whitespace",
  "category": "hygiene",
  "find": "[ \\t]+$",
  "replace": "",
  "flags": ["MULTILINE"]
}
```

### Attribute Formatting

```json
{
  "name": "attr-nospace",
  "title": "No space before attributes",
  "category": "attribute",
  "find": "\\s+'([A-Z]\\w*)",
  "replace": "'\\1"
}
```

### Complex Pattern with Captures

```json
{
  "name": "decl-record01",
  "title": "Format record type declarations",
  "category": "declaration",
  "find": "type\\s+(\\w+)\\s+is\\s+record",
  "replace": "type \\1 is record",
  "flags": ["MULTILINE"]
}
```

---

For more examples and the default patterns, see `adafmt_patterns.json` in the project repository.

## See Also

- [Getting Started Guide](getting-started-guide.md) - Basic adafmt usage
- [Troubleshooting Guide](troubleshooting-guide.md) - General troubleshooting
- [API Reference](../api/index.md) - Complete API documentation
