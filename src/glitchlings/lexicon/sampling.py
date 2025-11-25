"""Deterministic sampling functions for synonym selection.

This module provides referentially transparent sampling functions - identical
inputs always produce identical outputs. While `compute_sample_indices` uses
`random.Random` internally for compatibility, it never exposes RNG state to
callers and produces deterministic results from the given seed.

Referential Transparency Guarantees:
- derive_sampling_seed: Pure hash function, no state
- compute_sample_indices: Deterministic (encapsulates temporary RNG)
- sample_values: Pure selection by index
- deterministic_sample: Deterministic composition of the above

Design Pattern
--------------
The boundary layer (Lexicon ABC) stores the base seed. These functions:
1. Derive a query-specific seed (pure hash)
2. Compute indices deterministically (encapsulated RNG)
3. Select values by index (pure)

This separation means:
- Callers never manage RNG state directly
- Same seed/word/pos always produces same samples
- Testing is straightforward with explicit seeds
"""

from __future__ import annotations

import random
from hashlib import blake2s
from typing import Sequence


def derive_sampling_seed(word: str, pos: str | None, base_seed: int | None) -> int:
    """Derive a deterministic seed from word, POS, and base seed.

    This is a pure hash function - no RNG state is created or modified.

    Args:
        word: The query word to sample synonyms for.
        pos: Optional part-of-speech filter.
        base_seed: Base seed from the lexicon configuration.

    Returns:
        A 64-bit integer suitable for deterministic sampling.

    Examples:
        >>> derive_sampling_seed("hello", None, 42)
        7458907270398921413
        >>> derive_sampling_seed("hello", "n", 42)
        16553879851749481605
        >>> derive_sampling_seed("hello", None, None)  # Still deterministic per-word
        10668285397552454583
    """
    seed_material = blake2s(digest_size=8)
    seed_material.update(word.lower().encode("utf8"))
    if pos is not None:
        seed_material.update(pos.lower().encode("utf8"))
    seed_repr = "None" if base_seed is None else str(base_seed)
    seed_material.update(seed_repr.encode("utf8"))
    return int.from_bytes(seed_material.digest(), "big", signed=False)


def compute_sample_indices(
    collection_size: int,
    sample_size: int,
    seed: int,
) -> tuple[int, ...]:
    """Compute deterministic indices for sampling from a collection.

    Uses the same algorithm as random.Random.sample() for compatibility
    with existing behavior. The function creates a temporary RNG internally
    but does not expose it - this is a pure function from the caller's
    perspective since identical inputs always produce identical outputs.

    Args:
        collection_size: Total number of items available.
        sample_size: Maximum number of items to select.
        seed: Deterministic seed for index selection.

    Returns:
        Sorted tuple of indices to select, never exceeding collection_size.

    Examples:
        >>> compute_sample_indices(10, 3, 12345)
        (2, 5, 7)
        >>> compute_sample_indices(3, 5, 12345)  # Can't sample more than available
        (0, 1, 2)
    """
    if collection_size <= 0:
        return ()

    if sample_size >= collection_size:
        return tuple(range(collection_size))

    # Use random.Random internally for compatibility with existing behavior.
    # This is deterministic (same seed -> same output) so the function
    # remains pure from the caller's perspective.
    rng = random.Random(seed)
    indices = rng.sample(range(collection_size), k=sample_size)
    indices.sort()
    return tuple(indices)


def sample_values(
    values: Sequence[str],
    indices: Sequence[int],
) -> list[str]:
    """Select values at the given indices.

    This is a pure selection function - indices must be pre-computed.

    Args:
        values: Sequence of candidate values.
        indices: Indices of values to select (must be in bounds).

    Returns:
        List of selected values in index order.
    """
    return [values[i] for i in indices if 0 <= i < len(values)]


def deterministic_sample(
    values: Sequence[str],
    *,
    limit: int,
    word: str,
    pos: str | None,
    base_seed: int | None,
) -> list[str]:
    """Sample up to ``limit`` values deterministically.

    This is a convenience function that composes derive_sampling_seed,
    compute_sample_indices, and sample_values. It remains pure because
    all randomness is derived from the explicit seed parameter.

    Args:
        values: Full sequence of candidate values.
        limit: Maximum number of values to return.
        word: Query word used to derive the sampling seed.
        pos: Optional POS tag used in seed derivation.
        base_seed: Base seed from lexicon configuration.

    Returns:
        List of sampled values, sorted by original index.

    Examples:
        >>> deterministic_sample(["a", "b", "c", "d"], limit=2, word="test", pos=None, base_seed=42)
        ['a', 'd']
    """
    if limit <= 0:
        return []

    if len(values) <= limit:
        return list(values)

    seed = derive_sampling_seed(word, pos, base_seed)
    indices = compute_sample_indices(len(values), limit, seed)
    return sample_values(values, indices)


__all__ = [
    "compute_sample_indices",
    "derive_sampling_seed",
    "deterministic_sample",
    "sample_values",
]
