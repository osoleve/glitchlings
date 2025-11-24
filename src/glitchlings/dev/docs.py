"""Developer helpers for refreshing generated documentation assets."""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "docs"


def _run_script(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Documentation helper not found: {path}")
    runpy.run_path(str(path))


def refresh_cli_reference() -> None:
    """Regenerate the README CLI usage block."""
    _run_script(DOCS_DIR / "build_cli_reference.py")


def refresh_gallery() -> None:
    """Regenerate the glitchling gallery page."""
    _run_script(DOCS_DIR / "build_glitchling_gallery.py")


def refresh_all() -> None:
    """Regenerate CLI usage and gallery docs in one call."""
    refresh_cli_reference()
    refresh_gallery()


def main() -> None:
    refresh_all()


if __name__ == "__main__":
    main()
