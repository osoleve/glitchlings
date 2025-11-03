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
    """Expose a locally built Rust extension for test runs when available."""

    if importlib_util.find_spec("glitchlings._zoo_rust") is not None:
        return

    build_root = ROOT / "build"
    if not build_root.exists():
        return

    artifacts = sorted(
        build_root.glob("lib.*/glitchlings/_zoo_rust.*"),
        key=lambda candidate: candidate.stat().st_mtime,
        reverse=True,
    )
    if not artifacts:
        return

    importlib.import_module("glitchlings")

    for artifact in artifacts:
        spec = importlib_util.spec_from_file_location("glitchlings._zoo_rust", artifact)
        if spec is None or spec.loader is None:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules["glitchlings._zoo_rust"] = module
            spec.loader.exec_module(module)
            package = sys.modules.get("glitchlings")
            if package is not None and hasattr(package, "__path__"):
                package.__path__.append(str(artifact.parent))
            return
        except (ImportError, ModuleNotFoundError):
            continue


ensure_rust_extension_importable()

@pytest.fixture(scope="session")
def sample_text() -> str:
    from glitchlings import SAMPLE_TEXT

    return SAMPLE_TEXT
