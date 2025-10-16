#!/usr/bin/env python3
"""Ensure the committed Rust stubs match the version built by maturin."""

from __future__ import annotations

import argparse
import difflib
import importlib
import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
STUB_PATH = REPO_ROOT / "src" / "glitchlings" / "_zoo_rust.pyi"


def _load_generated_stub() -> tuple[Path, str]:
    module_spec = importlib.util.find_spec("glitchlings._zoo_rust")
    if module_spec is None:
        # Fallback for environments where the package is not installed but the
        # repository is available (e.g., CI before editable install).
        sys.path.insert(0, str(REPO_ROOT / "src"))
        module_spec = importlib.util.find_spec("glitchlings._zoo_rust")

    if module_spec is None:
        raise RuntimeError("glitchlings._zoo_rust is not importable; run maturin develop first")

    module = importlib.import_module("glitchlings._zoo_rust")
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
