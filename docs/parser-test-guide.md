# Parser-Based Architecture Testing Guide

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Draft

## 1. Introduction

### 1.1 Purpose
This guide provides comprehensive testing procedures for the parser-based architecture of adafmt. It covers unit tests, integration tests, and validation procedures to ensure correctness and reliability.

### 1.2 Testing Philosophy
- **Safety First**: Never corrupt valid Ada code
- **Comprehensive Coverage**: Test all Ada constructs
- **Real-World Focus**: Use actual Ada code examples
- **Performance Awareness**: Monitor parsing overhead
- **Regression Prevention**: Capture all fixed bugs as tests

## 2. Test Environment Setup

### 2.1 Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Install Ada 2022 parser
pip install /path/to/ada2022_parser-0.1.0-py3-none-any.whl

# Verify GNAT availability
gcc --version | grep "gcc"
gnatmake --version
```

### 2.2 Test Structure
```
tests/
├── parser/
│   ├── unit/
│   │   ├── test_string_safety.py
│   │   ├── test_operator_spacing.py
│   │   ├── test_comment_spacing.py
│   │   └── test_gnat_validation.py
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   ├── test_als_integration.py
│   │   └── test_worker_pool.py
│   └── fixtures/
│       ├── ada_samples/
│       └── expected_outputs/
```

## 3. Unit Test Specifications

### 3.1 String Literal Safety Tests

```python
class TestStringLiteralSafety:
    """Test string literal protection and breaking."""
    
    def test_string_detection(self):
        """Test accurate string literal detection."""
        ada_code = '''
        procedure Test is
           S1 : String := "Simple string";
           S2 : String := "String with "" quotes";
           S3 : String := "Multi" & "part" & "string";
        begin
           null;
        end Test;
        '''
        
        visitor = StringLiteralSafetyVisitor(ada_code.split('\n'))
        # Parse and visit
        assert len(visitor.string_regions) == 4
        assert visitor.is_in_string(2, 20)  # Inside "Simple string"
        assert not visitor.is_in_string(2, 10)  # Outside string
    
    def test_long_string_breaking(self):
        """Test breaking long strings with concatenation."""
        ada_code = '''
        Msg : String := "This is a very long error message that exceeds the maximum line length and needs breaking";
        '''
        
        visitor = StringLiteralSafetyVisitor(ada_code.split('\n'), max_line_length=80)
        result = visitor.process()
        
        assert '&' in result  # Concatenation added
        assert all(len(line) <= 80 for line in result.split('\n'))
    
    def test_string_break_points(self):
        """Test intelligent break point selection."""
        test_cases = [
            # (input, expected_breaks)
            ("Hello world this is long", ["Hello world ", "this is long"]),
            ("NoSpacesButVeryLongString", ["NoSpacesButVeryLongStr", "ing"]),
            ("Path/to/some/file.txt", ["Path/to/", "some/file.txt"]),
        ]
        
        for input_str, expected in test_cases:
            result = break_string_at_boundaries(input_str, max_len=15)
            assert result == expected
```

### 3.2 Operator Spacing Tests

```python
class TestOperatorSpacing:
    """Test operator spacing fixes."""
    
    def test_assignment_spacing(self):
        """Test := operator spacing."""
        ada_code = '''
        procedure Test is
           X:Integer:=5;     -- Needs fix
           Y : Integer := 6;  -- Already correct
           Z:=10;            -- Needs fix
        begin
           X:=X+1;           -- Needs fix
        end Test;
        '''
        
        visitor = OperatorSpacingVisitor(ada_code.split('\n'))
        result = visitor.process()
        
        assert 'X : Integer := 5;' in result
        assert 'Y : Integer := 6;' in result  # Unchanged
        assert 'Z := 10;' in result
        assert 'X := X + 1;' in result
    
    def test_operator_in_string_protection(self):
        """Test operators inside strings are not modified."""
        ada_code = '''
        Op : String := "Use := for assignment";
        X:=5;  -- This should be fixed
        '''
        
        visitor = OperatorSpacingVisitor(ada_code.split('\n'))
        result = visitor.process()
        
        assert '"Use := for assignment"' in result  # String unchanged
        assert 'X := 5;' in result  # Fixed outside string
    
    def test_all_operators(self):
        """Test all supported operators."""
        operators = [':=', '=>', '..', '>=', '<=', '/=']
        
        for op in operators:
            ada_code = f'A{op}B'
            visitor = OperatorSpacingVisitor([ada_code])
            result = visitor.process()
            assert f'A {op} B' in result
