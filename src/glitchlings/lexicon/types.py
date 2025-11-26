"""Pure type definitions for lexicon abstractions.

This module contains only type definitions, protocols, and dataclasses with no
side effects. It can be safely imported anywhere without triggering IO or
module loading.

Pure guarantees:
- No import side effects
- No file IO
- No RNG instantiation
- No mutable global state
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class SynonymQuery:
    """Immutable representation of a synonym lookup request."""

    word: str
    pos: str | None = None
    limit: int = 5


@dataclass(frozen=True, slots=True)
class SynonymResult:
    """Immutable result of a synonym lookup.

    Attributes:
        word: The original query word.
        synonyms: Ordered list of synonym candidates.
        pos: Part-of-speech filter applied, if any.
        seed_material: Opaque value used to derive deterministic samples.
    """

    word: str
    synonyms: tuple[str, ...]
    pos: str | None = None
    seed_material: str | None = None

    def sample(self, indices: Sequence[int]) -> tuple[str, ...]:
        """Return synonyms at the given indices.

        This is a pure function - indices must be pre-computed by the caller.

        Args:
            indices: Sorted indices into the synonyms tuple.

        Returns:
            Tuple of selected synonyms in index order.
        """
        return tuple(self.synonyms[i] for i in indices if i < len(self.synonyms))


@runtime_checkable
class SynonymProvider(Protocol):
    """Protocol for objects that can provide synonym lookups.

    This is the minimal interface required for synonym retrieval.
    Implementations may be backed by caches, databases, or live APIs.
    """

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        """Return up to ``n`` synonyms for ``word`` constrained by ``pos``."""
        ...


@runtime_checkable
class SynonymBackend(SynonymProvider, Protocol):
    """Extended protocol for backends that support POS queries."""

    def supports_pos(self, pos: str | None) -> bool:
        """Return ``True`` when the backend can service ``pos`` queries."""
        ...


@runtime_checkable
class CacheableSynonymBackend(SynonymBackend, Protocol):
    """Protocol for backends that support cache persistence."""

    def save_cache(self, path: str | None = None) -> str | None:
        """Persist the backend cache to ``path`` and return the destination."""
        ...


# Type aliases for cache structures
CacheEntries = dict[str, list[str]]
"""Mapping of words to their synonym lists."""


@dataclass(frozen=True, slots=True)
class CacheSnapshot:
    """Materialised cache data and its integrity checksum.

    This is an immutable snapshot of cache state that can be passed
    between pure functions without side effects.
    """

    entries: CacheEntries
    checksum: str | None = None


def empty_cache() -> CacheSnapshot:
    """Return an empty cache snapshot."""
    return CacheSnapshot(entries={}, checksum=None)


__all__ = [
    # Query/Result types
    "SynonymQuery",
    "SynonymResult",
    # Protocols
    "SynonymProvider",
    "SynonymBackend",
    "CacheableSynonymBackend",
    # Cache types
    "CacheEntries",
    "CacheSnapshot",
    "empty_cache",
]
