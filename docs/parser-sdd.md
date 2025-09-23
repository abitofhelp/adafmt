# Software Design Document: Parser-Based Architecture

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

## 1. Introduction

### 1.1 Purpose
This document describes the detailed design of the parser-based architecture for adafmt. It explains how the Ada 2022 ANTLR parser integrates with the existing system to provide safe, context-aware formatting.

### 1.2 Scope
The design covers:
- Integration of ada2022_parser with existing infrastructure
- Visitor pattern implementations for formatting rules
- Pre-ALS and Post-ALS processing pipelines
- GNAT compiler validation integration
- Migration from regex patterns to parser-based rules

### 1.3 Design Goals
1. **Correctness**: Never corrupt valid Ada code
2. **Context Awareness**: Understand Ada semantics, not just syntax
3. **Extensibility**: Easy to add new formatting rules
4. **Performance**: Acceptable overhead for parsing benefits
5. **Compatibility**: Maintain existing interfaces and workflows

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐
│ File Discovery  │ → Existing component
└────────┬────────┘
         ↓
┌─────────────────┐
│  Worker Pool    │ → Existing component
└────────┬────────┘
         ↓
┌─────────────────┐
│ Parser Pipeline │ → NEW component
├─────────────────┤
│ • Parse to AST  │
│ • Pre-ALS Visit │
│ • ALS Format    │
│ • Post-ALS Visit│
│ • GNAT Validate │
└────────┬────────┘
         ↓
┌─────────────────┐
│   File Writer   │ → Existing component
└─────────────────┘
```

### 2.2 Component Design

#### 2.2.1 Parser Integration
```python
from returns.result import Result, Success, Failure
from returns.io import IOResult, impure_safe

class AdaParser:
    """Wrapper around ada2022_parser for adafmt integration."""
    
    def __init__(self):
        self.parser = Parser()  # From ada2022_parser
        
    @impure_safe
    def _read_file_internal(self, file_path: Path) -> str:
        """Internal read with automatic exception handling."""
        return file_path.read_text(encoding='utf-8')
        
    def read_file(self, file_path: Path) -> Result[str, FileError]:
        """Read file with specific error mapping."""
        return self._read_file_internal(file_path).map_failure(
            lambda exc: FileError(
                path=file_path,
                operation="read",
                message=str(exc),
                permission_error=isinstance(exc, PermissionError)
            )
        )
        
    @impure_safe
    def _parse_content_internal(self, content: str) -> Any:
        """Internal parse with automatic exception handling."""
        return self.parser.parse(content)
        
    def parse_content(self, content: str, path: Path) -> Result[ParseResult, ParseError]:
        """Parse Ada content and return Result type."""
        return self._parse_content_internal(content).map_failure(
            lambda exc: ParseError(
                path=path,
                line=getattr(exc, 'line', 0),
                column=getattr(exc, 'column', 0),
                message=str(exc)
            )
        ).map(
            lambda tree: ParseResult(
                ast=tree,
                source_lines=content.split('\n'),
                path=path
            )
        )
    
    def parse_file(self, file_path: Path) -> Result[ParseResult, ParseError | FileError]:
        """Parse Ada file with full error handling."""
        return self.read_file(file_path).bind(
            lambda content: self.parse_content(content, file_path)
        )