```

### 3.3 Comment Spacing Tests

```python
class TestCommentSpacing:
    """Test comment spacing normalization."""
    
    def test_whole_line_comments(self):
        """Test whole-line comment spacing."""
        test_cases = [
            ("--Comment", "-- Comment"),
            ("--  Comment", "-- Comment"),  # Normalize to 2 spaces
            ("---", "---"),  # Separator unchanged
            ("--#SPARK", "--#SPARK"),  # Special form unchanged
        ]
        
        for input_comment, expected in test_cases:
            visitor = CommentSpacingVisitor([input_comment])
            result = visitor.process()
            assert result.strip() == expected
    
    def test_end_of_line_comments(self):
        """Test end-of-line comment spacing."""
        ada_code = '''
        X : Integer;--Need space
        Y : Integer;  -- Already good
        Z : Integer;   --Too many spaces
        '''
        
        visitor = CommentSpacingVisitor(ada_code.split('\n'))
        result = visitor.process()
        
        assert 'Integer; -- Need space' in result
        assert 'Integer;  -- Already good' in result
        assert 'Integer; -- Too many spaces' in result
```

### 3.4 GNAT Validation Tests

```python
class TestGNATValidation:
    """Test GNAT compiler validation."""
    
    @pytest.mark.asyncio
    async def test_valid_code(self):
        """Test validation passes for correct code."""
        ada_code = '''
        procedure Test is
           X : Integer := 42;
        begin
           null;
        end Test;
        '''
        
        validator = GNATValidator()
        result = await validator.validate_string(ada_code)
        
        assert result.valid
        assert not result.errors
    
    @pytest.mark.asyncio
    async def test_syntax_error_detection(self):
        """Test validation catches syntax errors."""
        ada_code = '''
        procedure Test is
           X : Integer := ;  -- Syntax error
        begin
           null;
        end Test;
        '''
        
        validator = GNATValidator()
        result = await validator.validate_string(ada_code)
        
        assert not result.valid
        assert 'expected expression' in result.errors
    
    @pytest.mark.asyncio  
    async def test_semantic_error_detection(self):
        """Test validation catches semantic errors."""
        ada_code = '''
        procedure Test is
           X : Undefined_Type;  -- Semantic error
        begin
           null;
        end Test;
        '''
        
        validator = GNATValidator()
        result = await validator.validate_string(ada_code)
        
        assert not result.valid
        assert 'Undefined_Type' in result.errors
        assert 'not declared' in result.errors
```

## 4. Integration Test Specifications

### 4.1 Full Pipeline Tests

```python
class TestFullPipeline:
    """Test complete formatting pipeline."""
    
    @pytest.mark.asyncio
    async def test_simple_file_formatting(self):
        """Test formatting a simple Ada file."""
        ada_file = create_temp_ada_file('''
        procedure Simple is
           X:Integer:=42;  --Need spaces
        begin
           null;--Also needs space
        end Simple;
        ''')
        
        formatter = ParserBasedFormatter(config=default_config())
        result = await formatter.format_file(ada_file)
        
        assert result.success
        assert 'X : Integer := 42;  -- Need spaces' in result.content
        assert 'null; -- Also needs space' in result.content
    
    @pytest.mark.asyncio
    async def test_complex_file_formatting(self):
        """Test formatting complex Ada constructs."""
        ada_file = fixtures_path / 'complex_example.adb'
        expected = fixtures_path / 'complex_example_formatted.adb'
        
        formatter = ParserBasedFormatter(config=default_config())
        result = await formatter.format_file(ada_file)
        
        assert result.success
        assert result.content == expected.read_text()
```

### 4.2 ALS Integration Tests

```python
class TestALSIntegration:
    """Test parser-based formatting with ALS."""
    
    @pytest.mark.asyncio
    async def test_pre_als_prevents_corruption(self):
        """Test Pre-ALS processing prevents string corruption."""
        ada_code = '''
        Msg : String := "This very long string would be corrupted by ALS without pre-processing";
        '''
        
        # Process with Pre-ALS
        formatter = ParserBasedFormatter(config=default_config())
        pre_als_result = await formatter.apply_pre_als(ada_code)
        
        # Simulate ALS formatting
        als_result = await simulate_als_format(pre_als_result)
        
        # Verify no corruption
        assert '&' in als_result  # String was broken safely
        assert 'corrupted' in als_result  # Content preserved
        assert als_result.count('"') % 2 == 0  # Quotes balanced
```

## 5. Test Data Management

### 5.1 Test Fixtures

```python
@pytest.fixture
def ada_samples():
    """Provide sample Ada code for testing."""
    return {
        'simple': '''
        procedure Simple is
        begin
           null;
        end Simple;
        ''',
        
        'with_strings': '''
        with Ada.Text_IO; use Ada.Text_IO;
        procedure Strings is
           S1 : String := "Hello";
           S2 : String := "Line with := operator";
        begin
           Put_Line(S1 & S2);
        end Strings;
        ''',
        
        'complex_operators': '''
        procedure Operators is
           X : Integer range 1..10:=5;
           Y : array(1..5)of Integer:=(others=>0);
        begin
           case X is
              when 1=>null;
              when 2 => null;
              when others=>null;
           end case;
        end Operators;
        '''
    }
