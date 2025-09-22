# Comment Pattern Changes

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Released

This document describes the changes made to adafmt's comment formatting patterns to fix aggressive reformatting issues.

## Problem

The original `cmt_whole_01` pattern was too aggressive, changing all comments from 3+ spaces to exactly 2 spaces after `--`. This broke ASCII art, documentation trees, and other carefully formatted comments in Ada source files.

## Solution

Based on empirical testing with the GNAT compiler using `-gnatyy -gnatyM120`, we determined the exact style requirements:
- Whole-line comments: minimum 2 spaces after `--`
- End-of-line comments: minimum 1 space after `--`

New patterns were created that only fix style violations, preserving already-correct formatting.

## Changes Made

### 1. Updated Comment Patterns

**Old Pattern (`cmt_whole_01`):**
- Changed ALL comments to exactly 2 spaces after `--`
- Broke ASCII art and documentation

**New Patterns:**
- `cmt_whole_02`: Only fixes whole-line comments with 0-1 spaces (preserves 2+ spaces)
- `comment_eol2`: Only fixes inline comments with no space after `--`
- `cmt_sep_line`: Ensures separator lines like `-- ======` have 2 spaces

### 2. Pattern Names

All pattern names were updated to exactly 12 characters to match the validation regex:
- `cmt_whole_02` (was `cmt_whole_01_v2`)
- `comment_eol2` (was `comment_eol_v2`)
- `cmt_sep_line` (was `cmt_separator_lines`)

### 3. Regex Syntax

Fixed Python regex replacement syntax:
- Changed `$1`, `$2` to `\g<1>`, `\g<2>`

## Testing

All patterns were tested against:
1. GNAT compiler with `-gnatyy -gnatyM120` flags
2. The abohlib Ada codebase
3. Comprehensive unit and integration tests

The new patterns correctly preserve:
- ASCII art and tree structures
- Documentation formatting
- Comments with 2+ spaces
- Inline comment formatting

## Files Modified

1. `/adafmt_patterns.json` - Updated with new comment patterns
2. `/tests/patterns/test_patterns.json` - Synchronized test patterns
3. `/tests/patterns/unit/test_individual_patterns_updated.py` - New tests for updated patterns
4. `/tests/patterns/integration/test_adafmt_integration.py` - Fixed integration test expectations
5. `/gnat-comment-style-rules.md` - Documentation of GNAT style requirements