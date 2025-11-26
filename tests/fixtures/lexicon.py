"""Shared lexicon test infrastructure."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from glitchlings.lexicon import Lexicon


class MockLexicon(Lexicon):
    """Reusable mock lexicon for testing.

    This lexicon takes a fixed mapping of words to synonyms and returns
    them deterministically (after applying the internal sampling logic).

    Args:
        mapping: Dictionary mapping words to their available synonyms
        seed: Random seed for deterministic behavior

    Example:
        lexicon = MockLexicon({
            "happy": ["joyful", "glad", "pleased"],
            "sad": ["unhappy", "sorrowful"],
        })
        synonyms = lexicon.get_synonyms("happy", n=2)
    """

    def __init__(self, mapping: dict[str, Iterable[str]], *, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self._mapping = {
            key.lower(): [str(value) for value in values] for key, values in mapping.items()
        }

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        """Get synonyms for a word from the fixed mapping.

        Args:
            word: The word to find synonyms for
            pos: Part of speech (ignored in this mock)
            n: Maximum number of synonyms to return

        Returns:
            List of synonyms (up to n items)
        """
        entries = self._mapping.get(word.lower(), [])
        return self._deterministic_sample(entries, limit=n, word=word, pos=pos)


class TrackingLexicon(Lexicon):
    """Lexicon implementation that tracks method calls for testing.

    This is useful for verifying that glitchlings correctly interact with
    their lexicons (e.g., calling reseed at the right times).

    Example:
        lexicon = TrackingLexicon()
        lexicon.reseed(42)
        assert lexicon.reseed_calls == [42]
    """

    def __init__(self, *, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self.reseed_calls: list[int | None] = []
        self.get_synonyms_calls: list[tuple[str, str | None, int]] = []

    def reseed(self, seed: int | None) -> None:
        """Track reseed calls."""
        self.reseed_calls.append(seed)
        super().reseed(seed)

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        """Track synonym requests and return generated synonyms."""
        self.get_synonyms_calls.append((word, pos, n))
        candidates = [f"{word}_syn_{idx}" for idx in range(1, 6)]
        return self._deterministic_sample(candidates, limit=n, word=word, pos=pos)


@pytest.fixture
def toy_embeddings() -> dict[str, list[float]]:
    """Small test embeddings for VectorLexicon tests.

    These embeddings are designed to have clear similarity relationships:
    - alpha, beta, epsilon are close (high first component)
    - gamma is orthogonal
    - delta is opposite to alpha
    """
    return {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "epsilon": [0.8, 0.2],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }


@pytest.fixture
def shared_vector_embeddings() -> dict[str, list[float]]:
    """Shared vector embeddings for lexicon tests.

    This is a simplified version of toy_embeddings for tests that
    need fewer test vectors.
    """
    return {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }
