# GNAT Comment Style Rules Summary

Based on empirical testing with `gcc -gnatyy`, here are the exact GNAT style rules for comments:

## 1. Whole-Line Comments
- **MUST** have exactly TWO spaces after `--`
- `--This` → ERROR: "two spaces required"
- `-- This` → ERROR: "space required" (only one space)
- `--  This` → CORRECT (two spaces)
- `--   This` → ACCEPTED (three or more spaces are allowed)

## 2. End-of-Line (Inline) Comments  
- **MUST** have at least ONE space after `--`
- `X : Integer; --comment` → ERROR: "space required"
- `X : Integer; -- comment` → CORRECT (one space)
- `X : Integer; --  comment` → CORRECT (two spaces)
- `X : Integer; --   comment` → CORRECT (three or more spaces)

## 3. Indented Comments
- Follow the same rules as whole-line comments
- Must be indented to match surrounding code
- Still require two spaces after `--` for whole-line comments

## Key Findings

1. **GNAT is stricter than Ada Style Guide examples**: The style guide shows one space, but GNAT requires two for whole-line comments.

2. **Different rules for different comment positions**:
   - Whole-line: minimum 2 spaces required
   - End-of-line: minimum 1 space required

3. **More spaces are always acceptable**: GNAT never complains about having MORE than the minimum spaces.

## Project-Specific Settings

- **Line Length**: 120 characters (instead of default 80)

## Recommended Patterns for adafmt

### Pattern 1: Whole-line comments (`cmt_whole_01`)
```regex
^(\s*)--\s*(\S.*)$
```
Replace with: `$1--  $2` (ensures 2 spaces)

### Pattern 2: End-of-line comments (`comment_eol1`) 
```regex
^(.*\S)\s*--\s*(.*)$
```
Replace with: `$1 -- $2` (ensures 1 space before, 1 space after)

### Important Notes

- Never reduce spacing if it's already more than required
- Preserve ASCII art and special formatting
- Be careful with commented-out code that might have its own `--` markers
- Watch for special markers like TODO, FIXME, NOTE that might need preservation

## Discrepancy with Ada Style Guide

The Ada Style Guide examples show single-spaced comments, but GNAT compiler enforces double-spacing for whole-line comments. We should follow GNAT's rules since:
1. The compiler is the ultimate authority
2. Code must compile without style warnings
3. GNAT style (`-gnatyy`) is the de facto standard in the Ada community