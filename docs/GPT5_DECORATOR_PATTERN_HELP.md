# Help Request: dry-python/returns Decorator Pattern with Custom Error Types

**Context:**
We are using dry-python/returns library for functional error handling in a Python project. We want to use the @impure_safe decorator to avoid boilerplate try/catch blocks, but we're running into issues with custom error types.

**Current Architecture Decision:**
- Use dataclass error types (not exceptions) for better type safety
- Use @impure_safe decorator to automatically convert exceptions to IOResult types
- Want to return IOResult[T, CustomError] where CustomError is a dataclass

**Problem:**
The @impure_safe decorator expects exceptions that inherit from BaseException, but we want to use dataclass error types that don't inherit from Exception.

**Current Code:**

```python
# errors.py
@dataclass(frozen=True)
class FileError(AdafmtError):
    """File operation error."""
    path: Path
    operation: Literal["read", "write", "create", "delete", "stat"]
    original_error: str | None = None
    permission_error: bool = False
    not_found: bool = False

# file_ops.py
def read_text(
    path: Union[str, Path],
    encoding: str = 'utf-8',
    errors: str = 'strict'
) -> IOResult[str, FileError]:
    """Read file with explicit error handling."""
    path = Path(path)
    
    @impure_safe
    def _read_with_custom_errors() -> str:
        try:
            return path.read_text(encoding=encoding, errors=errors)
        except Exception as exc:
            # This fails because FileError is not an Exception
            raise _map_read_error(path)(exc)  # Returns FileError dataclass
    
    return _read_with_custom_errors()
```

**Error:**
```
TypeError: exceptions must derive from BaseException
```

**Questions for GPT5:**

1. What is the correct pattern for using @impure_safe with custom dataclass error types that don't inherit from Exception?

2. Should we:
   a) Create a wrapper exception class that contains our dataclass and unwrap it after?
   b) Use a different decorator pattern?
   c) Abandon decorators and use explicit try/catch with IOSuccess/IOFailure?
   d) Make our error types inherit from Exception (but this seems against the functional programming philosophy)?

3. The dry-python/returns documentation shows examples with standard exceptions but not with custom dataclass errors. Is there a recommended pattern for this use case?

4. We noticed that @impure_safe directly stores the caught exception in IOFailure. How can we transform that exception to our custom dataclass error type while still using the decorator pattern?

**What We Want:**
- Use @impure_safe to avoid boilerplate
- Return IOResult[str, FileError] where FileError is a dataclass
- Map different exceptions (FileNotFoundError, PermissionError, etc.) to specific FileError instances with appropriate fields set

**Current Workaround Attempt:**
We tried creating an ErrorWrapper exception that contains the dataclass, but this feels hacky and requires unwrapping later.

Please provide the idiomatic dry-python/returns solution for this pattern.