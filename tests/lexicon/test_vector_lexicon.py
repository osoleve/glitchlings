from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from typing import Sequence

import pytest

from glitchlings.lexicon import vector as vector_module

VectorLexicon = vector_module.VectorLexicon
build_vector_cache = vector_module.build_vector_cache
load_vector_source = vector_module.load_vector_source
main = vector_module.main
_SpaCyAdapter = vector_module._SpaCyAdapter
_load_gensim_vectors = vector_module._load_gensim_vectors
_load_spacy_language = vector_module._load_spacy_language
_build_sentence_transformer_embeddings = (
    vector_module._build_sentence_transformer_embeddings
)


@pytest.fixture()
def toy_embeddings() -> dict[str, list[float]]:
    return {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "epsilon": [0.8, 0.2],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }


def test_vector_lexicon_precompute_and_sampling(toy_embeddings: dict[str, list[float]]) -> None:
    lexicon = VectorLexicon(
        source=toy_embeddings,
        max_neighbors=3,
        min_similarity=0.05,
        seed=123,
    )

    cached = lexicon.precompute("alpha")
    assert cached[0] == "beta"
    assert "alpha" not in cached

    sampled = lexicon.get_synonyms("alpha", n=2)
    assert sampled == [cached[0], cached[1]]

    second_sample = lexicon.get_synonyms("alpha", n=2)
    assert sampled == second_sample


def test_build_vector_cache_helper(tmp_path: Path, toy_embeddings: dict[str, list[float]]) -> None:
    output_path = tmp_path / "cache.json"
    build_vector_cache(source=toy_embeddings, words=["alpha", "gamma"], output_path=output_path)

    snapshot = VectorLexicon.load_cache(output_path)
    cache = snapshot.entries

    assert set(cache) == {"alpha", "gamma"}
    assert cache["alpha"]
    assert cache["gamma"]


def test_vector_cache_cli(tmp_path: Path, toy_embeddings: dict[str, list[float]]) -> None:
    vectors_path = tmp_path / "vectors.json"
    output_path = tmp_path / "output.json"
    tokens_path = tmp_path / "tokens.txt"

    with vectors_path.open("w", encoding="utf8") as handle:
        json.dump(toy_embeddings, handle)

    with tokens_path.open("w", encoding="utf8") as handle:
        handle.write("alpha\n")
        handle.write("delta\n")

    exit_code = main(
        [
            "--source",
            str(vectors_path),
            "--output",
            str(output_path),
            "--tokens",
            str(tokens_path),
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    payload = VectorLexicon.load_cache(output_path).entries

    assert sorted(payload) == ["alpha", "delta"]


def test_vector_cache_cli_refuses_to_overwrite(tmp_path: Path, toy_embeddings: dict[str, list[float]]) -> None:
    vectors_path = tmp_path / "vectors.json"
    output_path = tmp_path / "output.json"
    tokens_path = tmp_path / "tokens.txt"

    with vectors_path.open("w", encoding="utf8") as handle:
        json.dump(toy_embeddings, handle)

    with tokens_path.open("w", encoding="utf8") as handle:
        handle.write("alpha\n")

    output_path.write_text("existing cache", encoding="utf8")

    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "--source",
                str(vectors_path),
                "--output",
                str(output_path),
                "--tokens",
                str(tokens_path),
            ]
        )

    assert "Refusing to overwrite existing cache" in str(excinfo.value)


def test_vector_cache_cli_case_sensitive_preserves_case(tmp_path: Path) -> None:
    vectors_path = tmp_path / "vectors.json"
    output_path = tmp_path / "output.json"
    tokens_path = tmp_path / "tokens.txt"

    embeddings = {
        "Alpha": [1.0, 0.0],
        "alpha": [0.99, 0.01],
        "Beta": [0.9, 0.1],
    }

    with vectors_path.open("w", encoding="utf8") as handle:
        json.dump(embeddings, handle)

    with tokens_path.open("w", encoding="utf8") as handle:
        handle.write("Alpha\nalpha\n")

    exit_code = main(
        [
            "--source",
            str(vectors_path),
            "--output",
            str(output_path),
            "--tokens",
            str(tokens_path),
            "--case-sensitive",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    payload = VectorLexicon.load_cache(output_path).entries

    assert "Alpha" in payload and "alpha" in payload
    assert "alpha" in payload["Alpha"]


def test_vector_cache_cli_case_sensitive_falls_back_to_lowercase_source(tmp_path: Path) -> None:
    vectors_path = tmp_path / "vectors.json"
    output_path = tmp_path / "output.json"
    tokens_path = tmp_path / "tokens.txt"

    embeddings = {
        "alpha": [1.0, 0.0],
        "beta": [0.99, 0.01],
    }

    with vectors_path.open("w", encoding="utf8") as handle:
        json.dump(embeddings, handle)

    with tokens_path.open("w", encoding="utf8") as handle:
        handle.write("Alpha\n")

    exit_code = main(
        [
            "--source",
            str(vectors_path),
            "--output",
            str(output_path),
            "--tokens",
            str(tokens_path),
            "--case-sensitive",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    payload = VectorLexicon.load_cache(output_path).entries

    assert "Alpha" in payload
    assert "beta" in payload["Alpha"]


def test_load_vector_source_expands_user_paths(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    vectors_path = home_dir / "vectors.json"

    embeddings = {"alpha": [1.0, 0.0], "beta": [0.0, 1.0]}
    with vectors_path.open("w", encoding="utf8") as handle:
        json.dump(embeddings, handle)

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))

    loaded = load_vector_source("~/vectors.json")
    assert loaded["alpha"] == [1.0, 0.0]


def test_load_vector_source_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(RuntimeError, match="does not exist"):
        load_vector_source(str(missing))


def test_vector_lexicon_save_cache_requires_path(toy_embeddings: dict[str, list[float]]) -> None:
    lexicon = VectorLexicon(source=toy_embeddings, max_neighbors=2, min_similarity=0.0)
    with pytest.raises(RuntimeError, match="No cache path"):
        lexicon.save_cache()


def _fake_find_spec(monkeypatch, target: str) -> None:
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == target:
            return types.SimpleNamespace(name=target)
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)


def _fake_import_module(monkeypatch, target: str, module: object) -> None:
    original = importlib.import_module

    def _patched(name: str, package: str | None = None):
        if name == target:
            return module
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", _patched)


def test_load_spacy_language_uses_stubbed_module(monkeypatch) -> None:
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

    result = _load_spacy_language("stub-model")
    assert result == "loaded:stub-model"
    assert calls["model"] == "stub-model"


def test_load_spacy_language_requires_dependency(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "spacy", raising=False)
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == "spacy":
            return None
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)

    with pytest.raises(RuntimeError, match="spaCy is required"):
        _load_spacy_language("missing-model")


def test_load_gensim_vectors_invokes_keyedvectors(monkeypatch, tmp_path: Path) -> None:
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

    kv_path = tmp_path / "vectors.kv"
    bin_path = tmp_path / "vectors.bin"
    gz_path = tmp_path / "vectors.gz"
    kv_path.touch()
    bin_path.touch()
    gz_path.touch()

    kv_result = _load_gensim_vectors(kv_path)
    bin_result = _load_gensim_vectors(bin_path)
    gz_result = _load_gensim_vectors(gz_path)

    assert kv_result == "kv-loaded"
    assert kv_calls == {"path": str(kv_path), "mmap": "r"}
    assert bin_result == "w2v:.bin"
    assert gz_result == "w2v:.gz"
    assert w2v_calls == [
        {"path": str(bin_path), "binary": True},
        {"path": str(gz_path), "binary": True},
    ]


def test_load_gensim_vectors_requires_dependency(monkeypatch, tmp_path: Path) -> None:
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == "gensim":
            return None
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)

    with pytest.raises(RuntimeError, match="gensim package is required"):
        _load_gensim_vectors(tmp_path / "missing.bin")


