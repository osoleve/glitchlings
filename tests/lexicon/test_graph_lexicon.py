from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from glitchlings.lexicon.graph import GraphLexicon, _load_numberbatch


@pytest.fixture()
def toy_numberbatch() -> dict[str, list[float]]:
    return {
        "/c/en/alpha": [1.0, 0.0],
        "/c/en/beta": [0.9, 0.1],
        "/c/en/gamma": [0.1, 0.9],
        "/c/en/delta": [-1.0, 0.0],
        "/c/en/epsilon": [-0.8, -0.2],
        "/c/es/alpha": [1.0, 0.0],
    }


def test_graph_lexicon_sampling_and_normalization(
    toy_numberbatch: dict[str, list[float]]
) -> None:
    lexicon = GraphLexicon(source=toy_numberbatch, max_neighbors=3, seed=99)

    synonyms = lexicon.get_synonyms("Alpha!!", n=2)

    assert "beta" in {token.replace(" ", "") for token in synonyms}
    assert synonyms == lexicon.get_synonyms("alpha", n=2)


def test_graph_lexicon_lemmatization_variant(
    toy_numberbatch: dict[str, list[float]]
) -> None:
    lexicon = GraphLexicon(source=toy_numberbatch, max_neighbors=2)

    synonyms = lexicon.get_synonyms("ALPHAS", n=1)

    assert synonyms
    assert synonyms[0] != "alphas"


def test_graph_lexicon_missing_embeddings(tmp_path: Path) -> None:
    path = tmp_path / "missing.vec"
    lexicon = GraphLexicon(source=path)

    assert lexicon.get_synonyms("ghost", n=3) == []


def test_empty_queries_have_no_synonyms() -> None:
    lexicon = GraphLexicon(source={})
    assert lexicon.get_synonyms("!!!", n=2) == []


def test_graph_lexicon_save_cache_requires_path() -> None:
    lexicon = GraphLexicon(source={})
    with pytest.raises(RuntimeError, match="No cache path"):
        lexicon.save_cache()


def test_load_numberbatch_parses_gzipped_payload(tmp_path: Path) -> None:
    archive_path = tmp_path / "numberbatch_sample.txt.gz"
    with gzip.open(archive_path, "wt", encoding="utf8") as handle:
        handle.write("5 2\n")  # header indicating entry and dimension counts
        handle.write("/c/en/apple 1.0 0.0\n")
        handle.write("/c/en/banana 0.9 0.1\n")
        handle.write("/c/fr/pomme 0.8 0.2\n")  # non-English entry should be filtered
        handle.write("junk\n")  # ignored line with insufficient tokens
        handle.write("/c/en/cherry not_a_number 0.3\n")  # malformed vector skipped

    embeddings = _load_numberbatch(archive_path, languages={"en"})
    assert sorted(embeddings) == ["/c/en/apple", "/c/en/banana"]
    assert embeddings["/c/en/apple"] == [1.0, 0.0]
    assert embeddings["/c/en/banana"] == [0.9, 0.1]

    lexicon = GraphLexicon(source=archive_path, max_neighbors=1)
    synonyms = lexicon.get_synonyms("apple", n=1)
    assert synonyms
    assert "banana" in {token.replace(" ", "").lower() for token in synonyms}
