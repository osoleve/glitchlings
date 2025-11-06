from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from glitchlings.lexicon.vector import VectorLexicon


def test_backend_cache_roundtrip(
    tmp_path: Path,
    shared_vector_embeddings: dict[str, list[float]],
) -> None:
    backend_cls: type[Any] = VectorLexicon
    kwargs: dict[str, Any] = {
        "source": shared_vector_embeddings,
        "max_neighbors": 2,
        "min_similarity": 0.05,
    }
    restore_kwargs: dict[str, Any] = {"source": None}

    word = "alpha"
    cache_path = tmp_path / "vector_cache.json"
    lexicon = backend_cls(cache_path=cache_path, **kwargs)
    lexicon.precompute(word)
    saved_path = lexicon.save_cache()
    snapshot = backend_cls.load_cache(saved_path)
    assert snapshot.entries  # cache contains data
    assert snapshot.checksum is not None
    restored = backend_cls(cache_path=saved_path, **restore_kwargs)
    assert restored.get_synonyms(word, n=2) == lexicon.get_synonyms(word, n=2)


def test_cache_checksum_verification(
    tmp_path: Path, shared_vector_embeddings: dict[str, list[float]]
) -> None:
    cache_path = tmp_path / "vector_cache.json"
    lexicon = VectorLexicon(source=shared_vector_embeddings, max_neighbors=2, min_similarity=0.05)
    lexicon.precompute("alpha")
    lexicon.save_cache(cache_path)

    with cache_path.open("r", encoding="utf8") as handle:
        payload = json.load(handle)

    payload["entries"]["alpha"].append("corrupt")  # type: ignore[index]

    with cache_path.open("w", encoding="utf8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    with pytest.raises(RuntimeError):
        VectorLexicon.load_cache(cache_path)
