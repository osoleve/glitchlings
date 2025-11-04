"""Compatibility wrapper for the compiled Rust extension."""

from __future__ import annotations

import sys
from importlib import import_module, machinery, util
from pathlib import Path


def _load_local_extension() -> object:
    """Load the compiled extension from the source tree if available."""

    package_dir = Path(__file__).resolve().parent
    search_roots = (package_dir, package_dir.parent)

    for root in search_roots:
        for suffix in machinery.EXTENSION_SUFFIXES:
            candidate = (root / "_zoo_rust").with_suffix(suffix)
            if not candidate.exists():
                continue

            spec = util.spec_from_file_location("_zoo_rust", candidate)
            if spec is None or spec.loader is None:  # pragma: no cover - defensive
                continue

            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    message = "Unable to locate the compiled glitchlings._zoo_rust extension."
    raise ModuleNotFoundError(message)


try:
    _module = import_module("_zoo_rust")
except ModuleNotFoundError:
    _module = _load_local_extension()

sys.modules.setdefault("_zoo_rust", _module)
sys.modules[__name__] = _module
