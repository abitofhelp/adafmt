import pytest, importlib
spec = importlib.util.find_spec("cli") or importlib.util.find_spec("adafmt.cli")
if not spec:
    pytest.skip("cli module not present")
cli = importlib.import_module(spec.name)
def test_cli_module_imports():
    assert cli is not None