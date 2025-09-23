# Software Requirements Specification: Parser-Based Architecture

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Draft

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for the parser-based architecture of adafmt. The new architecture addresses critical limitations in the regex-based approach by providing context-aware formatting using an Ada 2022 parser.

### 1.2 Scope
The parser-based architecture extends adafmt's capabilities by:
- Preventing ALS-induced string literal corruption
- Providing safe, context-aware formatting transformations
- Adding GNAT compiler validation for correctness
- Supporting pre-ALS and post-ALS formatting phases

### 1.3 Definitions and Acronyms
- **AST**: Abstract Syntax Tree
- **ALS**: Ada Language Server
- **ANTLR**: ANother Tool for Language Recognition
- **GNAT**: GNU Ada Compiler
- **Pre-ALS**: Formatting phase before ALS processing
- **Post-ALS**: Formatting phase after ALS processing
- **Visitor Pattern**: Design pattern for traversing and modifying AST nodes

### 1.4 Reference Grammar
This project uses the Ada 2022 ANTLR reference grammar developed as a separate project. The grammar provides:
- Complete Ada 2022 language coverage
- ANTLR-generated parser with Python target
- Visitor pattern support for AST traversal
- Accurate parsing matching the Ada Reference Manual

## 2. Overall Description

### 2.1 Product Perspective
The parser-based architecture integrates with the existing adafmt infrastructure while replacing the regex-based pattern matching with AST visitor patterns.

### 2.2 Product Functions
1. **Parse Ada source files** into AST representation
2. **Apply Pre-ALS transformations** to prevent ALS bugs
3. **Orchestrate ALS formatting** on prepared code
4. **Apply Post-ALS transformations** to fix remaining issues
5. **Validate results** with GNAT compiler
6. **Preserve string literal integrity** throughout the process

### 2.3 User Characteristics
The system is designed for Ada developers who need reliable, automated code formatting that:
- Preserves code correctness
- Handles complex Ada constructs safely
- Integrates with existing toolchains
- Provides predictable, consistent results

### 2.4 Constraints
1. **Parser Dependency**: Requires ada2022_parser Python package (generated from the Ada 2022 ANTLR reference grammar)
2. **GNAT Availability**: Requires gcc/gnat compiler for validation
3. **Performance**: Parsing adds overhead compared to regex
4. **Memory**: AST representation requires more memory than text processing

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Parser Integration
- **REQ-PARSER-001**: System SHALL parse Ada source files using ada2022_parser
- **REQ-PARSER-002**: System SHALL handle parse failures using Result[AST, ParseError] types
- **REQ-PARSER-003**: System SHALL preserve original file on parse failure
- **REQ-PARSER-004**: System SHALL support Ada 2022 language features
- **REQ-PARSER-005**: Parser functions SHALL NOT throw exceptions

#### 3.1.2 Pre-ALS Processing
- **REQ-PRE-001**: System SHALL detect long string literals exceeding line length
- **REQ-PRE-002**: System SHALL break long strings using Ada concatenation syntax
- **REQ-PRE-003**: System SHALL detect preprocessing directives
- **REQ-PRE-004**: System SHALL validate syntax before ALS processing
- **REQ-PRE-005**: System SHALL skip files with preprocessing directives

#### 3.1.3 ALS Integration
- **REQ-ALS-001**: System SHALL pass pre-processed code to ALS
- **REQ-ALS-002**: System SHALL apply ALS formatting edits
- **REQ-ALS-003**: System SHALL handle ALS failures gracefully
- **REQ-ALS-004**: System SHALL preserve pre-ALS modifications

#### 3.1.4 Post-ALS Processing
- **REQ-POST-001**: System SHALL fix comment spacing (ensure " -- " format)
- **REQ-POST-002**: System SHALL fix assignment operator spacing (":=")
- **REQ-POST-003**: System SHALL fix range operator spacing ("..")
- **REQ-POST-004**: System SHALL fix arrow operator spacing ("=>")
- **REQ-POST-005**: System SHALL support vertical alignment (optional)
- **REQ-POST-006**: System SHALL support casing dictionaries
- **REQ-POST-007**: System SHALL NOT modify content inside string literals

#### 3.1.5 GNAT Validation
- **REQ-GNAT-001**: System SHALL validate formatted code with GNAT
- **REQ-GNAT-002**: System SHALL use command: `gcc -c -gnatc -gnatf -gnat2022 -gnatwe`
- **REQ-GNAT-003**: System SHALL reject files that fail validation
- **REQ-GNAT-004**: System SHALL log GNAT error messages
- **REQ-GNAT-005**: System SHALL support --no-gnat-validation flag

