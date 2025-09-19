# adafmt tests (patterns-focused pack)

This pack drops into your repo under `tests/` with the structure you requested.
It includes integration tests for the **patterns** feature and placeholder unit
tests that will **skip** if a module isn't present yet.

## Run

```bash
pytest -q
```

## Notes
- `integration/test_adafmt_integration.py` uses a small helper engine from `test_utils.py`
  and a default patterns set aligned to the **12-char slug + title/category** schema.
- `integration/test_cli_integration.py` and the unit tests will **skip or xfail**
  until the corresponding features land (e.g., CLI flags).