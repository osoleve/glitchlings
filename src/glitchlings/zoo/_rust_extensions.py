"""Centralised loading for the mandatory Rust extensions.

The project now requires the compiled :mod:`glitchlings._zoo_rust` module at
runtime.  This module provides a single import surface for those operations and
emits clear, actionable errors when the extension is missing or incomplete.
"""

from __future__ import annotations

import importlib
import logging
from types import ModuleType
from typing import Any, Callable, cast

log = logging.getLogger(__name__)


# Cache of loaded Rust operations to avoid repeated import attempts
_rust_operation_cache: dict[str, Callable[..., Any]] = {}
_rust_module: ModuleType | None = None


def _load_rust_module() -> ModuleType:
    """Import and cache the compiled Rust extension module.

    Raises
    ------
    RuntimeError
        If the extension cannot be imported.  The error message explains how to
        rebuild the wheel in environments where the compiled artefact is
        missing.
    """

    global _rust_module

    if _rust_module is not None:
        return _rust_module

    try:
        module = importlib.import_module("glitchlings._zoo_rust")
    except ModuleNotFoundError as exc:
        message = (
            "glitchlings._zoo_rust is required but missing. Rebuild the Rust "
            "extensions with `pip install .` or `maturin develop`."
        )
        raise RuntimeError(message) from exc
    except ImportError as exc:  # pragma: no cover - defensive
        message = "glitchlings._zoo_rust failed to import"
        raise RuntimeError(message) from exc

    _rust_module = module
    log.debug("Rust extension module successfully loaded")
    return module


def get_rust_operation(operation_name: str) -> Callable[..., Any]:
    """Load a specific Rust operation by name with caching.

    Parameters
    ----------
    operation_name : str
        The name of the operation to import from glitchlings._zoo_rust.

    Returns
    -------
    Callable
        The Rust operation callable.

    Notes
    -----
    - Results are cached to avoid repeated imports.
    - A missing operation raises :class:`RuntimeError` with guidance for
      rebuilding the extension module.
    """
    # Check cache first
    if operation_name in _rust_operation_cache:
        return _rust_operation_cache[operation_name]

    module = _load_rust_module()

    try:
        operation_obj = getattr(module, operation_name)
    except AttributeError as exc:
        message = (
            f"Rust operation '{operation_name}' is missing from glitchlings._zoo_rust. "
            "Rebuild the extension to refresh available operations."
        )
        raise RuntimeError(message) from exc

    if not callable(operation_obj):  # pragma: no cover - defensive
        message = f"Rust operation '{operation_name}' is not callable"
        raise RuntimeError(message)

    operation = cast(Callable[..., Any], operation_obj)
    _rust_operation_cache[operation_name] = operation
    log.debug("Rust operation '%s' loaded successfully", operation_name)

    return operation


def clear_cache() -> None:
    """Clear the operation cache, forcing re-import on next access.

    This is primarily useful for testing scenarios where the Rust module
    availability might change during runtime.
    """
    global _rust_module, _rust_operation_cache

    _rust_module = None
    _rust_operation_cache.clear()
    log.debug("Rust extension cache cleared")


def preload_operations(*operation_names: str) -> dict[str, Callable[..., Any]]:
    """Eagerly load multiple Rust operations at once.

    Parameters
    ----------
    *operation_names : str
        Names of operations to preload.

    Returns
    -------
    dict[str, Callable]
        Mapping of operation names to their callables.

    Examples
    --------
    >>> ops = preload_operations("fatfinger", "reduplicate_words", "delete_random_words")
    >>> fatfinger = ops["fatfinger"]
    """
    return {name: get_rust_operation(name) for name in operation_names}


__all__ = [
    "get_rust_operation",
    "clear_cache",
    "preload_operations",
]
