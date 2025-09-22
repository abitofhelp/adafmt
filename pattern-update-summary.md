# Pattern Update Summary

## Changes Made

### 1. Updated Comment Patterns

We replaced the aggressive comment patterns with more targeted ones based on GNAT compiler requirements:

#### Removed Patterns:
- **`cmt_whole_01`** - Changed ALL comments to exactly 2 spaces
- **`comment_eol1`** - Forced 2 spaces after `--` for inline comments

#### Added Patterns:
- **`cmt_whole_02`** - Only fixes whole-line comments with 0-1 spaces (preserves 2+ spaces)
- **`comment_eol2`** - Only fixes inline comments with NO space after `--` (preserves 1+ spaces)
- **`cmt_sep_line`** - Fixes separator lines like `-- =====` to have 2 spaces

### 2. Pattern Names

All pattern names must be exactly 12 characters (regex: `^[a-z0-9\-_]{12}$`), so we used:
- `cmt_whole_02` instead of `cmt_whole_01_v2`
- `comment_eol2` instead of `comment_eol1_v2`
- `cmt_sep_line` instead of `separator_lines`

### 3. Regex Syntax

Fixed replacement syntax from JavaScript-style (`$1`) to Python-style (`\g<1>`):
- `$1--  $2` → `\g<1>--  \g<2>`
- `$1 -- $2` → `\g<1> -- \g<2>`
- `$1--  $3` → `\g<1>--  \g<3>`

### 4. GNAT Compliance

Based on empirical testing with `gcc -gnatyy -gnatyM120`:
- Whole-line comments: MUST have 2+ spaces after `--`
- Inline comments: MUST have 1+ space after `--`
- More spaces than required are always acceptable

### 5. Test Updates

- Updated `adafmt_patterns.json` with new patterns
- Synchronized `tests/patterns/test_patterns.json`
- Created new test file `test_individual_patterns_updated.py`
- Updated existing tests to use new pattern names
- Fixed integration test expectations

## Benefits

1. **Less Aggressive**: Only fixes actual GNAT violations
2. **Preserves Formatting**: Won't change valid comment spacing
3. **ASCII Art Safe**: Won't break documentation diagrams
4. **GNAT Compliant**: Output passes `-gnatyy` style checks

## Next Steps

1. Run the test suite to ensure all tests pass
2. Test against the abohlib codebase with the new patterns
3. Verify the formatting is less disruptive while still fixing violations