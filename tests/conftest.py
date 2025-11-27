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
# The fresh_glitchling factory fixture is also imported and provides
# fresh glitchling instances - use fresh_glitchling("name") in tests.
