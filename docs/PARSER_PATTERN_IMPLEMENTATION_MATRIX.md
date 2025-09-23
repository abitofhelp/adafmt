# Parser Pattern Implementation Matrix

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Implementation Guide

Distilled implementation guide for parser-based patterns to fix ALS formatting holes.

## Pre-ALS Patterns (Prevent ALS Issues)

| Pattern Name | Core Issue | Parser Markers | Fix | Priority |
|--------------|------------|----------------|-----|----------|
| **string_literal_safety** | ALS corrupts long strings | `visitString_literal()` + line length > 120 | Break with `&` concatenation | Critical |
| **syntax_validation** | ALS crashes on syntax errors | Parse result = `Failure` | Skip file, log error | Critical |
| **preprocessing_detect** | GNATformat can't handle `#if/#endif` | Text contains `#if`, `#elsif`, `#endif` | Skip or handle separately | Critical |

### Pre-ALS Implementation Details

```python
# string_literal_safety
class PreALSStringVisitor(Ada2022ParserVisitor):
    def visitString_literal(self, ctx):
        line_num = ctx.start.line - 1
        line = self.source_lines[line_num]
        if len(line) > 120:  # configurable
            # Break string using Ada concatenation
            return self.break_string_safely(ctx.getText())

# syntax_validation  
def pre_als_syntax_check(ada_code: str) -> bool:
    parser = Parser()
    result = parser.parse(ada_code)
    return isinstance(result, Success)

# preprocessing_detect
def has_preprocessing_directives(ada_code: str) -> bool:
    return any(line.strip().startswith('#') for line in ada_code.split('\n'))
```

## Post-ALS Patterns (Fix ALS Omissions)

| Pattern Name | Core Issue | Parser Markers | Fix | Priority |
|--------------|------------|----------------|-----|----------|
| **comment_spacing** | `--` needs proper spacing | Terminal nodes with `--` text | Ensure ` -- ` format | High |
| **assign_spacing** | `:=` missing spaces | `visitAssignment_statement()`, `visitObject_declaration()` | Ensure ` := ` format | High |
| **range_spacing** | `..` missing spaces | `visitDiscrete_range()` | Ensure ` .. ` format | High |
| **arrow_spacing** | `=>` missing spaces | `visitCase_statement_alternative()`, aggregates | Ensure ` => ` format | High |
| **vertical_alignment** | Columns not aligned | Multiple declarations in sequence | Align `:`, `:=`, `--` | Medium |
| **casing_dictionary** | Special identifier casing | `visitIdentifier()` | Apply custom casing rules | Medium |

### Post-ALS Implementation Details

```python
# comment_spacing
class CommentSpacingVisitor(Ada2022ParserVisitor):
    def visitTerminal(self, node):
        if hasattr(node, 'symbol') and '--' in node.symbol.text:
            # Fix spacing: ensure " -- " format
            return self.fix_comment_spacing(node)

# assign_spacing  
class AssignmentSpacingVisitor(Ada2022ParserVisitor):
    def visitObject_declaration(self, ctx):
        line_text = self.get_line_text(ctx)
        if ':=' in line_text and not self.is_in_string(ctx):
            return self.fix_operator_spacing(line_text, ':=')
    
    def visitAssignment_statement(self, ctx):
        # Same logic as above
        return self.fix_assignment_spacing(ctx)

# range_spacing
class RangeSpacingVisitor(Ada2022ParserVisitor):
    def visitDiscrete_range(self, ctx):
        text = ctx.getText()
        if '..' in text and not ' .. ' in text:
            return self.fix_operator_spacing(text, '..')

# arrow_spacing
class ArrowSpacingVisitor(Ada2022ParserVisitor):
    def visitCase_statement_alternative(self, ctx):
        return self.fix_operator_spacing(ctx, '=>')
    
    def visitNamed_association(self, ctx):  # For aggregates
        return self.fix_operator_spacing(ctx, '=>')

# vertical_alignment
class VerticalAlignmentVisitor(Ada2022ParserVisitor):
    def visitDeclarative_part(self, ctx):
        # Find sequential declarations
        declarations = self.find_declaration_block(ctx)
        return self.align_declaration_operators(declarations)

# casing_dictionary
class CasingVisitor(Ada2022ParserVisitor):
    def __init__(self, dictionary: Dict[str, str]):
        self.casing_dict = dictionary  # {"usb_id": "USB_ID"}
    
    def visitIdentifier(self, ctx):
        name = ctx.getText().lower()
        if name in self.casing_dict:
            return self.replace_identifier(ctx, self.casing_dict[name])
```

