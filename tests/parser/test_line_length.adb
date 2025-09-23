with Ada.Text_IO; use Ada.Text_IO;

procedure Test_Line_Length is
   -- Test long lines with ALS
   X : Integer := 42;
   Very_Long_Variable : Integer:=100;  -- Missing spaces
   
   -- Long assignment that will get even longer with proper spacing
   Result:Integer:=Some_Function(A:=1,B:=2,C:=3,D:=4,E:=5,F:=6,G:=7,H:=8,I:=9,J:=10,K:=11,L:=12,M:=13);
begin
   -- Simple assignments
   X:=X+1;  -- Will become X := X + 1
   
   -- Long line that might exceed limit after spacing fixes
   if X>10 and then Very_Long_Variable<100 and then Result=42 then
      Put_Line("This line is getting close to the limit especially after all operators get proper spacing");
   end if;
end Test_Line_Length;