```

#### 2.2.2 Visitor Base Class
```python
class FormattingVisitor(Ada2022ParserVisitor):
    """Base class for all formatting visitors."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.modifications = []
        self.string_regions = []
        
    def visitString_literal(self, ctx):
        """Record string literal regions for protection."""
        start_line = ctx.start.line - 1
        start_col = ctx.start.column
        end_col = start_col + len(ctx.getText())
        self.string_regions.append((start_line, start_col, end_col))
        return self.visitChildren(ctx)
        
    def is_in_string(self, line: int, col: int) -> bool:
        """Check if position is inside a string literal."""
        for str_line, start_col, end_col in self.string_regions:
            if line == str_line and start_col <= col <= end_col:
                return True
        return False
        
    def record_modification(self, line: int, col: int, 
                          old_text: str, new_text: str):
        """Record a modification to apply later."""
        self.modifications.append({
            'line': line,
            'column': col,
            'old': old_text,
            'new': new_text
        })
```

#### 2.2.3 Pre-ALS Visitors

```python
class StringLiteralSafetyVisitor(FormattingVisitor):
    """Break long string literals safely before ALS."""
    
    def __init__(self, source_lines: List[str], max_line_length: int = 120):
        super().__init__(source_lines)
        self.max_line_length = max_line_length
        
    def visitString_literal(self, ctx):
        """Check and break long string literals."""
        line_num = ctx.start.line - 1
        line = self.source_lines[line_num]
        
        if len(line) > self.max_line_length:
            # Extract string content and break it
            string_text = ctx.getText()
            segments = self.break_string(string_text)
            
            if len(segments) > 1:
                # Find the assignment context
                assignment_ctx = self.find_parent_assignment(ctx)
                if assignment_ctx:
                    new_text = self.format_multiline_string(
                        assignment_ctx, segments
                    )
                    self.record_modification(
                        line_num, 0, line, new_text
                    )
        
        return super().visitString_literal(ctx)
        
    def break_string(self, string_lit: str) -> List[str]:
        """Break string into segments at natural boundaries."""
        # Implementation details...
        pass
```

```python
class PreprocessingDetector(FormattingVisitor):
    """Detect files with preprocessing directives."""
    
    def __init__(self, source_lines: List[str]):
        super().__init__(source_lines)
        self.has_preprocessing = False
        
    def check_preprocessing(self) -> bool:
        """Check for preprocessing directives."""
        for line in self.source_lines:
            if line.strip().startswith('#'):
                self.has_preprocessing = True
                return True
        return False
```

#### 2.2.4 Post-ALS Visitors

```python
class CommentSpacingVisitor(FormattingVisitor):
    """Fix comment spacing after --."""
    
    def visitTerminal(self, node):
        """Check terminal nodes for comments."""
        if hasattr(node, 'symbol') and '--' in node.symbol.text:
            line_num = node.symbol.line - 1
            col = node.symbol.column
            
            if not self.is_in_string(line_num, col):
                line = self.source_lines[line_num]
                
                # Check spacing after --
                after_idx = col + 2
                if after_idx < len(line) and line[after_idx] != ' ':
                    # Need to add space
                    old_text = line
                    new_text = line[:after_idx] + ' ' + line[after_idx:]
                    self.record_modification(
                        line_num, 0, old_text, new_text
                    )
        
        return self.visitChildren(node)
```

```python
class OperatorSpacingVisitor(FormattingVisitor):
    """Fix spacing around operators."""
    
    def __init__(self, source_lines: List[str]):
        super().__init__(source_lines)
        self.operators = [':=', '=>', '..', '>=', '<=', '/=']
        
    def visitObject_declaration(self, ctx):
        """Fix := spacing in declarations."""
        self.check_operator_spacing(ctx, ':=')
        return self.visitChildren(ctx)
        
    def visitAssignment_statement(self, ctx):
        """Fix := spacing in assignments."""
        self.check_operator_spacing(ctx, ':=')
        return self.visitChildren(ctx)
        
    def visitDiscrete_range(self, ctx):
        """Fix .. spacing in ranges."""
        self.check_operator_spacing(ctx, '..')
        return self.visitChildren(ctx)
        
    def check_operator_spacing(self, ctx, operator: str):
        """Check and fix operator spacing."""
        line_num = ctx.start.line - 1
        line = self.source_lines[line_num]
        
        # Find operator position
        col = line.find(operator)
        if col >= 0 and not self.is_in_string(line_num, col):
            # Check spacing
            before_ok = col == 0 or line[col-1] == ' '
            after_ok = col + len(operator) >= len(line) or \
                      line[col + len(operator)] == ' '
            
            if not before_ok or not after_ok:
                # Fix spacing
                old_text = line
                new_text = self.fix_operator_spacing(line, col, operator)
                self.record_modification(line_num, 0, old_text, new_text)
```

### 2.3 Processing Pipeline

```python
class ParserBasedFormatter:
    """Main formatting pipeline using parser."""
    
    def __init__(self, config: FormattingConfig):
        self.config = config
        self.parser = AdaParser()
        self.pre_als_visitors = [
            StringLiteralSafetyVisitor,
            PreprocessingDetector
        ]
        self.post_als_visitors = [
            CommentSpacingVisitor,
            OperatorSpacingVisitor,
            RangeSpacingVisitor,
            ArrowSpacingVisitor
        ]
        
    async def format_file(self, file_path: Path) -> FormattingResult:
        """Format a single Ada file."""
        
        # 1. Parse the file
        parse_result = self.parser.parse_file(file_path)
        if not parse_result.success:
            return FormattingResult(
                success=False,
                error=f"Parse error: {parse_result.error}"
            )
        
        # 2. Pre-ALS processing
        modified_source = self.apply_pre_als(
            parse_result.ast,
            parse_result.source_lines
        )
        
        # 3. ALS formatting
        als_result = await self.apply_als_formatting(
            file_path, modified_source
        )
        
        # 4. Post-ALS processing
        final_source = self.apply_post_als(
            als_result.ast,
            als_result.source_lines
        )
        
        # 5. GNAT validation
        if self.config.gnat_validation:
            valid = await self.validate_with_gnat(file_path, final_source)
            if not valid:
                return FormattingResult(
                    success=False,
                    error="GNAT validation failed"
                )
        
        return FormattingResult(
            success=True,
            content=final_source
        )
```

### 2.4 GNAT Validation

```python
class GNATValidator:
    """Validate Ada code using GNAT compiler."""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger
        self.command_template = [
            'gcc', '-c', '-gnatc', '-gnatf', 
            '-gnat2022', '-gnatwe', '-o', '/tmp/test.ali'
        ]
        
    async def validate(self, file_path: Path, content: str) -> ValidationResult:
        """Validate Ada code with GNAT."""
        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            suffix='.adb', mode='w', delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            # Run GNAT
            cmd = self.command_template + [tmp_path]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return ValidationResult(valid=True)
            else:
                return ValidationResult(
                    valid=False,
                    errors=stderr.decode('utf-8'),
                    warnings=stdout.decode('utf-8')
                )
                
        finally:
            os.unlink(tmp_path)
```

## 3. Data Structures

### 3.1 Core Data Types

```python
@dataclass
class ParseResult:
    """Result of parsing an Ada file."""
    ast: Optional[Any]  # ANTLR parse tree
    source_lines: Optional[List[str]]
    success: bool
    error: Optional[str] = None

@dataclass
class Modification:
    """A single text modification."""
    line: int
    column: int
    old_text: str
    new_text: str

@dataclass
class FormattingResult:
    """Result of formatting a file."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    modifications_count: int = 0

@dataclass
class ValidationResult:
    """Result of GNAT validation."""
    valid: bool
    errors: Optional[str] = None
    warnings: Optional[str] = None
```

## 4. Interface Design

### 4.1 Command Line Interface

```bash
# New flags
--no-pre-als          # Skip Pre-ALS processing
--no-post-als         # Skip Post-ALS processing  
--no-gnat-validation  # Skip GNAT validation
--casing-dictionary   # Path to identifier casing rules

# Deprecated
--no-patterns         # Replaced by --no-post-als
```

### 4.2 Configuration Interface

```yaml
# adafmt.yaml
parser:
  max_line_length: 120
  break_long_strings: true
  
pre_als:
  enabled: true
  visitors:
    - string_safety
    - preprocessing_check
    
post_als:
  enabled: true
  visitors:
    - comment_spacing
    - operator_spacing
    - range_spacing
    - arrow_spacing
    
validation:
  gnat_enabled: true
  gnat_flags: ["-gnatwe", "-gnatf"]
  
casing:
  dictionary_path: "project_casing.yaml"
  rules:
    USB_ID: "USB_ID"
    HTTP_Client: "HTTP_Client"
```

## 5. Functional Error Handling with Decorators

### 5.0 Decorator Pattern Architecture

The parser-based architecture uses dry-python/returns decorators to achieve functional error handling with minimal boilerplate:

#### 5.0.1 Decorator Selection Guidelines
- **@impure_safe**: For synchronous functions that may raise exceptions
- **@future_safe**: For async functions that may raise exceptions  
- **Error mapping**: Always map generic exceptions to specific error types

#### 5.0.2 Standard Pattern
```python
# Internal function with decorator (catches exceptions automatically)
@impure_safe
def _internal_operation(path: Path, data: str) -> str:
    """Internal operation with automatic exception handling."""
    return path.write_text(data)  # May raise exceptions

# Public API with error mapping
def public_operation(path: Path, data: str) -> Result[str, FileError]:
    """Public API with specific error types."""
    return _internal_operation(path, data).map_failure(
        lambda exc: FileError(
            path=path,
            operation="write",
            message=str(exc),
            permission_error=isinstance(exc, PermissionError)
        )
    )

# Async variant
@future_safe
async def _async_internal_operation(path: Path) -> str:
    """Async internal operation with automatic exception handling."""
    return await async_read_file(path)

async def async_public_operation(path: Path) -> Result[str, FileError]:
    """Async public API with specific error types."""
    return await _async_internal_operation(path).map_failure(
        lambda exc: FileError(
            path=path,
            operation="read",
            message=str(exc)
        )
    )
```

#### 5.0.3 Benefits of Decorator Pattern
1. **Reduced Boilerplate**: No manual try/catch blocks
2. **Consistent Error Handling**: All exceptions caught at function boundary
3. **Type Safety**: IOResult types ensure exceptions don't propagate
4. **Testability**: Easy to test error conditions
5. **Composability**: Results can be chained with bind(), map(), etc.

### 5.1 Error Type Hierarchy
```python
from dataclasses import dataclass
from typing import Literal
from pathlib import Path

@dataclass(frozen=True)
class ParseError:
    """Ada parsing error."""
    path: Path
    line: int
    column: int
    message: str
    
@dataclass(frozen=True)
class VisitorError:
    """Visitor processing error."""
    path: Path
    visitor_name: str
    node_type: str
    message: str

@dataclass(frozen=True)
class ALSError:
    """ALS communication error."""
    path: Path
    operation: Literal["format", "initialize", "shutdown"]
    message: str
    timeout: bool = False

@dataclass(frozen=True)
class GNATError:
    """GNAT validation error."""
    path: Path
    exit_code: int
    stdout: str
    stderr: str

@dataclass(frozen=True)
class FileError:
    """File operation error."""
    path: Path
    operation: Literal["read", "write", "create", "delete"]
    message: str
    permission_error: bool = False
```

### 5.2 Result Type Usage
```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind

class FormatterPipeline:
    """Pipeline with comprehensive error handling."""
    
    def format_file(self, path: Path) -> Result[FormattedFile, FormattingError]:
        """Format file with full error tracking."""
        return flow(
            path,
            self.parser.parse_file,           # IOResult[ParseResult, ParseError]
            bind(self.apply_pre_als),         # Result[str, VisitorError]
            bind(self.format_with_als),       # FutureResult[str, ALSError]
            bind(self.apply_post_als),        # Result[str, VisitorError]
            bind(self.validate_with_gnat),    # IOResult[str, GNATError]
            bind(self.write_result)           # IOResult[Path, FileError]
        )
```

### 5.3 Visitor Error Handling
```python
class SafeFormattingVisitor(FormattingVisitor):
    """Visitor with comprehensive error handling."""
    
    def safe_visit(self, tree) -> Result[str, VisitorError]:
        """Visit tree with error handling."""
        try:
            self.visit(tree)
            return Success(self.get_result())
        except Exception as e:
            return Failure(VisitorError(
                path=self.path,
                visitor_name=self.__class__.__name__,
                node_type=tree.__class__.__name__,
                message=str(e)
            ))
    
    def visit_with_recovery(self, tree) -> Result[str, VisitorError]:
        """Visit with error recovery."""
        result = self.safe_visit(tree)
        
        if isinstance(result, Failure):
            # Log error but return original content
            logger.warning(f"Visitor failed: {result.failure()}")
            return Success(self.original_content)
        
        return result
```

### 5.4 ALS Error Handling
```python
from returns.future import future_safe
from returns.result import Result

class ALSClient:
    """ALS client with functional error handling."""
    
    @future_safe
    async def _format_document_internal(self, path: Path, content: str) -> str:
        """Internal format with automatic exception handling."""
        request = self.create_format_request(path, content)
        response = await self.send_request(request)
        return self.apply_edits(content, response['result'])
        
    async def format_document(self, path: Path, content: str) -> Result[str, ALSError]:
        """Format with specific error mapping."""
        return await self._format_document_internal(path, content).map_failure(
            lambda exc: ALSError(
                path=path,
                operation="format",
                message=str(exc),
                timeout=isinstance(exc, asyncio.TimeoutError)
            )
        )
    
    async def format_with_retry(
        self, 
        path: Path, 
        content: str, 
        max_attempts: int = 3
    ) -> Result[str, ALSError]:
        """Format with retry logic."""
        for attempt in range(max_attempts):
            result = await self.format_document(path, content)
            
            if isinstance(result, Success):
                return result
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return result  # Return last failure
```

### 5.5 GNAT Validation Error Handling
```python
from returns.io import impure_safe
import subprocess

class GNATValidator:
    """GNAT validation with error handling."""
    
    @impure_safe
    def _validate_file_internal(self, path: Path) -> subprocess.CompletedProcess:
        """Internal validation with automatic exception handling."""
        return subprocess.run(
            ['gcc', '-c', '-gnatc', '-gnatf', '-gnat2022', '-gnatwe', str(path)],
            capture_output=True,
            text=True,
            check=True  # Raises on non-zero exit
        )
        
    def validate_file(self, path: Path) -> Result[None, GNATError]:
        """Validate with GNAT, mapping subprocess errors."""
        return self._validate_file_internal(path).map_failure(
            lambda exc: GNATError(
                path=path,
                exit_code=getattr(exc, 'returncode', -1),
                stdout=getattr(exc, 'stdout', ''),
                stderr=getattr(exc, 'stderr', str(exc))
            )
        ).map(lambda _: None)  # Success returns None
```

### 5.6 Concurrent Error Handling
```python
from returns.future import future_safe
from typing import List

class WorkerPool:
    """Worker pool with functional error handling."""
    
    @future_safe
    async def _process_single_file_internal(self, path: Path) -> FormattedFile:
        """Internal file processing with automatic exception handling."""
        # All exceptions automatically caught by decorator
        content = await self.read_file(path)
        formatted = await self.format_content(content, path)
        return await self.write_file(path, formatted)
        
    async def process_single_file(self, path: Path) -> Result[FormattedFile, FormattingError]:
        """Process single file with specific error mapping."""
        return await self._process_single_file_internal(path).map_failure(
            lambda exc: FormattingError(
                path=path,
                message=str(exc),
                operation="format"
            )
        )
    
    async def process_files(
        self, 
        paths: List[Path]
    ) -> Result[List[FormattedFile], List[FormattingError]]:
        """Process files with error collection."""
        # Create futures for all files
        futures = [
            self.process_single_file(path) 
            for path in paths
        ]
        
        # Gather results (never raises exceptions due to Result types)
        results = await asyncio.gather(*futures, return_exceptions=False)
        
        # Separate successes and failures
        successes = []
        failures = []
        
        for result in results:
            if isinstance(result, Success):
                successes.append(result.unwrap())
            elif isinstance(result, Failure):
                failures.append(result.failure())
        
        if failures:
            return Failure(failures)
        else:
            return Success(successes)
