with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Improved_Patterns is
   --  TEST: Comments that should NOT change (already correct)
   --  This has two spaces (correct)
   --   This has three spaces (also correct, should not change)
   --    This has four spaces (also correct, should not change)
   
   --  TEST: End-of-line comments that should NOT change
   X : Integer := 1; -- one space (correct)
   Y : Integer := 2; --  two spaces (correct)  
   Z : Integer := 3; --   three spaces (correct)
   
   --  TEST: Comments that SHOULD be fixed
   --This needs fixing (no space)
   -- This needs fixing (one space only)
   
   A : Integer := 4; --needs fixing (no space)
   
   --  TEST: ASCII art that should NOT change
   --  +-----------------------------------------------------------------------+
   --  | This is a box comment that should preserve its formatting             |
   --  +-----------------------------------------------------------------------+
   
   --  Tree structure that should be preserved:
   --  +-- Root
   --  |   +-- Child 1  
   --  |   +-- Child 2
   --  +-- Another Root
   
   -- =========================================================================
   -- This separator line should not change
   -- =========================================================================
   
   --  TEST: Commented code that might have its own comments
   --  procedure Example is
   --  begin
   --     -- This inner comment has one space
   --     null; -- inline in commented code
   --  end Example;
   
begin
   Put_Line ("Testing improved comment patterns");
end Test_Improved_Patterns;