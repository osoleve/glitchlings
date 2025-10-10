from __future__ import annotations

import pytest

from glitchlings.lexicon.vector import VectorLexicon
from glitchlings.zoo.jargoyle import substitute_random_synonyms


def _clean_tokens(text: str) -> list[str]:
    return [token.strip(".,") for token in text.split()]


@pytest.fixture()
def vector_lexicon() -> VectorLexicon:
    embeddings = {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }
    return VectorLexicon(source=embeddings, max_neighbors=2, min_similarity=0.05)


def test_jargoyle_multiple_pos_targets_change_words():
    text = "They sing happy songs."
    result = substitute_random_synonyms(
        text,
        rate=1.0,
        part_of_speech=("v", "a"),
        seed=123,
    )

    original_tokens = _clean_tokens(text)
    result_tokens = _clean_tokens(result)

    # Expect both verb and adjective replacements to differ from input
    changed = {
        orig for orig, new in zip(original_tokens, result_tokens) if orig != new
    }
    assert {"sing", "happy"} <= changed


def test_jargoyle_any_includes_all_supported_pos():
    text = "They sing happy songs quickly."
    result = substitute_random_synonyms(
        text,
        rate=1.0,
        part_of_speech="any",
        seed=99,
    )

    original_tokens = _clean_tokens(text)
    result_tokens = _clean_tokens(result)

    changed = {
        orig for orig, new in zip(original_tokens, result_tokens) if orig != new
    }
    assert {"sing", "happy", "songs", "quickly"} <= changed


def test_jargoyle_custom_lexicon_deterministic(vector_lexicon: VectorLexicon) -> None:
    text = "alpha beta"

    first = substitute_random_synonyms(
        text,
        rate=1.0,
        seed=2024,
        lexicon=vector_lexicon,
    )
    second = substitute_random_synonyms(
        text,
        rate=1.0,
        seed=2024,
        lexicon=vector_lexicon,
    )

    assert first == second
    assert first != text
