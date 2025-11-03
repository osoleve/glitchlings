from __future__ import annotations

import importlib
import sys
from importlib import util as importlib_util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def ensure_rust_extension_importable() -> None:
    """Ensure the compiled Rust extension is importable for tests."""

    importlib.import_module("glitchlings")
    importlib.import_module("glitchlings._zoo_rust")


ensure_rust_extension_importable()

@pytest.fixture(scope="session")
def sample_text() -> str:
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT
