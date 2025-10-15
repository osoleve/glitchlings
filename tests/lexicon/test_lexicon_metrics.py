from __future__ import annotations

from typing import Iterable

import pytest

from glitchlings.lexicon import (
    Lexicon,
    compare_lexicons,
    coverage_ratio,
    synonym_diversity,
)


class StubLexicon(Lexicon):
    """In-memory lexicon used to model WordNet baseline behaviour in tests."""

    def __init__(self, mapping: dict[str, Iterable[str]], *, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self._mapping = {
            key.lower(): [str(value) for value in values]
            for key, values in mapping.items()
        }

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        entries = self._mapping.get(word.lower(), [])
        return self._deterministic_sample(entries, limit=n, word=word, pos=pos)


@pytest.fixture()
def sample_words() -> list[str]:
    return ["alpha", "beta", "gamma"]


def test_synonym_diversity_and_coverage_compare_to_wordnet_baseline(
    sample_words: list[str],
) -> None:
    baseline = StubLexicon(
        {
            "alpha": ["aleph", "alfa"],
            "beta": ["beth"],
            "gamma": ["gimel", "gamma_ray", "gamma_particle"],
        }
    )
    candidate = StubLexicon(
        {
            "alpha": ["alfa", "alph", "alpha_wave"],
            "beta": ["beth", "vet", "vita"],
            "gamma": ["gimel", "gamma_wave", "gamma_radiation"],
        }
    )

    baseline_diversity = synonym_diversity(baseline, sample_words, sample_size=4)
    candidate_diversity = synonym_diversity(candidate, sample_words, sample_size=4)
    assert candidate_diversity >= baseline_diversity

    baseline_coverage = coverage_ratio(
        baseline,
        sample_words,
        sample_size=4,
        min_synonyms=2,
    )
    candidate_coverage = coverage_ratio(
        candidate,
        sample_words,
        sample_size=4,
        min_synonyms=2,
    )
    assert candidate_coverage >= baseline_coverage

    stats = compare_lexicons(
        baseline,
        candidate,
        sample_words,
        sample_size=4,
        min_synonyms=2,
    )
    assert stats["candidate_diversity"] == candidate_diversity
    assert stats["candidate_coverage"] == candidate_coverage


def test_mean_cosine_similarity_tracks_candidate_quality() -> None:
    words = ["alpha", "beta"]
    baseline = StubLexicon(
        {
            "alpha": ["aleph"],
            "beta": ["beth"],
        }
    )
    candidate = StubLexicon(
        {
            "alpha": ["alpha_wave", "alpha_state"],
            "beta": ["beta_wave", "beta_state"],
        }
    )
    embeddings = {
        "alpha": (1.0, 0.0),
        "aleph": (0.95, 0.05),
        "alpha_wave": (0.9, 0.1),
        "alpha_state": (0.88, 0.12),
        "beta": (0.0, 1.0),
        "beth": (0.05, 0.95),
        "beta_wave": (0.1, 0.9),
        "beta_state": (0.12, 0.88),
    }

    stats = compare_lexicons(
        baseline,
        candidate,
        words,
        sample_size=3,
        min_synonyms=1,
        embeddings=embeddings,
    )

    assert stats["baseline_similarity"] == pytest.approx(0.9986, rel=1e-4)
    assert stats["candidate_similarity"] == pytest.approx(0.9923, rel=1e-4)
    assert stats["baseline_similarity"] > stats["candidate_similarity"]
    assert stats["candidate_diversity"] > stats["baseline_diversity"]
