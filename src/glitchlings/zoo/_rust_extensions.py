"""Helpers for loading optional Rust acceleration hooks."""

from __future__ import annotations

import importlib
import logging
from types import ModuleType
from typing import Any, Callable

log = logging.getLogger(__name__)


_rust_operation_cache: dict[str, Callable[..., Any] | None] = {}
_rust_module: ModuleType | None = None
_module_checked: bool = False


def _load_rust_module() -> ModuleType | None:
    """Attempt to import the optional :mod:`glitchlings._zoo_rust` module."""

    global _rust_module, _module_checked

    if _module_checked:
        return _rust_module

    _module_checked = True
    try:
        module = importlib.import_module("glitchlings._zoo_rust")
    except ModuleNotFoundError:
        log.debug(
            "Rust extension module glitchlings._zoo_rust is unavailable; falling back to"
            " Python implementations where possible",
        )
        _rust_module = None
    except ImportError as exc:  # pragma: no cover - defensive
        log.warning("Failed to import glitchlings._zoo_rust: %s", exc)
        _rust_module = None
    else:
        _rust_module = module
        log.debug("Rust extension module successfully loaded")

    return _rust_module


def get_rust_operation(operation_name: str) -> Callable[..., Any] | None:
    """Load a specific Rust operation by name with caching.

    Parameters
    ----------
    operation_name : str
        The name of the operation to import from glitchlings._zoo_rust.

    Returns
    -------
    Callable | None
        The Rust operation callable if available, ``None`` otherwise.
    """

    if operation_name in _rust_operation_cache:
        return _rust_operation_cache[operation_name]

    module = _load_rust_module()
    if module is None:
        _rust_operation_cache[operation_name] = None
        return None

    operation = getattr(module, operation_name, None)
    if not callable(operation):
        log.debug(
            "Rust operation '%s' is unavailable in glitchlings._zoo_rust", operation_name
        )
        _rust_operation_cache[operation_name] = None
        return None

    _rust_operation_cache[operation_name] = operation
    log.debug("Rust operation '%s' loaded successfully", operation_name)
    return operation


def clear_cache() -> None:
    """Clear cached module and operation handles."""

    global _rust_module, _module_checked, _rust_operation_cache

    _rust_module = None
    _module_checked = False
    _rust_operation_cache.clear()
    log.debug("Rust extension cache cleared")


def preload_operations(*operation_names: str) -> dict[str, Callable[..., Any] | None]:
    """Eagerly load multiple Rust operations at once."""

    return {name: get_rust_operation(name) for name in operation_names}


__all__ = [
    "get_rust_operation",
    "clear_cache",
    "preload_operations",
]
