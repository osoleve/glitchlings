from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    importlib.import_module("pytest_cov")
except ModuleNotFoundError:
    _HAS_PYTEST_COV = False
else:
    _HAS_PYTEST_COV = True


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

@pytest.fixture(scope="session")
def sample_text() -> str:
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT
