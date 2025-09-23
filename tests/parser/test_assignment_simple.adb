-- Simple test file for assignment spacing
procedure Test_Assignment_Simple is
   X:=5;  -- Should become X := 5;
   Y:=10; -- Should become Y := 10;
   
   -- String literal protection test
   Op : String := ":=";  -- The := inside quotes should NOT change
   
   -- Already correct
   Z := 15;  -- Should stay as is
begin
   X:=X+1;     -- Should become X := X+1; (only assignment fixed for now)
   Result:=X;  -- Should become Result := X;
end Test_Assignment_Simple;