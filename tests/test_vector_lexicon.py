from __future__ import annotations

import json
from pathlib import Path

import pytest

from glitchlings.lexicon.vector import VectorLexicon, build_vector_cache, main


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


def test_vector_lexicon_cache_roundtrip(tmp_path: Path, toy_embeddings: dict[str, list[float]]) -> None:
    cache_path = tmp_path / "cache.json"
    lexicon = VectorLexicon(
        source=toy_embeddings,
        max_neighbors=2,
        min_similarity=0.05,
    )
    lexicon.precompute("alpha")
    lexicon.save_cache(cache_path)

    restored = VectorLexicon(cache_path=cache_path)
    assert restored.get_synonyms("alpha", n=2) == lexicon.get_synonyms("alpha", n=2)


def test_build_vector_cache_helper(tmp_path: Path, toy_embeddings: dict[str, list[float]]) -> None:
    output_path = tmp_path / "cache.json"
    build_vector_cache(source=toy_embeddings, words=["alpha", "gamma"], output_path=output_path)

    with output_path.open("r", encoding="utf8") as handle:
        cache = json.load(handle)

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

    with output_path.open("r", encoding="utf8") as handle:
        payload = json.load(handle)

    assert sorted(payload) == ["alpha", "delta"]
