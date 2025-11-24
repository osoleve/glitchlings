"""Compatibility wrapper for the compiled Rust extension."""

from __future__ import annotations

import sys

from glitchlings.internal.rust import load_rust_module

_module = load_rust_module()

sys.modules.setdefault("_zoo_rust", _module)
sys.modules[__name__] = _module
