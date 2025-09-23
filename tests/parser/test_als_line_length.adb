-- Test file to see how ALS handles long lines
with Ada.Text_IO; use Ada.Text_IO;

procedure Test_ALS_Line_Length is
   -- Test 1: Very long variable declaration
   Very_Long_Variable_Name_That_Exceeds_Normal_Limits : Integer := 42;
   
   -- Test 2: Long assignment without spaces (to test if ALS adds spaces and breaks lines)
   Another_Variable:Integer:=Very_Long_Function_Call_With_Many_Parameters(First_Parameter:=1,Second_Parameter:=2,Third:=3);
   
   -- Test 3: Long boolean expression
   Status:Boolean:=Ada.Directories.Exists(Full_Path_Name)and then not Ada.Directories.Kind(Full_Path_Name)=Ada.Directories.Directory;
   
   -- Test 4: Long array aggregate
   Data:array(1..100)of Integer:=(1..50=>Default_Value,51..75=>Another_Value,76..100=>Yet_Another_Default_Value_Here);
   
   -- Test 5: Long procedure call with many parameters
   Result : Integer;
begin
   -- Test 6: Long if statement
   if Very_Long_Condition_Check(Parameter1)and then Another_Long_Condition(Parameter2)and then Yet_Another_Check(Param3)then
      Put_Line("This is a very long line that might need breaking");
   end if;
   
   -- Test 7: Long procedure call
   Very_Long_Package_Name.Very_Long_Procedure_Name(First_Parameter=>Value1,Second_Parameter=>Value2,Third_Parameter=>Value3,Fourth=>4);
   
   -- Test 8: Long case statement
   case Very_Long_Expression_That_Returns_An_Enumeration_Value(With_Parameters=>True,And_More_Parameters=>False)is
      when First_Value => Put_Line("First");
      when Second_Value=> Put_Line("Second");  -- Missing space before =>
      when others      => null;
   end case;
   
   -- Test 9: Very long comment that exceeds the normal line length limit and would need to be wrapped to multiple lines to be properly formatted
   
   -- Test 10: Long mathematical expression
   Result:=Complex_Calculation(A:=1,B:=2)*Another_Function(X:=10,Y:=20)+Yet_More_Math(Value:=30)/Final_Function(P:=40);
end Test_ALS_Line_Length;