from __future__ import annotations

import importlib
import sys
import types
from collections.abc import Iterable
from random import Random
from typing import Any

import pytest

from glitchlings.compat import reset_optional_dependencies


@pytest.fixture(autouse=True)
def torch_stub() -> Iterable[type[Any]]:
    """Install a lightweight torch stub that exposes ``DataLoader``."""
    preserved = {
        name: sys.modules.get(name)
        for name in ("torch", "torch.utils", "torch.utils.data")
    }
    for name in preserved:
        sys.modules.pop(name, None)

    torch_module = types.ModuleType("torch")
    utils_module = types.ModuleType("torch.utils")
    data_module = types.ModuleType("torch.utils.data")

    class DummyDataLoader:
        def __init__(self, dataset: list[Any]) -> None:
            self.dataset = dataset
            self.batch_size = None

        def __iter__(self) -> Iterable[Any]:
            return iter(self.dataset)

        def __len__(self) -> int:
            return len(self.dataset)

    data_module.DataLoader = DummyDataLoader
    utils_module.data = data_module
    torch_module.utils = utils_module

    sys.modules["torch"] = torch_module
    sys.modules["torch.utils"] = utils_module
    sys.modules["torch.utils.data"] = data_module

    reset_optional_dependencies()

    yield DummyDataLoader

    for name, module in preserved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    reset_optional_dependencies()


class _Rubric:
    def __init__(self, funcs, weights):
        self.funcs = list(funcs)
        self.weights = list(weights)


class _SingleTurnEnv:
    def __init__(self, dataset=None, rubric=None):
        self.dataset = dataset
        self.rubric = rubric


class _VerifierEnvironment:
    def __init__(self, dataset=None):
        self.dataset = dataset


def _load_environment(_: str) -> _VerifierEnvironment:
    return _VerifierEnvironment()


@pytest.fixture(autouse=True)
def verifiers_stub() -> types.ModuleType:
    """Install a verifiers stub module for Prime DLC tests."""
    verifiers_module = types.ModuleType("verifiers")
    verifiers_module.Environment = _VerifierEnvironment
    verifiers_module.Rubric = _Rubric
    verifiers_module.SingleTurnEnv = _SingleTurnEnv
    verifiers_module.load_environment = _load_environment
    sys.modules["verifiers"] = verifiers_module
    return verifiers_module
