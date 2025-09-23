# Parser Integration Guide

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This guide explains how to integrate and use the new parser-based architecture for Ada formatting in adafmt.

## Overview

The parser-based architecture replaces regex patterns with AST visitors that understand Ada syntax. This provides:

- **Context awareness**: Understands when code is inside string literals
- **Correctness**: Never corrupts valid Ada code
- **Extensibility**: Easy to add new formatting rules
- **Safety**: Comprehensive error handling with Result types

## Architecture Components

### 1. Parser Wrapper (`parser_wrapper.py`)

The parser wrapper provides a functional interface to the Ada 2022 ANTLR parser:

```python
from adafmt.parser_wrapper import parse_ada_content, AdaParserWrapper

# Parse content directly
result = parse_ada_content(ada_source, Path("example.adb"))

if isinstance(result, Success):
    parse_result = result.unwrap()
    print(f"Parsed {parse_result.line_count} lines")
    print(f"Has preprocessing: {parse_result.has_preprocessing}")
else:
    error = result.failure()
    print(f"Parse failed: {error.message} at {error.line}:{error.column}")
```

### 2. Formatting Visitors

Visitors implement the actual formatting rules:

#### Base Visitor (`formatting_visitor.py`)

All visitors inherit from `FormattingVisitorBase`:

```python
from adafmt.formatting_visitor import FormattingVisitorBase

class MyCustomVisitor(FormattingVisitorBase):
    def get_visitor_name(self) -> str:
        return "MyCustomVisitor"
    
    def get_supported_rules(self) -> List[str]:
        return ["my_custom_rule"]
    
    def _apply_formatting_rules(self, tree: Any) -> None:
        # Process each line
        for line_num, line in enumerate(self.source_lines):
            if self.is_line_in_string_literal(line_num):
                continue  # Skip lines in string literals
            
            # Apply custom formatting logic
            modified_line = self.apply_my_rule(line)
            
            if modified_line != line:
                self.record_line_modification(
                    line_num=line_num,
                    new_line=modified_line,
                    description="Applied my custom rule"
                )
                self.applied_rules.add("my_custom_rule")
```

#### Comment Spacing Visitor (`comment_spacing_visitor.py`)

Fixes spacing after comment indicators:

```python
from adafmt.comment_spacing_visitor import CommentSpacingVisitor

# Process source lines
visitor = CommentSpacingVisitor(source_lines, Path("file.adb"))
result = visitor.visit_tree(ast)

if isinstance(result, Success):
    visitor_result = result.unwrap()
    print(f"Fixed {visitor_result.statistics['fixed_comments']} comments")
```

#### Operator Spacing Visitor (`operator_spacing_visitor.py`)

Fixes spacing around Ada operators:

```python
from adafmt.operator_spacing_visitor import OperatorSpacingVisitor

visitor = OperatorSpacingVisitor(source_lines, Path("file.adb"))
result = visitor.visit_tree(ast)

if isinstance(result, Success):
    visitor_result = result.unwrap()
    stats = visitor.get_operator_statistics()
    print(f"Fixed {stats['total_fixes']} operators")
    print(f"Rules applied: {stats['rules_applied']}")
```

### 3. Pattern Processor (`parser_pattern_processor.py`)

The pattern processor orchestrates multiple visitors:

```python
from adafmt.parser_pattern_processor import ParserPatternProcessor

# Create processor with specific patterns enabled
enabled_patterns = {"comment_spacing", "assignment_spacing", "arrow_spacing"}
processor = ParserPatternProcessor(enabled_patterns)

# Process Ada content
result = processor.process_content(ada_source, Path("example.adb"))

if isinstance(result, Success):
    proc_result = result.unwrap()
    
    if proc_result.has_changes:
        print(f"Applied {len(proc_result.applied_patterns)} patterns")
        print(f"Made {proc_result.total_modifications} modifications")
        
        # Get the formatted content
        formatted_content = proc_result.modified_content
    else:
        print("No changes needed")
else:
    error = result.failure()
    print(f"Processing failed: {error.message}")
```

## Error Handling

All functions use functional error handling with Result types:

```python
from returns.result import Success, Failure

# All operations return Result[Value, Error]
result = parser.parse_content(content, path)

# Pattern matching for error handling
match result:
    case Success(value):
        # Success path
        print(f"Parsed successfully: {value}")
    case Failure(error):
        # Error path
        print(f"Error: {error.message}")
        if hasattr(error, 'line'):
            print(f"At line {error.line}, column {error.column}")
```

### Error Types

- **ParseError**: Ada parsing failures
- **VisitorError**: Visitor processing failures  
- **PatternError**: Pattern application failures
- **FileError**: File operation failures

## Integration with Existing System

### Pattern Name Mapping

The parser processor maps legacy pattern names to visitors:

```python
pattern_mappings = {
    'assign_set01': 'operator_spacing',     # Legacy assignment pattern
    'comment_spacing': 'comment_spacing',   # Direct mapping
    'arrow_spacing': 'operator_spacing',    # Operator-based
    'range_spacing': 'operator_spacing',    # Operator-based
}
```

### Backward Compatibility

