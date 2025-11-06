from __future__ import annotations

import sys
import types
from collections.abc import Iterable
from typing import Any

import pytest

from glitchlings.compat import reset_optional_dependencies


@pytest.fixture()
def torch_stub() -> Iterable[type[Any]]:
    """Install a lightweight torch stub that exposes ``DataLoader``.
    
    This fixture is not autouse - tests that need it should explicitly request it
    or set it as autouse in their local conftest.py.
    """
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


# Note: verifiers_stub classes are available in conftest.py but NOT automatically installed
# Tests that need verifiers must set up sys.modules["verifiers"] themselves
