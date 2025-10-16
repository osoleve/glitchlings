#!/usr/bin/env python3
"""Ensure the committed Rust stubs match the version built by maturin."""

from __future__ import annotations

import argparse
import difflib
import importlib
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
STUB_PATH = REPO_ROOT / "src" / "glitchlings" / "_zoo_rust.pyi"


def _load_generated_stub() -> tuple[Path, str]:
    try:
        module = importlib.import_module("glitchlings._zoo_rust")
    except ModuleNotFoundError:
        # Fallback for environments where the package is not installed but the
        # repository is available (e.g., CI before editable install). We defer
        # importing until after we have patched `sys.path` so that a missing
        # parent package does not abort the search.
        repo_src = str(REPO_ROOT / "src")
        if repo_src not in sys.path:
            sys.path.insert(0, repo_src)
        try:
            module = importlib.import_module("glitchlings._zoo_rust")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "glitchlings._zoo_rust is not importable; run maturin develop first"
            ) from exc

    module_path = Path(module.__file__)
    stub_path = module_path.with_suffix(".pyi")
    if not stub_path.exists():
        raise RuntimeError(f"Generated stub not found next to {module_path}")

    return stub_path, stub_path.read_text(encoding="utf-8")


def _load_repo_stub() -> str:
    if STUB_PATH.exists():
        return STUB_PATH.read_text(encoding="utf-8")
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="Replace the tracked stub with the generated version.")
    args = parser.parse_args(argv)

    generated_path, generated = _load_generated_stub()
    recorded = _load_repo_stub()

    if generated == recorded:
        return 0

    if args.update:
        STUB_PATH.write_text(generated, encoding="utf-8")
        return 0

    diff = difflib.unified_diff(
        recorded.splitlines(),
        generated.splitlines(),
        fromfile=str(STUB_PATH),
        tofile=str(generated_path),
        lineterm="",
    )
    sys.stdout.write("\n".join(diff) + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
