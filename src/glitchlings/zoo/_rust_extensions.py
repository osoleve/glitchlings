"""Helpers for loading the mandatory Rust acceleration hooks."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import Any, Callable, Mapping, MutableMapping, cast


class RustExtensionImportError(RuntimeError):
    """Raised when the compiled Rust extension cannot be imported."""


def _import_rust_module() -> ModuleType:
    """Import the compiled Rust module, raising if it cannot be located."""

    module: ModuleType | None = None
    last_error: ModuleNotFoundError | None = None
    for name in ("glitchlings._zoo_rust", "_zoo_rust"):
        try:
            module = import_module(name)
        except ModuleNotFoundError as exc:
            last_error = exc
        else:
            break

    if module is None:
        message = (
            "glitchlings._zoo_rust failed to import. Rebuild the project with "
            "`pip install .` or `maturin develop` so the compiled extension is available."
        )
        raise RustExtensionImportError(message) from last_error

    sys.modules.setdefault("glitchlings._zoo_rust", module)
    sys.modules.setdefault("_zoo_rust", module)
    return module


_RUST_MODULE: ModuleType | None = None
_OPERATION_CACHE: MutableMapping[str, Callable[..., Any]] = {}


def _get_rust_module() -> ModuleType:
    """Return the compiled Rust module, importing it on first use."""

    global _RUST_MODULE

    if _RUST_MODULE is None:
        _RUST_MODULE = _import_rust_module()

    return _RUST_MODULE


def _build_missing_operation_error(name: str) -> RuntimeError:
    message = (
        "Rust operation '{name}' is not exported by glitchlings._zoo_rust. "
        "Rebuild the project to refresh the compiled extension."
    )
    return RuntimeError(message.format(name=name))


def get_rust_operation(operation_name: str) -> Callable[..., Any]:
    """Return a callable exported by :mod:`glitchlings._zoo_rust`.

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


__all__ = ["RustExtensionImportError", "get_rust_operation", "preload_operations"]
