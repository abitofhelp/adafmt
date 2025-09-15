import pytest
from tests.test_utils import PatternEngine, DEFAULT_PATTERNS, fake_als

def test_als_then_patterns_end_to_end(tmp_path):
    rules = PatternEngine.load_list(DEFAULT_PATTERNS)
    before = """procedure Demo is
   X:Integer:=1..10; --bad  spacing
   Y :  String:=  ( 1,2 ,  3 );   --comment
   --foo
   Z : array (  1..10)  of Integer := (1,2,3);
begin
   Put_Line("value -- inside string");  --   EOL comment
end Demo;"""
    # Note: The paren_r_sp01 pattern removes space before ), so "(1 .. 10)  of" is expected
    want = """procedure Demo is
   X : Integer := 1 .. 10; --  bad  spacing
   Y : String := (1, 2, 3); --  comment
   --  foo
   Z : array (1 .. 10)  of Integer := (1, 2, 3);
begin
   Put_Line("value -- inside string");  --  EOL comment
end Demo;
"""
    after_als = fake_als(before)
    out, stats = PatternEngine.apply(after_als, rules, timeout_ms=50)
    assert out == want
    # sanity: a few key rules fired
    for k in ("range_dots01","assign_set01","comment_eol1","cmt_whole_01"):
        assert k in stats.replacements_by_rule