## Implementation Workflow

```
Input Ada File
       ↓
   Pre-ALS Patterns ←── Skip if preprocessing detected
       ↓                Skip if syntax invalid  
   ALS Formatting       Break long strings safely
       ↓
   Post-ALS Patterns ←── Fix comment spacing
       ↓                Fix operator spacing
   GNAT Validation      Apply vertical alignment
       ↓                Apply casing dictionary
   Output Ada File
```

## Parser Markers Quick Reference

| What to Look For | Visitor Method | Context Check |
|------------------|----------------|---------------|
| String literals | `visitString_literal()` | Always safe to modify |
| Comments | `visitTerminal()` with `--` | Check not in string |
| Assignments | `visitAssignment_statement()` | Check not in string |
| Declarations | `visitObject_declaration()` | Check not in string |
| Ranges | `visitDiscrete_range()` | Check not in string |
| Case alternatives | `visitCase_statement_alternative()` | Check for `=>` |
| Aggregates | `visitNamed_association()` | Check for `=>` |
| Declaration blocks | `visitDeclarative_part()` | For alignment |
| Identifiers | `visitIdentifier()` | For casing rules |

## String Safety Framework

**Critical**: Always check if we're inside a string literal before applying fixes.

```python
class SafeFormattingVisitor(Ada2022ParserVisitor):
    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.string_regions = []  # Populated by visitString_literal
        
    def visitString_literal(self, ctx):
        # Record this region as protected
        start_line = ctx.start.line - 1
        start_col = ctx.start.column  
        end_col = start_col + len(ctx.getText())
        self.string_regions.append((start_line, start_col, end_col))
        return self.visitChildren(ctx)
    
    def is_in_string(self, line: int, col: int) -> bool:
        """Check if position is inside any string literal."""
        for str_line, start_col, end_col in self.string_regions:
            if line == str_line and start_col <= col <= end_col:
                return True
        return False
    
    def safe_fix_operator(self, ctx, operator: str):
        """Only fix operator if not in string literal."""
        line = ctx.start.line - 1
        col = self.find_operator_column(ctx, operator)
        
        if not self.is_in_string(line, col):
            return self.fix_operator_spacing(ctx, operator)
        
        return None  # Skip - inside string
```

## Configuration Options

```python
@dataclass
class FormattingConfig:
    # Pre-ALS
    max_line_length: int = 120
    break_strings: bool = True
    skip_preprocessing: bool = True
    
    # Post-ALS
    normalize_comments: bool = True
    fix_operator_spacing: bool = True
    apply_vertical_alignment: bool = False  # Optional
    
    # Casing dictionary
    identifier_casing: Dict[str, str] = field(default_factory=dict)
    
    # Style preferences  
    spaces_after_comment: int = 2  # " -- " format
    align_operators: bool = False
```

## Testing Strategy

For each pattern:

1. **Create test Ada code** with the issue
2. **Verify parser identifies** the correct nodes
3. **Apply fix** and check result
4. **Validate with GNAT** compiler
5. **Test string safety** - ensure no corruption

```python
def test_assign_spacing_pattern():
    ada_code = '''
    procedure Test is
       X : Integer:=42;  -- Missing spaces
       S : String := "Text with := inside";  -- Should NOT be modified
    begin
       X:=X+1;  -- Missing spaces
    end Test;
    '''
    
    # Apply pattern
    result = apply_assignment_spacing_pattern(ada_code)
    
    # Verify fixes
    assert ' := 42' in result  # Fixed declaration
    assert ' := X + 1' in result  # Fixed assignment
    assert '"Text with := inside"' in result  # String unchanged
    
    # Verify compilable
    assert gnat_syntax_check(result)
```

## Summary

This matrix provides:
- **Actionable patterns** with specific visitor methods
- **Safety framework** to prevent string corruption  
- **Clear pre/post-ALS classification**
- **Implementation code snippets**
- **Testing approach**

Each pattern targets a specific ALS formatting hole using the appropriate parser visitor method, with string literal safety as the overriding concern.