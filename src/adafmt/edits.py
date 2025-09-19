# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Language Server Protocol (LSP) text edit utilities.

This module provides functions for applying text edits returned by the
Ada Language Server. It handles the LSP TextEdit format which uses
line/character positions rather than byte offsets.

The main functionality includes:
    - Converting between line/character positions and byte offsets
    - Applying multiple text edits to a document
    - Generating unified diffs for displaying changes

LSP position coordinates:
    - Lines are 0-indexed
    - Characters are 0-indexed UTF-16 code units within a line
    - Positions are between characters (like cursor positions)
"""

from __future__ import annotations

from typing import List, Dict, Any
import difflib

def _line_offsets(s: str) -> List[int]:
    """Calculate byte offsets for the start of each line in a string.
    
    This creates an index allowing fast conversion from line numbers
    to byte positions in the string.
    
    Args:
        s: The text content to analyze
        
    Returns:
        List of byte offsets where each line starts. The first element
        is always 0 (start of string), and there's one extra element
        at the end representing the total length.
        
    Example:
        >>> _line_offsets("Hello\nWorld\n")
        [0, 6, 12]  # "Hello\n" starts at 0, "World\n" at 6, EOF at 12
    """
    offs = [0]
    i = 0
    for line in s.splitlines(True):  # keepends=True preserves newlines
        i += len(line)
        offs.append(i)
    return offs

def _to_offset(s: str, line: int, character: int) -> int:
    """Convert LSP line/character position to byte offset.
    
    LSP uses line and character positions, but Python string slicing
    needs byte offsets. This function performs the conversion.
    
    Args:
        s: The text content
        line: 0-based line number
        character: 0-based character position within the line
        
    Returns:
        Byte offset in the string
        
    Note:
        - Line numbers are clamped to valid range to handle edge cases
        - Character positions are NOT validated/clamped, assuming the
          LSP server provides valid positions
        - This assumes UTF-8 encoding where character = byte for ASCII
    """
    offs = _line_offsets(s)
    line = max(0, min(line, len(offs)-1))
    return offs[line] + character

def apply_text_edits(original: str, edits: List[Dict[str, Any]]) -> str:
    """Apply LSP TextEdit list to original text.
    
    Processes a list of text edits as returned by textDocument/formatting
    or other LSP methods. Edits are applied in reverse order (last to first)
    to avoid position shifting issues.
    
    Args:
        original: The original text content
        edits: List of LSP TextEdit objects, each containing:
               - range: {start: {line, character}, end: {line, character}}
               - newText: Replacement text (can be empty for deletions)
               
    Returns:
        The text after applying all edits
        
    Example:
        >>> original = "Hello World"
        >>> edits = [{
        ...     "range": {
        ...         "start": {"line": 0, "character": 6},
        ...         "end": {"line": 0, "character": 11}
        ...     },
        ...     "newText": "Ada"
        ... }]
        >>> apply_text_edits(original, edits)
        'Hello Ada'
        
    Note:
        The algorithm sorts edits by start position (descending) and applies
        them back-to-front. This ensures that earlier edits don't invalidate
        the positions of later edits.
    """
    if not edits:
        return original
    
    # Convert LSP positions to byte offsets and collect edit operations
    spans = []
    for e in edits:
        try:
            r = e["range"]
            s_off = _to_offset(original, r["start"]["line"], r["start"]["character"])
            e_off = _to_offset(original, r["end"]["line"], r["end"]["character"])
            spans.append((s_off, e_off, e.get("newText", "")))
        except (KeyError, TypeError) as ex:
            # Handle malformed edit objects from ALS
            raise TypeError(f"Invalid edit format from ALS: {e!r}") from ex
    
    # Sort by start offset descending to apply from end to beginning
    spans.sort(key=lambda t: (t[0], t[1]), reverse=True)

    out = original
    for s_off, e_off, repl in spans:
        out = out[:s_off] + repl + out[e_off:]
    return out

def unified_diff(a: str, b: str, path: str) -> str:
    """Generate a unified diff between two versions of a file.
    
    Creates a standard unified diff format showing the changes between
    the original and modified versions of a file. This is the same
    format used by 'diff -u' and git.
    
    Args:
        a: Original file content
        b: Modified file content  
        path: File path to show in the diff header
        
    Returns:
        Unified diff as a string, empty if no changes
        
    Example output:
        --- example.ads
        +++ example.ads
        @@ -1,3 +1,3 @@
         package Example is
        -   procedure Hello;
        +   procedure Hello_World;
         end Example;
         
    Note:
        - Uses 3 lines of context around changes (n=3)
        - Preserves line endings from the input strings
        - Returns empty string if contents are identical
    """
    return "".join(difflib.unified_diff(
        a.splitlines(True), b.splitlines(True),
        fromfile=path, tofile=path, n=3
    ))
