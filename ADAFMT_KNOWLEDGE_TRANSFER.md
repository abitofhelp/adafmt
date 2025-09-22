# adafmt Knowledge Transfer Document

**Purpose:** This document captures the essential knowledge, design decisions, implementation details, and lessons learned from the Python-based adafmt project to inform the development of the new Go-based unified tool.

## Executive Summary

adafmt is a Python-based Ada language formatter that integrates with the Ada Language Server (ALS) to format Ada source code. It implements parallel processing, pattern-based post-formatting, and comprehensive error handling. The project is being superseded by a new Go-based tool that will combine formatting functionality with semantic operations using an ANTLR-based Ada 2022 parser.

## Project Overview

### What adafmt Does Well

1. **ALS Integration Excellence**
   - Robust JSON-RPC over stdio implementation
   - Proper initialization sequence handling
   - Graceful error recovery with retry logic
   - Comprehensive debug logging for troubleshooting
   - Health checks and readiness probing

2. **Parallel Processing Architecture**
   - Clean async worker pool implementation
   - Bounded queues to prevent memory exhaustion
   - Thread-safe metrics collection
   - Health monitoring with 30-second timeouts
   - Graceful shutdown with signal handling

3. **User Experience**
   - Adaptive TTY interface (pretty/basic/plain modes)
   - Real-time progress tracking
   - Color-coded status indicators
   - Comprehensive error messages with actionable guidance
   - **TTY output is informative without being overwhelming**

4. **Logging Excellence**
   - **Always-on JSONL structured logging (a standout feature)**
   - **Well-balanced verbosity - helpful without spam**
   - **Separate log files for different concerns**
   - **Debug modes available but not required for normal use**
   - Timestamped files prevent overwrites

5. **Production-Ready Features**
   - Atomic file writes (temp + rename)
   - Comprehensive metrics collection
   - Signal handling (SIGTERM, SIGINT)
   - File size limits (1MB default)

6. **Pattern System Design**
   - JSON-based configuration
   - Timeout protection against ReDoS
   - Detailed debug logging
   - Category-based organization

### What adafmt Fails to Do Well

1. **The Fatal Flaw: Regex-Based Pattern System**
   - Cannot distinguish between code and string literals
   - Corrupts string literals containing pattern-like content
   - Example: `constant String := "--"` becomes `constant String := " -- "`
   - No amount of regex complexity can solve this context-sensitivity issue

2. **Platform Limitations**
   - Signal-based timeouts only work on Unix-like systems
   - Falls back to less reliable threading.Timer on Windows

3. **ALS Limitations**
   - ALS formatting is incomplete (no comment spacing, etc.)
   - Pattern system was created to fill gaps but introduced new problems
   - No semantic understanding of code structure

4. **Complexity Issues**
   - File processor has complex parallel/non-parallel code paths
   - Worker pool consumer pattern is over-engineered
   - Pattern validation is insufficient

## Key Technical Components

### 1. ALS Client Implementation

The ALS client is one of the strongest parts of adafmt:

```python
# Key insights:
- Use asyncio for non-blocking I/O
- Implement proper JSON-RPC 2.0 protocol
- Handle partial messages and buffering correctly
- Implement request/response correlation with IDs
- Proper initialization sequence is critical
```

**Important sequences:**
1. Initialize request with rootUri and capabilities
2. Wait for initialized notification
3. Send didOpen notifications for files
4. Use textDocument/formatting requests
5. Clean shutdown with proper cleanup

### 2. Parallel Processing Architecture

```python
# Architecture:
- WorkerPool manages N async workers
- Queue-based work distribution
- Each worker handles: pattern application + file writing
- Thread-safe metrics collection
- Health monitoring prevents stuck workers
```

**Key design decisions:**
- Queue size: 10 items (not 100) to limit memory
- Default workers: 1 (ALS is the bottleneck)
- Buffer size: 8KB for file I/O
- Timeout: 30 seconds for health checks

### 3. Pattern System (The Problem Child)

The pattern system was designed to fix ALS formatting gaps:
- Comment spacing (GNAT requires 2 spaces after --)
- Operator spacing (:=, =>, ..)
- Delimiter spacing (commas, semicolons)

**Why it failed:**
- Regex cannot understand Ada syntax context
- String literals are indistinguishable from code
- Even sophisticated patterns with quote-counting fail
- The solution requires actual parsing

### 4. Logging and Diagnostics

adafmt implements comprehensive logging:
- Main log: General operations
- Pattern log: Pattern applications
- Stderr log: Captured stderr from ALS
- Debug logs: Optional detailed traces

All logs use JSONL format for structured data.

## Lessons Learned

### 1. **Regex Patterns Are Insufficient**
The fundamental lesson: **You cannot format a context-sensitive language with context-free patterns**. String literals, character literals, comments, and code require different handling that only a parser can provide.

### 2. **ALS Integration Patterns**
- Always implement health checks
- Handle initialization sequence carefully
- Implement proper cleanup/shutdown
- Log everything for debugging
- Retry transient errors with backoff

### 3. **Parallel Processing Insights**
- ALS is single-threaded, so multiple workers don't help ALS operations
- Parallel processing helps with pattern application and file I/O
- Queue bounds are critical to prevent memory issues
- Health monitoring prevents zombie workers

### 4. **Error Handling Philosophy**
- Distinguish between recoverable and fatal errors
- Provide actionable error messages
- Continue processing other files on single-file errors
- Collect and report all errors at the end

## Important Architectural Differences

### UI/UX Approaches: adafmt vs adafix

**adafmt (TTY-based):**
- Adaptive TTY interface with three modes (pretty/basic/plain)
- Progress bars and real-time status updates
- Color-coded output for different file states
- Runs in terminal with no GUI dependencies
- Excellent balance of information without overwhelming

**adafix (Graphical Interface):**
- Has a graphical user interface component
- Details to be discovered during integration
- May offer richer interaction possibilities
- Could have different progress/status reporting

**Integration Decision Point:**
- Evaluate both approaches during integration
- May adopt adafmt's TTY style for consistency with CLI tools
- May preserve adafix's GUI for richer user interaction
- Or potentially support both modes
- Decision will be made based on reference implementation goals

### Error Handling: adafmt vs adafix

**adafmt (Python Exception-Based):**
- Uses Python's exception model
- Exceptions can propagate up the call stack
- Try/except blocks at various levels
- Some exceptions escape to top level

**adafix (Go Functional Error Pattern):**
- **Strict functional programming error handling**
- **ALL exceptions caught locally and converted to errors**
- **No exceptions ever escape the method where they occur**
- **Every function that can fail returns (result, error)**
- **Errors bubble up through return values, not exceptions**

Example of the adafix pattern:
```go
func ProcessFile(path string) (*Result, error) {
    // ANY exception/panic here is caught
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic in ProcessFile: %v", r)
        }
    }()
    
    // Normal error handling
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("reading file: %w", err)
    }
    
    return result, nil
}
```

This is a **critical architectural difference** to maintain in the new project.

## Migration Recommendations

### 1. **Preserve from adafmt:**
- **Logging excellence** - The balance and structure are exemplary
- **TTY output design** - Informative without being overwhelming
- ALS client implementation patterns (translate to Go)
- Parallel processing architecture (adapt for Go)
- Comprehensive error handling approach
- UI/UX design (progress tracking, status codes)
- Separate log files for different concerns
- JSONL structured logging format

### 2. **Replace with Parser-Based Approach:**
- Pattern system → ANTLR visitor patterns
- Regex matching → AST node identification
- String escaping → AST node types
- Pattern categories → Visitor methods

### 3. **Architecture Suggestions:**
```go
// Unified command architecture
type Command interface {
    Execute(ctx context.Context, files []string) error
}

// Format command uses parser
type FormatCommand struct {
    parser  *Parser
    als     *ALSClient
    workers *WorkerPool
}

// Visitor for formatting rules
type FormatVisitor struct {
    BaseVisitor
    rules FormatRules
}
```

### 4. **Testing Strategy:**
- Port integration tests (valuable)
- Create AST-based unit tests
- Test with Ada 2022 language tests
- Validate against GNAT compiler

## Performance Benchmarks

From recent runs on abohlib codebase:
- 1 worker: 80 seconds
- 2 workers: 19.3 seconds
- 3 workers: 19.2 seconds
- 4 workers: 19.3 seconds

Conclusion: ALS is the bottleneck; 2 workers are optimal.

## Deprecation Notices

### For adafmt README:
```markdown
## Development Status: Discontinued

**Reason:** Running into context parsing issues that exceeded the limits of regex.

Development has moved to a new unified Go-based tool that uses an ANTLR-based Ada 2022 parser for accurate, context-aware formatting.
```

### For adafix README:
```markdown
## Development Status: Discontinued  

**Reason:** To take advantage of ALS architectural improvements from the adafmt project.

Development has moved to a new unified tool that combines the parser capabilities of adafix with the enhanced ALS integration from adafmt.
```

## Critical Mission for adatool

### Reference Implementation Status

**adatool is intended to be THE reference implementation of an Ada tool using the reference Ada 2022 grammar.** This elevates it beyond a mere utility to:

1. **Engineering Excellence is Non-Negotiable**
   - Every line of code must exemplify best practices
   - No shortcuts, no hacks, no "good enough"
   - If a simple solution isn't excellent, choose the complex but correct one
   - Quality over delivery speed, always

2. **Documentation as First-Class Citizen**
   - Documentation must be comprehensive and current
   - **Requirements traceability to source code** (you will see this in action)
   - Every design decision documented
   - API documentation for all public interfaces
   - Architecture decisions recorded
   - Each source file traces back to specific requirements
   - Requirements changes must update both code and docs

3. **Best Practices Implementation**
   - Each requirement implemented using industry best practices
   - Patterns chosen for correctness, not convenience
   - Performance optimizations only after correctness proven
   - Security considerations in every component

4. **Reference Quality Standards**
   - Code others will study to learn "how it should be done"
   - Suitable for presentation at conferences
   - Worthy of academic papers
   - Sets the standard for Ada tooling

## Final Recommendations

1. **Start with adafix as the base** - It already follows these principles
2. **Port ALS client carefully** - Maintain the excellence while translating
3. **Design for correctness first** - Performance and features come after
4. **Document everything** - Future developers will study this code
5. **Test comprehensively** - Reference implementations must be bulletproof

The journey from adafmt to adatool represents an evolution from "solving a problem" to "setting the standard" - a worthy mission for the Ada community.

### Remember

When faced with architectural decisions in adatool:
- Choose the **correct** solution over the easy one
- Choose the **maintainable** solution over the clever one
- Choose the **documented** solution over the obvious one
- Choose the **testable** solution over the simple one

This is not just a tool - it's a reference implementation that will influence how others build Ada tools for years to come.

---
*Document prepared for knowledge transfer to the new project's Claude assistant.*