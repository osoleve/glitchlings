from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

@pytest.fixture(scope="session")
def sample_text() -> str:
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT
