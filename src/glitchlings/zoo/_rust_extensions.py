"""Compatibility shim for the Rust extension loader utilities.

This module re-exports from :mod:`glitchlings.internal.rust_ffi` for
backward compatibility. New code should import directly from
``internal.rust_ffi`` instead.
"""

from __future__ import annotations

from glitchlings.internal.rust import (
    RustExtensionImportError,
    get_rust_operation,
    preload_operations,
)
from glitchlings.internal.rust_ffi import resolve_seed

__all__ = ["RustExtensionImportError", "get_rust_operation", "preload_operations", "resolve_seed"]
