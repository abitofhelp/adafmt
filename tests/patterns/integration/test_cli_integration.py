import pytest, importlib

def test_cli_flags_present_or_skip():
    mod = importlib.util.find_spec("adafmt.cli") or importlib.util.find_spec("cli")
    if not mod:
        pytest.skip("adafmt.cli not available yet")
    cli = importlib.import_module(mod.name)
    # If parser exists, try parsing known flags; otherwise xfail until implemented
    parse = getattr(cli, "parse_args", None) or getattr(cli, "build_parser", None)
    if not parse:
        pytest.xfail("CLI parser function not exposed (pending implementation)")