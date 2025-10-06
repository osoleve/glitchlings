import pytest

from glitchlings import SAMPLE_TEXT
from glitchlings.zoo.jargoyle import ensure_wordnet


@pytest.fixture(scope="session", autouse=True)
def _wordnet_ready() -> None:
    """Ensure the NLTK WordNet corpus is available for the test suite."""

    try:
        ensure_wordnet()
    except RuntimeError as exc:  # pragma: no cover - only triggered on env issues
        pytest.fail(f"WordNet setup failed for tests: {exc}")


@pytest.fixture(scope="session")
def sample_text() -> str:
    return SAMPLE_TEXT
