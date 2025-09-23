-- Test file for assignment operator spacing patterns
with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Assignment_Spacing is
   -- Variable declarations with various spacing issues
   X : Integer:=5;                    -- No spaces around :=
   Y : Integer :=10;                  -- No space after :=
   Z : Integer:= 15;                  -- No space before :=
   W : Integer := 20;                 -- Correct spacing
   V : Integer  :=  25;               -- Extra spaces (acceptable)
   
   -- Constants
   Max_Value:constant Integer:=100;   -- Multiple spacing issues
   Min_Value : constant Integer := 0; -- Correct spacing
   
   -- String literals containing :=
   Op1 : String := ":=";              -- String contains assignment op
   Op2 : String:=":= is assignment";  -- Assignment needs fix, string OK
   Msg : String := "X:=5 is bad";     -- Assignment OK, string ignored
   
   -- Complex initializations
   Data:array(1..10)of Integer:=(others=>0);  -- Multiple issues
   
   -- Record type with default values
   type Point is record
      X:Integer:=0;                   -- Needs spacing fix
      Y : Integer := 0;               -- Correct spacing
   end record;
   
   Origin:Point:=(X=>0,Y=>0);         -- Assignment needs fix
   
begin
   -- Assignment statements
   X:=X+1;                            -- No spaces around :=
   Y := Y + 1;                        -- Correct spacing
   Z  :=  Z  +  1;                    -- Extra spaces (acceptable)
   
   -- Assignments in expressions
   if X:=10 then                      -- Assignment needs fix
      Put_Line("X is 10");
   end if;
   
   -- Multiple assignments (if supported)
   X:=Y; Y:=Z; Z:=W;                  -- All need fixes
   
   -- String output
   Put_Line("Assignment op: " & Op1);
   Put_Line(Msg);
end Test_Assignment_Spacing;