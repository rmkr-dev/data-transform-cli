from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def fixture_text(fixtures_dir: Path):
    def _load(name: str) -> str:
        return (fixtures_dir / name).read_text(encoding="utf-8")

    return _load
