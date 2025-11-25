"""Internal utilities shared across the glitchlings package.

This subpackage contains impure modules that handle side effects:

- ``rust.py``: Low-level Rust extension loader and FFI primitives
- ``rust_ffi.py``: High-level Rust operation wrappers (preferred entry point)

Pure modules should NOT import from this package. Use the operations in
``rust_ffi.py`` at boundary layers only.

See AGENTS.md "Functional Purity Architecture" for details.
"""

from __future__ import annotations

__all__ = []
