import pytest, importlib
spec = importlib.util.find_spec("als_client") or importlib.util.find_spec("adafmt.als_client")
if not spec:
    pytest.skip("als_client module not present")
als = importlib.import_module(spec.name)
def test_als_module_imports():
    assert als is not None