from __future__ import annotations

import importlib.util
import sys
import types
from typing import Sequence

import pytest


@pytest.fixture()
def toy_embeddings() -> dict[str, list[float]]:
    """Small test embeddings for VectorLexicon tests."""
    return {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "epsilon": [0.8, 0.2],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }


@pytest.fixture()
def shared_vector_embeddings() -> dict[str, list[float]]:
    """Shared vector embeddings for lexicon tests."""
    return {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }


def _fake_find_spec(monkeypatch, target: str) -> None:
    """Helper to fake importlib.util.find_spec for a target module."""
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == target:
            return types.SimpleNamespace(name=target)
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)


def _fake_import_module(monkeypatch, target: str, module: object) -> None:
    """Helper to fake importlib.import_module for a target module."""
    original = importlib.import_module

    def _patched(name: str, package: str | None = None):
        if name == target:
            return module
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", _patched)


@pytest.fixture()
def mock_spacy_language(monkeypatch):
    """Fixture providing a mocked spaCy language model."""
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


@pytest.fixture()
def mock_gensim_vectors(monkeypatch, tmp_path):
    """Fixture providing mocked gensim KeyedVectors."""
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


@pytest.fixture()
def mock_sentence_transformers(monkeypatch):
    """Fixture providing a mocked sentence-transformers module."""
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
