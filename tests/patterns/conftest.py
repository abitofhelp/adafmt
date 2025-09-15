import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def repo_root():
    # Assume tests/ lives at <repo>/tests
    return Path(__file__).resolve().parents[1]

@pytest.fixture
def tmp_text(tmp_path):
    def _w(name: str, text: str):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p
    return _w