"""Compatibility shim for the Rust extension loader utilities."""

from __future__ import annotations

from glitchlings.internal.rust import (
    RustExtensionImportError,
    get_rust_operation,
    preload_operations,
    resolve_seed,
)

__all__ = ["RustExtensionImportError", "get_rust_operation", "preload_operations", "resolve_seed"]