The processor provides the same interface as the regex system:

```python
# Old regex system interface
# processor.apply_patterns(content, enabled_patterns)

# New parser system interface (same signature)
result = processor.process_content(content, path)
```

## Adding New Formatting Rules

### 1. Create a New Visitor

```python
from adafmt.formatting_visitor import FormattingVisitorBase

class PragmaFormattingVisitor(FormattingVisitorBase):
    """Format pragma spacing and alignment."""
    
    def get_visitor_name(self) -> str:
        return "PragmaFormattingVisitor"
    
    def get_supported_rules(self) -> List[str]:
        return ["pragma_spacing", "pragma_alignment"]
    
    def _apply_formatting_rules(self, tree: Any) -> None:
        # Walk the AST to find pragma nodes
        self._visit_pragmas(tree)
    
    def _visit_pragmas(self, node: Any) -> None:
        # Implementation for pragma formatting
        pass
```

### 2. Register the Visitor

Add to `ParserPatternProcessor`:

```python
self.visitor_classes = {
    'comment_spacing': CommentSpacingVisitor,
    'operator_spacing': OperatorSpacingVisitor,
    'pragma_formatting': PragmaFormattingVisitor,  # Add new visitor
}

self.pattern_to_visitor = {
    # Existing mappings...
    'pragma_spacing': 'pragma_formatting',      # Add pattern mapping
    'pragma_alignment': 'pragma_formatting',
}
```

### 3. Add Tests

```python
def test_pragma_formatting():
    """Test pragma formatting visitor."""
    source = ["pragma Assert (X > 0);"]
    visitor = PragmaFormattingVisitor(source)
    
    result = visitor.visit_tree(dummy_ast)
    assert isinstance(result, Success)
    
    visitor_result = result.unwrap()
    assert visitor_result.has_changes
    assert "pragma_spacing" in visitor_result.applied_rules
```

## Configuration

### Enabling/Disabling Patterns

```python
# Enable specific patterns
enabled = {"comment_spacing", "assignment_spacing"}
processor = ParserPatternProcessor(enabled)

# Enable all patterns (default)
processor = ParserPatternProcessor()

# Disable all patterns
processor = ParserPatternProcessor(set())
```

### Pattern Validation

```python
# Validate pattern names
patterns = {"comment_spacing", "unknown_pattern"}
result = processor.validate_patterns(patterns)

if isinstance(result, Failure):
    error = result.failure()
    print(f"Invalid patterns: {error.message}")
```

## Performance Considerations

### Parser Caching

The parser wrapper can be reused across multiple files:

```python
parser = AdaParserWrapper()

for file_path in ada_files:
    result = parser.parse_file(file_path)
    # Process result...
```

### Visitor Optimization

- Visitors process line-by-line for efficiency
- String literal regions are identified once per file
- Modifications are applied in batch at the end

### Memory Usage

- AST nodes are processed in visitor pattern (no full tree storage)
- Source lines are kept in memory for modification
- Modifications are collected and applied efficiently

## Migration from Regex Patterns

### Pattern Mapping

| Regex Pattern | Parser Visitor | Notes |
|--------------|----------------|-------|
| `assign_set01` | `operator_spacing` | Assignment operator spacing |
| Comment patterns | `comment_spacing` | Context-aware comment handling |
| Operator patterns | `operator_spacing` | Multiple operator types |

### API Changes

```python
# Old regex-based API
from adafmt.pattern_formatter import PatternFormatter
formatter = PatternFormatter()
result = formatter.apply(path, content)

# New parser-based API
from adafmt.parser_pattern_processor import process_ada_content
result = process_ada_content(content, path, enabled_patterns)
```

### Benefits of Migration

1. **No string literal corruption**: Parser understands Ada syntax
2. **Better error messages**: Context-aware error reporting
3. **Extensible**: Easy to add complex formatting rules
4. **Testable**: Isolated visitor logic
5. **Maintainable**: Clear separation of concerns

## Examples

### Complete Processing Example

```python
from pathlib import Path
from adafmt.parser_pattern_processor import process_ada_file

# Process an Ada file
ada_file = Path("example.adb")
enabled_patterns = {"comment_spacing", "assignment_spacing", "arrow_spacing"}

result = process_ada_file(ada_file, enabled_patterns)

match result:
    case Success(proc_result):
        if proc_result.has_changes:
            # Write back the formatted content
            ada_file.write_text(proc_result.modified_content)
            
            print(f"Formatted {ada_file}")
            print(f"Applied patterns: {proc_result.applied_patterns}")
            print(f"Total changes: {proc_result.total_modifications}")
            
            # Show detailed statistics
            for visitor_result in proc_result.visitor_results:
                if visitor_result.statistics:
                    print(f"  {visitor_result.statistics}")
        else:
            print(f"No changes needed for {ada_file}")
    
    case Failure(error):
        print(f"Failed to process {ada_file}: {error.message}")
        if hasattr(error, 'line') and error.line > 0:
            print(f"  Error at line {error.line}")
```

This architecture provides a solid foundation for context-aware Ada formatting while maintaining compatibility with the existing pattern system.