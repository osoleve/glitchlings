from __future__ import annotations

import importlib
import inspect

import pytest

from glitchlings.types_rust import expected_signatures

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("glitchlings._zoo_rust") is None,
    reason="glitchlings._zoo_rust not built",
)


def test_rust_function_signatures_match() -> None:
    module = importlib.import_module("glitchlings._zoo_rust")
    expected = expected_signatures()
    for name, expected_signature in expected.items():
        function = getattr(module, name)
        actual = inspect.signature(function)
        assert (
            actual == expected_signature
        ), f"Signature mismatch for {name}: {actual!s} != {expected_signature!s}"
