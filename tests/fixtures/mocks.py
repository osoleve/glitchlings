"""Centralized mock infrastructure for optional dependencies."""
from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any, Sequence

import pytest

__all__ = [
    'mock_module',
    'torch_stub',
    'mock_spacy_language',
    'mock_gensim_vectors',
    'mock_sentence_transformers',
    '_Rubric',
    '_SingleTurnEnv',
    '_VerifierEnvironment',
    '_load_environment',
]

@contextmanager
def mock_module(module_name: str, stub_module: types.ModuleType):
    """Context manager that temporarily installs a mock module.

    Args:
        module_name: Name of the module to mock (e.g., "torch")
        stub_module: The stub module to install

    Yields:
        The stub module

    Example:
        stub = types.ModuleType("torch")
        with mock_module("torch", stub):
            import torch  # Gets the stub
    """
    preserved = sys.modules.get(module_name)
    sys.modules[module_name] = stub_module
    try:
        yield stub_module
    finally:
        if preserved is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = preserved


@pytest.fixture
def torch_stub() -> Iterable[type[Any]]:
    """Install a lightweight torch stub that exposes DataLoader.

    This fixture provides a minimal PyTorch stub with just enough functionality
    to test DLC integration without requiring the full PyTorch installation.

    Yields:
        DummyDataLoader class that can be used in tests
    """
    from glitchlings.compat import reset_optional_dependencies

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

    data_module.DataLoader = DummyDataLoader  # type: ignore[attr-defined]
    utils_module.data = data_module  # type: ignore[attr-defined]
    torch_module.utils = utils_module  # type: ignore[attr-defined]

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


def _fake_find_spec(monkeypatch, target: str) -> None:
    """Helper to fake importlib.util.find_spec for a target module.

    Args:
        monkeypatch: pytest monkeypatch fixture
        target: Name of the module to fake
    """
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == target:
            return types.SimpleNamespace(name=target)
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)


def _fake_import_module(monkeypatch, target: str, module: object) -> None:
    """Helper to fake importlib.import_module for a target module.

    Args:
        monkeypatch: pytest monkeypatch fixture
        target: Name of the module to fake
        module: The fake module to return
    """
    original = importlib.import_module

    def _patched(name: str, package: str | None = None):
        if name == target:
            return module
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", _patched)


@pytest.fixture
def mock_spacy_language(monkeypatch):
    """Fixture providing a mocked spaCy language model.

    Returns:
        Tuple of (stub_spacy_module, calls_dict) for verification
    """
    monkeypatch.delitem(sys.modules, "spacy", raising=False)
    stub_spacy = types.ModuleType("spacy")
    calls: dict[str, str] = {}

    def _load(name: str):
        calls["model"] = name
        return f"loaded:{name}"

    stub_spacy.load = _load  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "spacy", stub_spacy)
    _fake_find_spec(monkeypatch, "spacy")
    _fake_import_module(monkeypatch, "spacy", stub_spacy)

    return stub_spacy, calls


@pytest.fixture
def mock_gensim_vectors(monkeypatch, tmp_path):
    """Fixture providing mocked gensim KeyedVectors.

    Returns:
        Tuple of (fake_keyedvectors_module, kv_calls_dict, w2v_calls_list)
    """
    from pathlib import Path

    monkeypatch.delitem(sys.modules, "gensim", raising=False)
    monkeypatch.delitem(sys.modules, "gensim.models", raising=False)
    monkeypatch.delitem(sys.modules, "gensim.models.keyedvectors", raising=False)

    fake_gensim = types.ModuleType("gensim")
    fake_models = types.ModuleType("gensim.models")
    fake_keyedvectors = types.ModuleType("gensim.models.keyedvectors")
    kv_calls: dict[str, object] = {}
    w2v_calls: list[dict[str, object]] = []

    class FakeKeyedVectors:
        @classmethod
        def load(cls, path: str, *, mmap: str | None = None):
            kv_calls["path"] = path
            kv_calls["mmap"] = mmap
            return "kv-loaded"

        @classmethod
        def load_word2vec_format(cls, path: str, *, binary: bool):
            w2v_calls.append({"path": path, "binary": binary})
            return f"w2v:{Path(path).suffix}"

    fake_keyedvectors.KeyedVectors = FakeKeyedVectors  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "gensim", fake_gensim)
    monkeypatch.setitem(sys.modules, "gensim.models", fake_models)
    monkeypatch.setitem(sys.modules, "gensim.models.keyedvectors", fake_keyedvectors)

    _fake_find_spec(monkeypatch, "gensim")

    original_import = importlib.import_module

    def _patched_import(name: str, package: str | None = None):
        if name == "gensim.models.keyedvectors":
            return fake_keyedvectors
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", _patched_import)

    return fake_keyedvectors, kv_calls, w2v_calls


@pytest.fixture
def mock_sentence_transformers(monkeypatch):
    """Fixture providing a mocked sentence-transformers module.

    Returns:
        The stub sentence_transformers module for verification
    """
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    stub_module = types.ModuleType("sentence_transformers")

    class FakeModel:
        def __init__(self, name: str) -> None:
            self.name = name
            stub_module.last_instance = self  # type: ignore[attr-defined]

        def encode(
            self,
            tokens: Sequence[str],
            *,
            batch_size: int,
            normalize_embeddings: bool,
            convert_to_numpy: bool,
        ) -> list[list[float]]:
            stub_module.encode_call = {  # type: ignore[attr-defined]
                "tokens": list(tokens),
                "batch_size": batch_size,
                "normalize": normalize_embeddings,
                "convert": convert_to_numpy,
            }
            return [[1.0, 0.0], [0.0, 1.0]]

    stub_module.SentenceTransformer = FakeModel  # type: ignore[attr-defined]
    _fake_find_spec(monkeypatch, "sentence_transformers")
    _fake_import_module(monkeypatch, "sentence_transformers", stub_module)

    return stub_module


# Verifiers stub classes for DLC tests
class _Rubric:
    """Mock rubric for verifiers tests."""

    def __init__(self, funcs, weights):
        self.funcs = list(funcs)
        self.weights = list(weights)


class _SingleTurnEnv:
    """Mock single-turn environment for verifiers tests."""

    def __init__(self, dataset=None, rubric=None):
        self.dataset = dataset
        self.rubric = rubric


class _VerifierEnvironment:
    """Mock verifier environment for tests."""

    def __init__(self, dataset=None):
        self.dataset = dataset


def _load_environment(_: str) -> _VerifierEnvironment:
    """Mock load_environment function."""
    return _VerifierEnvironment()