def test_build_sentence_transformer_embeddings_generates_vectors(monkeypatch) -> None:
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

    embeddings = _build_sentence_transformer_embeddings(
        "sentence-transformers/all-mpnet-base-v2",
        ["alpha", "beta", "alpha", ""],
    )

    assert embeddings == {"alpha": [1.0, 0.0], "beta": [0.0, 1.0]}
    assert stub_module.last_instance.name == "sentence-transformers/all-mpnet-base-v2"  # type: ignore[attr-defined]
    assert stub_module.encode_call["tokens"] == ["alpha", "beta"]  # type: ignore[index]
    assert stub_module.encode_call["batch_size"] == 64  # type: ignore[index]
    assert stub_module.encode_call["normalize"] is True  # type: ignore[index]
    assert stub_module.encode_call["convert"] is True  # type: ignore[index]


def test_build_sentence_transformer_embeddings_requires_dependency(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == "sentence_transformers":
            return None
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)

    with pytest.raises(RuntimeError, match="sentence-transformers is required"):
        _build_sentence_transformer_embeddings("model", ["alpha"])


def _make_fake_spacy_language():
    class _Strings:
        def __init__(self):
            self._to_int = {"alpha": 1, "beta": 2, "gamma": 3}
            self._to_str = {value: key for key, value in self._to_int.items()}

        def __contains__(self, item):
            if isinstance(item, str):
                return item in self._to_int
            if isinstance(item, int):
                return item in self._to_str
            return False

        def __getitem__(self, item):
            if isinstance(item, str):
                return self._to_int[item]
            return self._to_str[item]

    class _Vectors:
        def __init__(self, strings: _Strings):
            self._strings = strings
            self._vectors = {
                strings["alpha"]: [1.0, 0.0],
                strings["beta"]: [0.9, 0.1],
            }

        def __contains__(self, key: int) -> bool:
            return key in self._vectors

        def get(self, key: int):
            return self._vectors[key]

        def most_similar(self, _query, n: int):
            ordered = [self._strings["beta"], self._strings["alpha"]]
            scores = [0.95, 0.9]
            return [ordered[:n]], [scores[:n]]

        def keys(self):
            return self._vectors.keys()

    class _Vocab:
        def __init__(self):
            self.strings = _Strings()
            self.vectors = _Vectors(self.strings)

    class _Language:
        def __init__(self):
            self.vocab = _Vocab()

    return _Language()


def test_spacy_adapter_exposes_vocabulary(monkeypatch) -> None:
    fake_numpy = types.SimpleNamespace(asarray=lambda data, *_, **__: data)
    monkeypatch.delitem(sys.modules, "numpy", raising=False)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    _fake_find_spec(monkeypatch, "numpy")
    _fake_import_module(monkeypatch, "numpy", fake_numpy)

    language = _make_fake_spacy_language()
    adapter = _SpaCyAdapter(language)

    assert adapter.contains("alpha")
    assert not adapter.contains("delta")
    assert adapter.nearest("alpha", limit=2) == [("beta", 0.95)]
    assert adapter.nearest("missing", limit=2) == []
    assert list(adapter.iter_keys()) == ["alpha", "beta"]


def test_spacy_adapter_requires_numpy(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "numpy", raising=False)
    original = importlib.util.find_spec

    def _patched(name: str, package: str | None = None):
        if name == "numpy":
            return None
        return original(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", _patched)

    language = _make_fake_spacy_language()
    with pytest.raises(RuntimeError, match="NumPy"):
        _SpaCyAdapter(language)
