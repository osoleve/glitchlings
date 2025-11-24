from __future__ import annotations

# ruff: noqa: E402,F401
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Add both src and project root to path for imports
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import shared fixtures from the fixtures modules
# These are now available to all tests via conftest.py
from tests.fixtures.glitchlings import fresh_glitchling, sample_text  # noqa: E402
from tests.fixtures.lexicon import (  # noqa: E402
    MockLexicon,
    TrackingLexicon,
    shared_vector_embeddings,
    simple_lexicon,
    toy_embeddings,
)
from tests.fixtures.mocks import (  # noqa: E402
    _load_environment,
    _Rubric,
    _SingleTurnEnv,
    _VerifierEnvironment,
    mock_gensim_vectors,
    mock_module,
    mock_sentence_transformers,
    mock_spacy_language,
    torch_stub,
)

try:
    importlib.import_module("pytest_cov")
except ModuleNotFoundError:
    _HAS_PYTEST_COV = False
else:
    _HAS_PYTEST_COV = True


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for the test suite."""
    config.addinivalue_line("markers", "slow: marks tests as slow (>1s)")
    config.addinivalue_line(
        "markers", "integration: integration tests requiring multiple components"
    )
    config.addinivalue_line("markers", "requires_rust: requires compiled Rust extension")
    config.addinivalue_line("markers", "requires_datasets: requires datasets package")
    config.addinivalue_line("markers", "requires_torch: requires PyTorch")
    config.addinivalue_line(
        "markers", "requires_vectors: requires vector lexicon dependencies"
    )
    config.addinivalue_line("markers", "unit: unit tests (default)")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register stub coverage options when pytest-cov is absent."""

    if _HAS_PYTEST_COV:
        return

    group = parser.getgroup("cov")
    group.addoption(
        "--cov",
        action="append",
        default=[],
        metavar="MODULE",
        help="Ignored because pytest-cov is not installed.",
    )
    group.addoption(
        "--cov-report",
        action="append",
        default=[],
        metavar="TYPE",
        help="Ignored because pytest-cov is not installed.",
    )


# Note: sample_text fixture is now imported from tests.fixtures.glitchlings
# The fresh_glitchling factory fixture is also imported and can replace
# individual glitchling fixtures.

# Legacy glitchling fixtures - kept for backward compatibility
# New tests should use fresh_glitchling("name") instead


@pytest.fixture()
def typogre_instance():
    """Fixture providing a fresh Typogre instance for each test.

    DEPRECATED: Use fresh_glitchling("typogre") instead.
    """
    from glitchlings import typogre
    return typogre.clone()


@pytest.fixture()
def mim1c_instance():
    """Fixture providing a fresh Mim1c instance for each test.

    DEPRECATED: Use fresh_glitchling("mim1c") instead.
    """
    from glitchlings import mim1c
    return mim1c.clone()


@pytest.fixture()
def jargoyle_instance():
    """Fixture providing a fresh Jargoyle instance for each test.

    DEPRECATED: Use fresh_glitchling("jargoyle") instead.
    """
    from glitchlings import jargoyle
    return jargoyle.clone()


@pytest.fixture()
def rushmore_instance():
    """Fixture providing a fresh Rushmore instance for each test.

    DEPRECATED: Use fresh_glitchling("rushmore") instead.
    """
    from glitchlings import rushmore
    return rushmore.clone()


@pytest.fixture()
def redactyl_instance():
    """Fixture providing a fresh Redactyl instance for each test.

    DEPRECATED: Use fresh_glitchling("redactyl") instead.
    """
    from glitchlings import redactyl
    return redactyl.clone()


@pytest.fixture()
def scannequin_instance():
    """Fixture providing a fresh Scannequin instance for each test.

    DEPRECATED: Use fresh_glitchling("scannequin") instead.
    """
    from glitchlings import scannequin
    return scannequin.clone()


@pytest.fixture()
def zeedub_instance():
    """Fixture providing a fresh Zeedub instance for each test.

    DEPRECATED: Use fresh_glitchling("zeedub") instead.
    """
    from glitchlings import zeedub
    return zeedub.clone()
