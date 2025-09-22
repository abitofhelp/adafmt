with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Patterns is
   --  Correct whole-line comment
   X : Integer := 1; -- Correct inline comment
   
   -- =======================================================
   --  Section header
   -- =======================================================
   
   --  ASCII art example:
   --  +-- Root
   --  |   +-- Child 1
   --  |   +-- Child 2
   
begin
   Put_Line ("Testing patterns");
end Test_Patterns;
