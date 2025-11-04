from __future__ import annotations

import importlib
import subprocess
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


def _build_rust_extension() -> None:
    """Install the project in editable mode to compile the Rust extension."""

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(ROOT)],
            check=True,
            cwd=str(ROOT),
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - build failure
        message = "Failed to build the Rust extension."
        raise RuntimeError(message) from exc


def ensure_rust_extension_importable() -> None:
    """Ensure the compiled Rust extension is importable for tests."""

    importlib.import_module("glitchlings")
    try:
        importlib.import_module("glitchlings._zoo_rust")
    except ModuleNotFoundError:
        _build_rust_extension()
        importlib.invalidate_caches()
        sys.modules.pop("glitchlings._zoo_rust", None)
        sys.modules.pop("_zoo_rust", None)
        importlib.import_module("glitchlings._zoo_rust")
ensure_rust_extension_importable()

@pytest.fixture(scope="session")
def sample_text() -> str:
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT
