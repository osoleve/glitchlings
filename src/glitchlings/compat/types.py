"""Pure type definitions for compatibility infrastructure.

This module contains only type definitions and sentinels with no side effects.
It can be safely imported anywhere without triggering module loading or IO.

Pure guarantees:
- No import side effects
- No module loading attempts
- No file IO
- No RNG instantiation
"""

from __future__ import annotations


class _MissingSentinel:
    """Sentinel value indicating no cached import attempt has been made."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<MISSING>"


MISSING: _MissingSentinel = _MissingSentinel()
"""Singleton sentinel for uninitialized optional dependency cache."""


__all__ = [
    "MISSING",
    "_MissingSentinel",
]
