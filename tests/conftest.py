import pytest

from glitchlings import SAMPLE_TEXT


@pytest.fixture(scope="session")
def sample_text() -> str:
    return SAMPLE_TEXT
