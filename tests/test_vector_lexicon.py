from __future__ import annotations

import json
from pathlib import Path

import pytest

from glitchlings.lexicon.vector import (
    VectorLexicon,
    build_vector_cache,
    load_vector_source,
    main,
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
