# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Test parser patterns against ALS-formatted Ada code."""

import asyncio
import pytest
import shutil
from pathlib import Path
from typing import Optional, Tuple

try:
    from ada2022_parser import Parser, Success
    from ada2022_parser.generated import Ada2022ParserVisitor
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    class Ada2022ParserVisitor:
        pass

from adafmt.als_client import ALSClient
from adafmt.edits import apply_text_edits


async def format_ada_code_with_als(ada_code: str, project_path: Optional[Path] = None) -> Tuple[str, bool]:
    """Format Ada code using the Ada Language Server.
    
    Args:
        ada_code: The Ada source code to format
        project_path: Optional path to a .gpr project file
        
    Returns:
        Tuple of (formatted_code, success_flag)
    """
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adb', delete=False) as f:
        f.write(ada_code)
        temp_path = Path(f.name)
    
    try:
        # Initialize ALS client
        client = ALSClient(
            project_file=str(project_path) if project_path else None,
            logger=None
        )
        
        # Initialize ALS
        await client.initialize()
        
        # Open the document
        await client._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": temp_path.as_uri(),
                "languageId": "ada",
                "version": 1,
                "text": ada_code
            }
        })
        
        # Request formatting
        result = await client.request_with_timeout({
            "method": "textDocument/formatting",
            "params": {
                "textDocument": {"uri": temp_path.as_uri()},
                "options": {"tabSize": 3, "insertSpaces": True}
            }
        }, timeout=10.0)
        
        # Apply edits if any
        if result and isinstance(result, list) and len(result) > 0:
            formatted = apply_text_edits(ada_code, result)
            return formatted, True
        else:
            # No edits needed
            return ada_code, True
            
    except Exception as e:
        print(f"ALS formatting failed: {e}")
        return ada_code, False
        
    finally:
        # Cleanup
        temp_path.unlink(missing_ok=True)
        await client.shutdown()


@pytest.mark.skipif(
    not PARSER_AVAILABLE or shutil.which("ada_language_server") is None,
    reason="ada2022_parser or Ada Language Server not available"
)
@pytest.mark.integration
class TestParserWithALSFormatting:
    """Test parser-based patterns on ALS-formatted code."""
    
    @pytest.mark.asyncio
    async def test_assignment_spacing_after_als(self):
        """Test that our parser correctly identifies remaining spacing issues after ALS formatting."""
        
        # Original code with spacing issues
        ada_code = """
with Ada.Text_IO; use Ada.Text_IO;
procedure Test is
   X : Integer:=5;          -- No spaces
   Y : Integer := 10;       -- Correct
   Z:Integer:=15;           -- Multiple issues
begin
   X:=X+1;                  -- No spaces
   Y := Y + 1;              -- Correct
end Test;
"""
        
        # Format with ALS
        formatted_code, success = await format_ada_code_with_als(ada_code)
        
        if success:
            print("ALS formatted code:")
            print(formatted_code)
            print("\n" + "="*50 + "\n")
        
        # Now parse and check what ALS fixed
        parser = Parser()
        result = parser.parse(formatted_code)
        
        assert isinstance(result, Success)
        
        # Use our visitor to check spacing
        class AssignmentChecker(Ada2022ParserVisitor):
            def __init__(self, source_lines):
                self.source_lines = source_lines
                self.assignments_found = []
                
            def visitAssignment_statement(self, ctx):
                line_num = ctx.start.line - 1
                line_text = self.source_lines[line_num]
                
                # Check for := in the line
                if ':=' in line_text:
                    # Simple check: count spaces around :=
                    parts = line_text.split(':=')
                    if len(parts) == 2:
                        before = parts[0]
                        after = parts[1]
                        
                        # Check if there's at least one space before and after
                        spaces_before = len(before) - len(before.rstrip())
                        spaces_after = len(after) - len(after.lstrip())
                        
                        self.assignments_found.append({
                            'line': line_num + 1,
                            'text': line_text.strip(),
                            'spaces_before': spaces_before,
                            'spaces_after': spaces_after,
                            'needs_fix': spaces_before < 1 or spaces_after < 1
                        })
                
                return self.visitChildren(ctx)
        
        lines = formatted_code.split('\n')
        visitor = AssignmentChecker(lines)
        visitor.visit(result.value['tree'])
        
        print("Assignment analysis after ALS formatting:")
        for assign in visitor.assignments_found:
            status = "NEEDS FIX" if assign['needs_fix'] else "OK"
            print(f"Line {assign['line']}: {status} - {assign['text']}")
            print(f"  Spaces before ':=': {assign['spaces_before']}")
            print(f"  Spaces after ':=': {assign['spaces_after']}")
    
    @pytest.mark.asyncio
    async def test_comment_spacing_after_als(self):
        """Test comment spacing detection after ALS formatting."""
        
        ada_code = """
--This needs space
-- This is correct  
procedure Test is
   X : Integer;  --Needs space
   Y : String;   -- This is OK
begin
   null; --Another one
end Test;
"""
        
        # Format with ALS
        formatted_code, success = await format_ada_code_with_als(ada_code)
        
        if success:
            print("\nALS formatted comments:")
            print(formatted_code)
            
            # Check what spacing issues remain
            lines = formatted_code.split('\n')
            for i, line in enumerate(lines):
                if '--' in line:
                    # Find the -- position
                    idx = line.find('--')
                    if idx > 0:
                        # End-of-line comment
                        before = line[:idx]
                        after = line[idx+2:]
                        space_before = before.endswith(' ')
                        space_after = after.startswith(' ') if after else True
                        print(f"Line {i+1}: EOL comment - space before: {space_before}, after: {space_after}")
                    else:
                        # Whole-line comment
                        after = line[2:]
                        spaces = len(after) - len(after.lstrip())
                        print(f"Line {i+1}: Whole-line comment - {spaces} spaces after --")


if __name__ == "__main__":
    # Run a simple test
    if PARSER_AVAILABLE and shutil.which("ada_language_server"):
        test = TestParserWithALSFormatting()
        asyncio.run(test.test_assignment_spacing_after_als())
        asyncio.run(test.test_comment_spacing_after_als())
    else:
        print("Parser or ALS not available for testing")