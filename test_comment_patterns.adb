--  =============================================================================
--  Test_Comment_Patterns - GNAT Style Comment Validation
--  =============================================================================
--  Copyright (c) 2025 A Bit of Help, Inc.
--  SPDX-License-Identifier: MIT
--
--  Purpose:
--    This file tests various comment patterns to validate GNAT style rules
--    using the -gnatyy compiler switch.

with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Comment_Patterns is

   --  Test 1: Standard whole-line comments (should have 2 spaces)
   --This is wrong (no space)
   -- This is wrong (one space)  
   --  This is correct (two spaces)
   --   This is wrong (three spaces)
   
   X : Integer := 42; -- inline comment wrong (one space)
   Y : Integer := 42; --  inline comment correct (two spaces)
   Z : Integer := 42; --   inline comment wrong (three spaces)
   
   --  Test 2: Block comments
   --  ==========================================================================
   --  This is a block comment header
   --  ==========================================================================
   
   --  Test 3: ASCII art in comments
   --  Tree structure:
   --  +-- Root
   --  |   +-- Child 1
   --  |   +-- Child 2
   --  +-- Another Root
   
   --  Test 4: Commented-out code
   --  procedure Old_Code is
   --  begin
   --     null;
   --  end Old_Code;
   
   --  Test 5: Special markers
   --  TODO: Implement this feature
   --  FIXME: This needs attention
   --  NOTE: Important information here
   
   --  Test 6: Separator lines
   --  --------------------------------------------------------------------------
   
   --  Test 7: Box comments
   --  +------------------------------------------------------------------------+
   --  | This is a box comment                                                  |
   --  +------------------------------------------------------------------------+

begin
   --  Test 8: Comments in code blocks
   Put_Line ("Testing comment patterns");
   
   --  Test 9: Multi-line explanatory comments
   --  This is a longer comment that explains something complex about the
   --  implementation. It spans multiple lines and each line should have
   --  exactly two spaces after the comment delimiter.
   
   if True then
      --  Test 10: Indented comments (should follow code indentation)
      Put_Line ("Indented code");
      --  The comment above should be at the same indentation level
   end if;
   
   --  Test 11: Empty comment lines in blocks
   --  First line of comment block
   --
   --  Third line after empty comment line
   
end Test_Comment_Patterns;