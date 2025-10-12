"""Tests for the optional dependency compatibility helpers."""

from __future__ import annotations

import math

import pytest

from glitchlings.compat import optional_import


def test_optional_import_resolves_module() -> None:
    resource = optional_import("math")

    assert resource.is_available()
    assert resource.optional() is math
    assert resource.require() is math


def test_optional_import_resolves_attribute() -> None:
    resource = optional_import("math", "sqrt")

    assert resource.is_available()
    assert resource.require() is math.sqrt


def test_optional_import_missing_module() -> None:
    resource = optional_import("glitchlings__missing__module", friendly_name="missing")

    assert resource.optional() is None
    with pytest.raises(ModuleNotFoundError, match="missing is not installed"):
        resource.require()


def test_optional_import_missing_attribute() -> None:
    resource = optional_import("math", "nope")

    with pytest.raises(ImportError, match="does not expose"):
        resource.require()