```

### 5.2 Expected Outputs

Store expected formatted outputs in `fixtures/expected_outputs/` with clear naming:
- `simple_formatted.adb`
- `with_strings_formatted.adb`
- `complex_operators_formatted.adb`

## 6. Performance Testing

### 6.1 Parsing Performance

```python
def test_parsing_performance():
    """Measure parsing overhead."""
    large_file = generate_large_ada_file(lines=1000)
    
    # Measure regex processing
    start = time.time()
    regex_result = apply_regex_patterns(large_file)
    regex_time = time.time() - start
    
    # Measure parser processing
    start = time.time()
    parser_result = apply_parser_patterns(large_file)
    parser_time = time.time() - start
    
    overhead = parser_time / regex_time
    assert overhead < 2.0, f"Parser overhead {overhead}x exceeds 2x limit"
```

### 6.2 Memory Usage

```python
def test_memory_usage():
    """Test memory consumption with large files."""
    import psutil
    process = psutil.Process()
    
    initial_memory = process.memory_info().rss
    
    # Parse large file
    large_file = generate_large_ada_file(lines=5000)
    parser = AdaParser()
    result = parser.parse(large_file)
    
    peak_memory = process.memory_info().rss
    memory_increase = (peak_memory - initial_memory) / 1024 / 1024  # MB
    
    assert memory_increase < 100, f"Memory increase {memory_increase}MB exceeds limit"
```

## 7. Regression Testing

### 7.1 String Literal Corruption Test

```python
def test_no_string_literal_corruption():
    """Regression test for string literal corruption bug."""
    # This is the exact case that failed with regex
    ada_code = '''
    SQL_Metacharacters : constant String := "';\--/**/";  -- SQL injection chars
    '''
    
    formatter = ParserBasedFormatter(config=default_config())
    result = formatter.format_string(ada_code)
    
    # Verify string content unchanged
    assert "';\--/**/" in result
    assert result.count('--') == 2  # One in string, one in comment
```

### 7.2 Edge Case Collection

Maintain a directory of edge cases that caused bugs:
```
tests/regression/
├── issue_001_string_corruption.adb
├── issue_002_comment_in_string.adb
├── issue_003_long_line_break.adb
└── README.md  # Description of each issue
```

## 8. Continuous Integration

### 8.1 GitHub Actions Workflow

```yaml
name: Parser Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install GNAT
      run: |
        sudo apt-get update
        sudo apt-get install -y gnat
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run unit tests
      run: pytest tests/parser/unit -v
    
    - name: Run integration tests
      run: pytest tests/parser/integration -v
    
    - name: Check coverage
      run: pytest --cov=adafmt.parser --cov-report=xml
```

## 9. Test Execution

### 9.1 Running Tests

```bash
# Run all parser tests
pytest tests/parser -v

# Run specific test category
pytest tests/parser/unit/test_string_safety.py -v

# Run with coverage
pytest tests/parser --cov=adafmt.parser --cov-report=html

# Run performance tests
pytest tests/parser/performance -v --benchmark

# Run only fast tests
pytest tests/parser -v -m "not slow"
```

### 9.2 Test Markers

```python
# Mark slow tests
@pytest.mark.slow
def test_large_file_processing():
    pass

# Mark tests requiring GNAT
@pytest.mark.requires_gnat
def test_gnat_validation():
    pass

# Mark integration tests
@pytest.mark.integration
def test_full_pipeline():
    pass
```

## 10. Debugging Failed Tests

### 10.1 Debugging Parser Issues

```python
def debug_parser_output():
    """Helper to visualize parse tree."""
    ada_code = "procedure Test is begin null; end Test;"
    
    parser = Parser()
    result = parser.parse(ada_code)
    
    if isinstance(result, Success):
        tree = result.value['tree']
        print_parse_tree(tree, indent=0)
```

### 10.2 Debugging Visitor Behavior

```python
class DebugVisitor(FormattingVisitor):
    """Visitor with debug output."""
    
    def visitChildren(self, node):
        print(f"Visiting: {node.__class__.__name__}")
        return super().visitChildren(node)
```

## 11. Success Criteria

### 11.1 Test Coverage
- Unit test coverage > 90%
- Integration test coverage > 80%
- All edge cases have regression tests

### 11.2 Performance
- Parsing overhead < 2x regex processing
- Memory usage < 100MB for typical files
- Processing rate > 100 files/second

### 11.3 Correctness
- Zero string literal corruptions
- All formatted code compiles with GNAT
- All formatting reversible (format twice = format once)

## 12. Maintenance

### 12.1 Adding New Tests
1. Identify formatting rule to test
2. Create minimal Ada example
3. Write unit test for visitor
4. Write integration test for pipeline
5. Add to regression suite if fixing bug

### 12.2 Updating Tests
- Update when Ada 2022 grammar changes
- Update when new GNAT versions released
- Update when new formatting rules added
- Keep performance baselines current