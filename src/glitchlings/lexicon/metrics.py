"""Utility helpers for evaluating lexicon coverage and quality."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing hint only
    from . import Lexicon


def _unique_synonyms(
    lexicon: "Lexicon",
    word: str,
    *,
    pos: str | None,
    sample_size: int,
) -> list[str]:
    """Return unique synonym candidates excluding the original token."""

    collected: list[str] = []
    seen: set[str] = set()
    source = word.lower()
    for synonym in lexicon.get_synonyms(word, pos=pos, n=sample_size):
        normalized = synonym.lower()
        if normalized == source:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        collected.append(synonym)
    return collected


def synonym_diversity(
    lexicon: "Lexicon",
    words: Iterable[str],
    *,
    pos: str | None = None,
    sample_size: int = 5,
) -> float:
    """Return the mean unique-synonym count for ``words`` using ``lexicon``."""

    totals = []
    for word in words:
        synonyms = _unique_synonyms(lexicon, word, pos=pos, sample_size=sample_size)
        totals.append(len(synonyms))
    if not totals:
        return 0.0
    return sum(totals) / len(totals)


def coverage_ratio(
    lexicon: "Lexicon",
    words: Iterable[str],
    *,
    pos: str | None = None,
    sample_size: int = 5,
    min_synonyms: int = 3,
) -> float:
    """Return the fraction of ``words`` with at least ``min_synonyms`` candidates."""

    total = 0
    hits = 0
    for word in words:
        total += 1
        synonyms = _unique_synonyms(lexicon, word, pos=pos, sample_size=sample_size)
        if len(synonyms) >= min_synonyms:
            hits += 1
    if total == 0:
        return 0.0
    return hits / total


def _cosine_similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for value_a, value_b in zip(vector_a, vector_b):
        dot += value_a * value_b
        norm_a += value_a * value_a
        norm_b += value_b * value_b
    magnitude = math.sqrt(norm_a) * math.sqrt(norm_b)
    if magnitude == 0.0:
        return 0.0
    return dot / magnitude


def mean_cosine_similarity(
    lexicon: "Lexicon",
    embeddings: Mapping[str, Sequence[float]],
    words: Iterable[str],
    *,
    pos: str | None = None,
    sample_size: int = 5,
) -> float:
    """Return the mean cosine similarity between each word and its candidates."""

    total = 0.0
    count = 0
    for word in words:
        source_vector = embeddings.get(word)
        if source_vector is None:
            continue
        synonyms = _unique_synonyms(lexicon, word, pos=pos, sample_size=sample_size)
        for synonym in synonyms:
            synonym_vector = embeddings.get(synonym)
            if synonym_vector is None:
                continue
            total += _cosine_similarity(source_vector, synonym_vector)
            count += 1
    if count == 0:
        return 0.0
    return total / count


def compare_lexicons(
    baseline: "Lexicon",
    candidate: "Lexicon",
    words: Iterable[str],
    *,
    pos: str | None = None,
    sample_size: int = 5,
    min_synonyms: int = 3,
    embeddings: Mapping[str, Sequence[float]] | None = None,
) -> dict[str, float]:
    """Return comparative coverage and diversity statistics for two lexicons."""

    stats = {
        "baseline_diversity": synonym_diversity(
            baseline, words, pos=pos, sample_size=sample_size
        ),
        "candidate_diversity": synonym_diversity(
            candidate, words, pos=pos, sample_size=sample_size
        ),
        "baseline_coverage": coverage_ratio(
            baseline,
            words,
            pos=pos,
            sample_size=sample_size,
            min_synonyms=min_synonyms,
        ),
        "candidate_coverage": coverage_ratio(
            candidate,
            words,
            pos=pos,
            sample_size=sample_size,
            min_synonyms=min_synonyms,
        ),
    }

    if embeddings is not None:
        stats["baseline_similarity"] = mean_cosine_similarity(
            baseline, embeddings, words, pos=pos, sample_size=sample_size
        )
        stats["candidate_similarity"] = mean_cosine_similarity(
            candidate, embeddings, words, pos=pos, sample_size=sample_size
        )

    return stats


__all__ = [
    "compare_lexicons",
    "coverage_ratio",
    "mean_cosine_similarity",
    "synonym_diversity",
]