#### 3.1.6 String Literal Safety
- **REQ-STRING-001**: System SHALL identify all string literal regions
- **REQ-STRING-002**: System SHALL protect string literals from modifications
- **REQ-STRING-003**: System SHALL handle escaped quotes correctly
- **REQ-STRING-004**: System SHALL handle multi-line concatenated strings

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance
- **REQ-PERF-001**: Parsing overhead SHALL not exceed 2x regex processing time
- **REQ-PERF-002**: System SHALL support parallel file processing
- **REQ-PERF-003**: System SHALL cache parsed ASTs when possible
- **REQ-PERF-004**: System SHALL handle files up to 100KB efficiently

#### 3.2.2 Reliability  
- **REQ-REL-001**: System SHALL never corrupt valid Ada code
- **REQ-REL-002**: System SHALL preserve semantic meaning
- **REQ-REL-003**: System SHALL handle all Ada 2022 constructs
- **REQ-REL-004**: System SHALL fail safely with clear error messages
- **REQ-REL-005**: All errors SHALL be explicitly typed and documented
- **REQ-REL-006**: No exceptions SHALL cross function boundaries

#### 3.2.3 Maintainability
- **REQ-MAINT-001**: Visitor patterns SHALL be clearly documented
- **REQ-MAINT-002**: New patterns SHALL be easy to add
- **REQ-MAINT-003**: Pattern logic SHALL be testable in isolation
- **REQ-MAINT-004**: System SHALL provide debug logging

#### 3.2.4 Compatibility
- **REQ-COMPAT-001**: System SHALL maintain existing CLI interface
- **REQ-COMPAT-002**: System SHALL support existing configuration
- **REQ-COMPAT-003**: System SHALL work with existing worker pool
- **REQ-COMPAT-004**: System SHALL produce same output format

### 3.3 Error Handling Requirements

#### 3.3.1 Functional Error Handling
- **REQ-ERR-001**: System SHALL use dry-python/returns Result/IOResult types exclusively
- **REQ-ERR-002**: All functions that can fail SHALL return Result[T, E] types
- **REQ-ERR-003**: System SHALL define specific error types for each domain:
  - FileError for file operations
  - ParseError for parsing failures
  - ALSError for ALS communication issues
  - ValidationError for GNAT validation failures
  - ConcurrencyError for worker pool issues
- **REQ-ERR-004**: Exceptions SHALL be caught at the point of origin
- **REQ-ERR-005**: Error messages SHALL include full context and path information

#### 3.3.2 Concurrency Error Handling
- **REQ-ERR-006**: Worker pool SHALL handle timeout errors explicitly
- **REQ-ERR-007**: Concurrent operations SHALL use FutureResult for async error handling
- **REQ-ERR-008**: Failed workers SHALL NOT crash the entire process
- **REQ-ERR-009**: System SHALL track and report per-worker error rates

#### 3.3.3 Error Recovery
- **REQ-ERR-010**: System SHALL continue processing remaining files on error
- **REQ-ERR-011**: System SHALL support retry logic for transient failures
- **REQ-ERR-012**: System SHALL implement circuit breaker for ALS failures
- **REQ-ERR-013**: System SHALL provide default values where appropriate

### 3.4 Interface Requirements

#### 3.4.1 Command Line Interface
- **REQ-CLI-001**: System SHALL support --no-pre-als flag
- **REQ-CLI-002**: System SHALL support --no-post-als flag
- **REQ-CLI-003**: System SHALL support --no-gnat-validation flag
- **REQ-CLI-004**: System SHALL support --casing-dictionary flag
- **REQ-CLI-005**: System SHALL deprecate --no-patterns flag

#### 3.4.2 Configuration Interface
- **REQ-CONFIG-001**: System SHALL support rule configuration files
- **REQ-CONFIG-002**: System SHALL allow rule enable/disable
- **REQ-CONFIG-003**: System SHALL support rule parameters
- **REQ-CONFIG-004**: System SHALL validate configuration

## 4. Validation Requirements

### 4.1 Test Requirements
- **REQ-TEST-001**: Each visitor pattern SHALL have unit tests
- **REQ-TEST-002**: String literal protection SHALL be tested extensively
- **REQ-TEST-003**: GNAT validation SHALL be tested with invalid code
- **REQ-TEST-004**: Integration tests SHALL cover full workflow

### 4.2 Acceptance Criteria
1. No string literal corruption in any test case
2. All Post-ALS patterns produce valid Ada code
3. GNAT validation catches all syntax/semantic errors
4. Performance overhead is acceptable (<2x)
5. Existing functionality remains intact

## 5. Appendices

### 5.1 Example Visitor Pattern
```python
class AssignmentSpacingVisitor(Ada2022ParserVisitor):
    def visitObject_declaration(self, ctx):
        # Fix := spacing in declarations
        return self.fix_assignment_spacing(ctx)
```

### 5.2 GNAT Validation Command
```bash
gcc -c -gnatc -gnatf -gnat2022 -gnatwe -o /tmp/test.ali file.adb
```

### 5.3 Pre-ALS String Breaking Example
```ada
-- Before Pre-ALS
Message : String := "This very long string exceeds line limit";

-- After Pre-ALS
Message : String := 
   "This very long string " &
   "exceeds line limit";
```