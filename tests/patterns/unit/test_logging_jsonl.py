import pytest, importlib
spec = importlib.util.find_spec("logging_jsonl") or importlib.util.find_spec("adafmt.logging_jsonl")
if not spec:
    pytest.skip("logging_jsonl module not present")
lj = importlib.import_module(spec.name)
def test_logging_jsonl_module_imports():
    assert lj is not None