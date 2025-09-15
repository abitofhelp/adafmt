import pytest, importlib
spec = importlib.util.find_spec("edits") or importlib.util.find_spec("adafmt.edits")
if not spec:
    pytest.skip("edits module not present")
ed = importlib.import_module(spec.name)
def test_edits_module_imports():
    assert ed is not None