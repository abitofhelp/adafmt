with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Comment_Rules is
   --  WHOLE LINE COMMENTS
   --No space after delimiter
   -- One space after delimiter
   --  Two spaces after delimiter
   --   Three spaces after delimiter
   --    Four spaces after delimiter
   
   --  INLINE COMMENTS
   A : Integer := 1; --no space
   B : Integer := 2; -- one space
   C : Integer := 3; --  two spaces
   D : Integer := 4; --   three spaces
   E : Integer := 5; --    four spaces
   
   --  INDENTED COMMENTS
begin
   if True then
      --no space indented
      -- one space indented
      --  two spaces indented
      --   three spaces indented
      null;
   end if;
end Test_Comment_Rules;