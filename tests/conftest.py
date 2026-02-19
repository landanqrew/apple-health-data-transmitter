from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_zip_path() -> str:
    return str(FIXTURES_DIR / "sample_export.zip")
