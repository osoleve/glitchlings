"""Centralized loading and fallback management for optional Rust extensions.

This module provides a single source of truth for importing Rust-accelerated
operations, eliminating duplicated try/except blocks across the codebase.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

log = logging.getLogger(__name__)


# Cache of loaded Rust operations to avoid repeated import attempts
_rust_operation_cache: dict[str, Callable[..., Any] | None] = {}
_rust_module_available: bool | None = None


def is_rust_module_available() -> bool:
    """Check if the Rust extension module can be imported.

    Returns
    -------
    bool
        True if glitchlings._zoo_rust can be imported successfully.

    Notes
    -----
    The result is cached after the first check to avoid repeated import attempts.
    """
    global _rust_module_available

    if _rust_module_available is not None:
        return _rust_module_available

    try:
        import glitchlings._zoo_rust  # noqa: F401

        _rust_module_available = True
        log.debug("Rust extension module successfully loaded")
    except (ImportError, ModuleNotFoundError):
        _rust_module_available = False
        log.debug("Rust extension module not available; using Python fallbacks")

    return _rust_module_available


def get_rust_operation(operation_name: str) -> Callable[..., Any] | None:
    """Load a specific Rust operation by name with caching.

    Parameters
    ----------
    operation_name : str
        The name of the operation to import from glitchlings._zoo_rust.

    Returns
    -------
    Callable | None
        The Rust operation callable if available, None otherwise.

    Examples
    --------
    >>> fatfinger = get_rust_operation("fatfinger")
    >>> if fatfinger is not None:
    ...     result = fatfinger(text, ...)
    ... else:
    ...     result = python_fallback(text, ...)

    Notes
    -----
    - Results are cached to avoid repeated imports
    - Returns None if the Rust module is unavailable or the operation doesn't exist
    - All import errors are logged at debug level
    """
    # Check cache first
    if operation_name in _rust_operation_cache:
        return _rust_operation_cache[operation_name]

    # If the module isn't available, don't try to import individual operations
    if not is_rust_module_available():
        _rust_operation_cache[operation_name] = None
        return None

    try:
        from glitchlings import _zoo_rust

        operation = getattr(_zoo_rust, operation_name, None)
        _rust_operation_cache[operation_name] = operation

        if operation is None:
            log.debug(f"Rust operation '{operation_name}' not found in extension module")
        else:
            log.debug(f"Rust operation '{operation_name}' loaded successfully")

        return operation

    except (ImportError, ModuleNotFoundError, AttributeError) as exc:
        log.debug(f"Failed to load Rust operation '{operation_name}': {exc}")
        _rust_operation_cache[operation_name] = None
        return None


def clear_cache() -> None:
    """Clear the operation cache, forcing re-import on next access.

    This is primarily useful for testing scenarios where the Rust module
    availability might change during runtime.
    """
    global _rust_module_available, _rust_operation_cache

    _rust_module_available = None
    _rust_operation_cache.clear()
    log.debug("Rust extension cache cleared")


def preload_operations(*operation_names: str) -> dict[str, Callable[..., Any] | None]:
    """Eagerly load multiple Rust operations at once.

    Parameters
    ----------
    *operation_names : str
        Names of operations to preload.

    Returns
    -------
    dict[str, Callable | None]
        Mapping of operation names to their callables (or None if unavailable).

    Examples
    --------
    >>> ops = preload_operations("fatfinger", "reduplicate_words", "delete_random_words")
    >>> fatfinger = ops["fatfinger"]
    """
    return {name: get_rust_operation(name) for name in operation_names}


__all__ = [
    "is_rust_module_available",
    "get_rust_operation",
    "clear_cache",
    "preload_operations",
]
