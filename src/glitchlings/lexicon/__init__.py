"""Lexicon abstractions and default backend resolution helpers."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from hashlib import blake2s
from pathlib import Path
from typing import Callable, Iterable

from glitchlings.conf import get_config

from ._cache import CacheEntries, CacheSnapshot


class Lexicon(ABC):
    """Abstract interface describing synonym lookup backends.

    Parameters
    ----------
    seed:
        Optional integer used to derive deterministic random number generators
        for synonym sampling. Identical seeds guarantee reproducible results for
        the same word/part-of-speech queries.

    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._seed = seed

    @property
    def seed(self) -> int | None:
        """Return the current base seed used for deterministic sampling."""
        return self._seed

    def reseed(self, seed: int | None) -> None:
        """Update the base seed driving deterministic synonym sampling."""
        self._seed = seed

    def _derive_rng(self, word: str, pos: str | None) -> random.Random:
        """Return an RNG derived from the base seed, word, and POS tag."""
        seed_material = blake2s(digest_size=8)
        seed_material.update(word.lower().encode("utf8"))
        if pos is not None:
            seed_material.update(pos.lower().encode("utf8"))
        seed_repr = "None" if self._seed is None else str(self._seed)
        seed_material.update(seed_repr.encode("utf8"))
        derived_seed = int.from_bytes(seed_material.digest(), "big", signed=False)
        return random.Random(derived_seed)

    def _deterministic_sample(
        self, values: Iterable[str], *, limit: int, word: str, pos: str | None
    ) -> list[str]:
        """Return up to ``limit`` values sampled deterministically."""
        if limit <= 0:
            return []

        items = list(values)
        if len(items) <= limit:
            return items

        rng = self._derive_rng(word, pos)
        indices = rng.sample(range(len(items)), k=limit)
        indices.sort()
        return [items[index] for index in indices]

    @abstractmethod
    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        """Return up to ``n`` synonyms for ``word`` constrained by ``pos``."""

    def supports_pos(self, pos: str | None) -> bool:
        """Return ``True`` when the backend can service ``pos`` queries."""
        return True

    def __repr__(self) -> str:  # pragma: no cover - trivial representation
        return f"{self.__class__.__name__}(seed={self._seed!r})"


class LexiconBackend(Lexicon):
    """Extended lexicon interface that supports cache persistence."""

    Cache = CacheEntries

    @classmethod
    @abstractmethod
    def load_cache(cls, path: str | Path) -> CacheSnapshot:
        """Return a validated cache snapshot loaded from ``path``."""

    @abstractmethod
    def save_cache(self, path: str | Path | None = None) -> Path | None:
        """Persist the backend cache to ``path`` and return the destination."""


from .metrics import (  # noqa: E402
    compare_lexicons,
    coverage_ratio,
    mean_cosine_similarity,
    synonym_diversity,
)
from .vector import VectorLexicon, build_vector_cache  # noqa: E402

_WordNetLexicon: type[LexiconBackend] | None
try:  # pragma: no cover - optional dependency
    from .wordnet import WordNetLexicon as _WordNetLexicon
except (
    ImportError,
    ModuleNotFoundError,
    AttributeError,
):  # pragma: no cover - triggered when nltk unavailable
    _WordNetLexicon = None

WordNetLexicon: type[LexiconBackend] | None = _WordNetLexicon


_BACKEND_FACTORIES: dict[str, Callable[[int | None], Lexicon | None]] = {}


def register_backend(name: str, factory: Callable[[int | None], Lexicon | None]) -> None:
    """Register ``factory`` for ``name`` so it can be selected via config."""
    normalized = name.lower()
    _BACKEND_FACTORIES[normalized] = factory


def unregister_backend(name: str) -> None:
    """Remove a previously registered backend."""
    _BACKEND_FACTORIES.pop(name.lower(), None)


def available_backends() -> list[str]:
    """Return the names of registered lexicon factories."""
    return sorted(_BACKEND_FACTORIES)


def _vector_backend(seed: int | None) -> Lexicon | None:
    config = get_config()
    cache_path = config.lexicon.vector_cache
    if cache_path is None:
        return None
    if not cache_path.exists():
        return None
    return VectorLexicon(cache_path=cache_path, seed=seed)


def _wordnet_backend(seed: int | None) -> Lexicon | None:  # pragma: no cover - optional
    if WordNetLexicon is None:
        return None
    try:
        lexicon = WordNetLexicon(seed=seed)
    except RuntimeError:
        return None
    return lexicon


register_backend("vector", _vector_backend)
register_backend("wordnet", _wordnet_backend)


def get_default_lexicon(seed: int | None = None) -> Lexicon:
    """Return the first available lexicon according to configuration priority."""
    config = get_config()
    attempts: list[str] = []
    for name in config.lexicon.priority:
        factory = _BACKEND_FACTORIES.get(name.lower())
        if factory is None:
            attempts.append(f"{name} (unknown)")
            continue
        lexicon = factory(seed)
        if lexicon is not None:
            return lexicon
        attempts.append(f"{name} (unavailable)")
    attempted = ", ".join(attempts) or "<none>"
    raise RuntimeError(
        "No lexicon backends available; configure lexicon.priority with at least one "
        f"working backend. Attempts: {attempted}."
    )


__all__ = [
    "Lexicon",
    "LexiconBackend",
    "VectorLexicon",
    "WordNetLexicon",
    "build_vector_cache",
    "compare_lexicons",
    "coverage_ratio",
    "mean_cosine_similarity",
    "synonym_diversity",
    "get_default_lexicon",
    "register_backend",
    "unregister_backend",
    "available_backends",
]
