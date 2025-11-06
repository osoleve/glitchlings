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


# Optional glitchling fixtures - note that these are module-level instances
# Tests should use .clone() when they need to modify parameters


@pytest.fixture()
def typogre_instance():
    """Fixture providing a fresh Typogre instance for each test."""
    from glitchlings import typogre
    return typogre.clone()


@pytest.fixture()
def mim1c_instance():
    """Fixture providing a fresh Mim1c instance for each test."""
    from glitchlings import mim1c
    return mim1c.clone()


@pytest.fixture()
def jargoyle_instance():
    """Fixture providing a fresh Jargoyle instance for each test."""
    from glitchlings import jargoyle
    return jargoyle.clone()


@pytest.fixture()
def rushmore_instance():
    """Fixture providing a fresh Rushmore instance for each test."""
    from glitchlings import rushmore
    return rushmore.clone()


@pytest.fixture()
def redactyl_instance():
    """Fixture providing a fresh Redactyl instance for each test."""
    from glitchlings import redactyl
    return redactyl.clone()


@pytest.fixture()
def scannequin_instance():
    """Fixture providing a fresh Scannequin instance for each test."""
    from glitchlings import scannequin
    return scannequin.clone()


@pytest.fixture()
def zeedub_instance():
    """Fixture providing a fresh Zeedub instance for each test."""
    from glitchlings import zeedub
    return zeedub.clone()
