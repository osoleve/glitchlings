"""Regression tests covering dataset corruption with optional dependencies."""

from __future__ import annotations

import builtins
import importlib
import sys

import pytest


def test_corrupt_dataset_requires_optional_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ``Glitchling.corrupt_dataset`` surfaces a clear error."""

    monkeypatch.delitem(sys.modules, "datasets", raising=False)

    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[override]
        if name == "datasets":
            raise ModuleNotFoundError("datasets is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    for module_name in [
        module
        for module in sys.modules
        if module == "glitchlings" or module.startswith("glitchlings.")
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    glitchlings = importlib.import_module("glitchlings")
    assert glitchlings is not None

    from glitchlings.zoo.core import AttackWave, Glitchling

    noop = Glitchling("noop", lambda text, **_: text, AttackWave.CHARACTER)

    with pytest.raises(ModuleNotFoundError, match="datasets is not installed"):
        noop.corrupt_dataset(dataset=object(), columns=["text"])