```

### 5.7 Error Recovery Strategies

#### 5.7.1 Partial Success
```python
def format_with_fallback(self, path: Path) -> Result[FormattedFile, FormattingError]:
    """Try full formatting, fall back to partial."""
    # Using chained error recovery with alt() method
    return (
        self.full_format(path)
        .alt(lambda _: self.als_only_format(path))
        .alt(lambda _: self.parse_only_check(path))
        .alt(lambda _: Success(UnformattedFile(path)))
    )
```

#### 5.7.2 Circuit Breaker
```python
class ALSCircuitBreaker:
    """Circuit breaker for ALS failures."""
    
    def __init__(self, failure_threshold: int = 5):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.is_open = False
        
    async def call(self, operation) -> Result[T, ALSError]:
        """Execute with circuit breaker."""
        if self.is_open:
            return Failure(ALSError(
                path=Path(""),
                operation="circuit_breaker",
                message="Circuit breaker is open"
            ))
        
        result = await operation()
        
        if isinstance(result, Failure):
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
        else:
            self.failure_count = 0
            
        return result
```

### 5.8 Error Reporting
```python
def report_errors(results: List[Result[FormattedFile, FormattingError]]) -> None:
    """Report errors in a user-friendly way."""
    errors_by_type = defaultdict(list)
    
    for result in results:
        if isinstance(result, Failure):
            error = result.failure()
            errors_by_type[type(error).__name__].append(error)
    
    if errors_by_type:
        console.print("\n[red]Errors encountered:[/red]")
        
        for error_type, errors in errors_by_type.items():
            console.print(f"\n[yellow]{error_type}:[/yellow]")
            for error in errors[:5]:  # Limit to 5 per type
                console.print(f"  • {error.path}: {error.message}")
            
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more")
```

## 6. Performance Considerations

### 6.1 Parsing Optimization
- Parse each file once, reuse AST
- Consider caching parsed ASTs for large projects
- Use lazy parsing for large files

### 6.2 Visitor Optimization
- Minimize AST traversals
- Combine related visitors when possible
- Skip visitors based on file characteristics

### 6.3 Parallelization
- Maintain worker pool for file-level parallelism
- Consider parallel visitor execution (if independent)
- Batch GNAT validations when possible

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each visitor in isolation
- Test string literal detection
- Test modification application
- Test GNAT command generation

### 7.2 Integration Tests
- Test full pipeline with various Ada constructs
- Test error scenarios
- Test performance with large files
- Test worker pool integration

### 7.3 Regression Tests
- Ensure no string literal corruption
- Verify all regex pattern functionality preserved
- Test edge cases from bug reports

## 8. Migration Plan

### 8.1 Phase 1: Infrastructure
1. Create parser integration layer
2. Implement base visitor class
3. Add GNAT validation
4. Update worker pool interface

### 8.2 Phase 2: Core Visitors
1. Implement string safety visitor
2. Implement operator spacing visitors
3. Implement comment spacing visitor
4. Test with small projects

### 8.3 Phase 3: Advanced Features
1. Add vertical alignment
2. Add casing dictionary
3. Implement configuration system
4. Performance optimization

### 8.4 Phase 4: Deprecation
1. Mark regex patterns as deprecated
2. Provide migration guide
3. Remove regex code in future version

## 9. Future Enhancements

### 9.1 Additional Visitors
- Pragma formatting
- Aspect clause alignment
- Generic instantiation formatting
- Use clause organization

### 9.2 Smart Features
- Context-aware line breaking
- Semantic-based alignment
- Project-wide consistency checking
- Style inference from existing code

### 9.3 Tool Integration
- IDE plugin support
- Git pre-commit hooks
- CI/CD integration
- Code review tools