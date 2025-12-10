"""Shared helpers for loading the compiled Rust extension."""

from __future__ import annotations

import random
import sys
from importlib import machinery, util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping, MutableMapping, cast

_EXTENSION_STEM = "_corruption_engine"


class RustExtensionImportError(RuntimeError):
    """Raised when the compiled Rust extension cannot be imported."""


def _iter_extension_candidates() -> tuple[Path, ...]:
    """Return likely paths for the compiled extension within the package."""

    package_root = Path(__file__).resolve().parents[1]
    extension_dir = package_root / _EXTENSION_STEM
    search_roots = (extension_dir, package_root)

    candidates: list[Path] = []
    for root in search_roots:
        for suffix in machinery.EXTENSION_SUFFIXES:
            candidate = (root / _EXTENSION_STEM).with_suffix(suffix)
            if candidate.exists():
                candidates.append(candidate)
    return tuple(candidates)


def _existing_compiled_module() -> ModuleType | None:
    """Return a previously loaded compiled module if one is present."""

    for name in ("glitchlings._corruption_engine", "_corruption_engine"):
        module = sys.modules.get(name)
        if module is None:
            continue
        module_file = getattr(module, "__file__", "")
        if module_file and not str(module_file).endswith("__init__.py"):
            return module
    return None


def _load_extension_from_disk() -> ModuleType:
    """Load the compiled extension from disk or raise if unavailable."""

    candidates = _iter_extension_candidates()
    for candidate in candidates:
        spec = util.spec_from_file_location(_EXTENSION_STEM, candidate)
        if spec is None or spec.loader is None:
            continue
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    searched = ", ".join(str(path) for path in candidates) or "<unavailable>"
    message = (
        "glitchlings._corruption_engine failed to import. Rebuild the project with"
        "`pip install .` or `maturin develop` so the compiled extension is available "
        f"(searched: {searched})."
    )
    raise RustExtensionImportError(message)


def load_rust_module() -> ModuleType:
    """Return the compiled Rust module, loading it on demand."""

    existing = _existing_compiled_module()
    if existing is not None:
        return existing

    module = _load_extension_from_disk()
    sys.modules.setdefault("glitchlings._corruption_engine", module)
    sys.modules.setdefault("_corruption_engine", module)
    return module


_RUST_MODULE: ModuleType | None = None
_OPERATION_CACHE: MutableMapping[str, Callable[..., Any]] = {}


def _get_rust_module() -> ModuleType:
    """Return the compiled Rust module, importing it on first use."""

    global _RUST_MODULE

    if _RUST_MODULE is None:
        _RUST_MODULE = load_rust_module()

    return _RUST_MODULE


def _build_missing_operation_error(name: str) -> RuntimeError:
    message = (
        "Rust operation '{name}' is not exported by glitchlings._corruption_engine."
        "Rebuild the project to refresh the compiled extension."
    )
    return RuntimeError(message.format(name=name))


def resolve_seed(seed: int | None, rng: random.Random | None) -> int:
    """Resolve a 64-bit seed using an optional RNG."""

    if seed is not None:
        return int(seed) & 0xFFFFFFFFFFFFFFFF
    if rng is not None:
        return rng.getrandbits(64)
    return random.getrandbits(64)


def get_rust_operation(operation_name: str) -> Callable[..., Any]:
    """Return a callable exported by :mod:`glitchlings._corruption_engine`.

    Parameters
    ----------
    operation_name : str
        Name of the function to retrieve from the compiled extension.

    Raises
    ------
    RuntimeError
        If the operation cannot be located or is not callable.
    """

    operation = _OPERATION_CACHE.get(operation_name)
    if operation is not None:
        return operation

    module = _get_rust_module()
    try:
        candidate = getattr(module, operation_name)
    except AttributeError as exc:
        raise _build_missing_operation_error(operation_name) from exc

    if not callable(candidate):
        raise _build_missing_operation_error(operation_name)

    operation = cast(Callable[..., Any], candidate)
    _OPERATION_CACHE[operation_name] = operation
    return operation


def preload_operations(*operation_names: str) -> Mapping[str, Callable[..., Any]]:
    """Eagerly load multiple Rust operations at once."""

    return {name: get_rust_operation(name) for name in operation_names}


__all__ = [
    "RustExtensionImportError",
    "get_rust_operation",
    "load_rust_module",
    "preload_operations",
    "resolve_seed",
]
