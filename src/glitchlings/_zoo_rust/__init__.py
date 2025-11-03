"""Compatibility wrapper for the compiled Rust extension."""

from importlib import import_module
import sys

_module = import_module("_zoo_rust")
sys.modules[__name__] = _module
