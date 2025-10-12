from __future__ import annotations

from pathlib import Path

import pytest

from glitchlings.lexicon.graph import GraphLexicon


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
