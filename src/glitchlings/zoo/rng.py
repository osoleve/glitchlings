"""RNG boundary layer for seed resolution.

This module provides the interface between RNG state and concrete random values.
All randomness in the glitchlings library flows through these functions.

Design Philosophy
-----------------
RNG management is an *impure* operation - it involves stateful objects
(random.Random) and non-deterministic behavior when no seed is provided.
This module provides the boundary layer that converts RNG state into
concrete values that can be passed to pure functions.

The pattern is:
    1. User provides `seed: int | None` and/or `rng: random.Random | None`
    2. Boundary layer resolves to a concrete `int` via `resolve_seed()`
    3. Pure/Rust functions receive the concrete seed value

This separation means:
    - Pure transformation code never touches RNG objects
    - Tests can provide explicit seed values for reproducibility
    - RNG state management is isolated to the boundary

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import random
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bit width for seed values (64-bit for compatibility with Rust u64)
SEED_BIT_WIDTH = 64
SEED_MASK = (1 << SEED_BIT_WIDTH) - 1  # 0xFFFFFFFFFFFFFFFF

# FNV-1a constants for 64-bit hashing (fast, simple string hashing)
_FNV_OFFSET_BASIS = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3

# SplitMix64 constants (standard PRNG seed mixer)
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
_SPLITMIX_MIX1 = 0xBF58476D1CE4E5B9
_SPLITMIX_MIX2 = 0x94D049BB133111EB


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class RandomBitsSource(Protocol):
    """Protocol for objects that can provide random bits."""

    def getrandbits(self, k: int) -> int:
        """Return a non-negative integer with k random bits."""
        ...


# ---------------------------------------------------------------------------
# Core Boundary Functions
# ---------------------------------------------------------------------------


def resolve_seed(
    seed: int | None,
    rng: random.Random | None,
) -> int:
    """Resolve a seed from optional explicit seed or RNG state.

    This is the primary boundary function for RNG resolution. Call this
    once at the boundary layer, then pass the resulting int to all
    downstream pure/Rust functions.

    Args:
        seed: Explicit seed value. If provided, takes precedence over rng.
        rng: Random generator to sample from if seed is None.

    Returns:
        A 64-bit unsigned integer suitable for Rust FFI.

    Note:
        If both seed and rng are None, uses module-level random state.
        This is non-deterministic and should only happen at top-level CLI usage.

    Examples:
        >>> resolve_seed(42, None)  # explicit seed
        42
        >>> rng = random.Random(123)
        >>> resolve_seed(None, rng)  # sample from RNG
        14522756016584210807
    """
    if seed is not None:
        return int(seed) & SEED_MASK
    if rng is not None:
        return rng.getrandbits(SEED_BIT_WIDTH)
    return random.getrandbits(SEED_BIT_WIDTH)


def resolve_seed_deterministic(
    seed: int | None,
    rng: random.Random | None,
) -> int:
    """Resolve a seed, requiring explicit seed or RNG.

    Like resolve_seed(), but raises ValueError if both seed and rng are None.
    Use this when non-deterministic behavior would be a bug.

    Args:
        seed: Explicit seed value.
        rng: Random generator to sample from.

    Returns:
        A 64-bit unsigned integer.

    Raises:
        ValueError: If both seed and rng are None.
    """
    if seed is not None:
        return int(seed) & SEED_MASK
    if rng is not None:
        return rng.getrandbits(SEED_BIT_WIDTH)
    raise ValueError("Either seed or rng must be provided for deterministic behavior")


# ---------------------------------------------------------------------------
# Seed Derivation (Deterministic)
# ---------------------------------------------------------------------------


def _fnv1a_hash(data: bytes) -> int:
    """FNV-1a 64-bit hash of bytes.

    Fast, simple string hashing with good distribution.
    No cryptographic properties needed for seed derivation.
    """
    h = _FNV_OFFSET_BASIS
    for byte in data:
        h ^= byte
        h = (h * _FNV_PRIME) & SEED_MASK
    return h


def _splitmix64(state: int) -> int:
    """SplitMix64 mixing function.

    Standard PRNG seed mixer used by Java's SplittableRandom
    and Rust's rand crate. Provides excellent avalanche properties.
    """
    state = (state + _SPLITMIX_GAMMA) & SEED_MASK
    state = ((state ^ (state >> 30)) * _SPLITMIX_MIX1) & SEED_MASK
    state = ((state ^ (state >> 27)) * _SPLITMIX_MIX2) & SEED_MASK
    return (state ^ (state >> 31)) & SEED_MASK


def derive_seed(base_seed: int, *components: int | str) -> int:
    """Derive a new seed from a base seed and components.

    This is a pure function for hierarchical seed derivation.
    Used by Gaggle to give each glitchling a unique but reproducible seed.

    Uses FNV-1a for string hashing and SplitMix64 for mixing. This provides
    stable, deterministic derivation across interpreter runs without the
    overhead of cryptographic hashing.

    Args:
        base_seed: The parent seed.
        *components: Additional components to mix in (integers or strings).

    Returns:
        A derived 64-bit seed.

    Examples:
        >>> derive_seed(12345, 0)  # first child
        2454886589211414944
        >>> derive_seed(12345, 1)  # second child
        18133564086679993456
        >>> derive_seed(12345, "typogre")  # named child
        1187037253482581891
    """
    state = base_seed & SEED_MASK

    for component in components:
        if isinstance(component, str):
            # Hash string to u64 via FNV-1a, then XOR into state
            state ^= _fnv1a_hash(component.encode("utf-8"))
        else:
            # XOR integer directly (masked to 64 bits)
            state ^= abs(component) & SEED_MASK

        # Mix with SplitMix64 after each component
        state = _splitmix64(state)

    return state


# ---------------------------------------------------------------------------
# Random Value Generation (Impure)
# ---------------------------------------------------------------------------


def create_rng(seed: int) -> random.Random:
    """Create a new Random instance from a seed.

    Use this when you need to create child RNG states for parallel operations.
    Prefer passing concrete seed values to functions when possible.

    Args:
        seed: The seed for the new RNG.

    Returns:
        A new random.Random instance.
    """
    return random.Random(seed)


def sample_random_float(rng: random.Random) -> float:
    """Sample a random float in [0.0, 1.0) from an RNG.

    Args:
        rng: The random generator.

    Returns:
        Float in range [0.0, 1.0).
    """
    return rng.random()


def sample_random_int(rng: random.Random, *, low: int, high: int) -> int:
    """Sample a random integer in [low, high] inclusive.

    Args:
        rng: The random generator.
        low: Minimum value (inclusive).
        high: Maximum value (inclusive).

    Returns:
        Random integer in range [low, high].
    """
    return rng.randint(low, high)


def sample_random_index(rng: random.Random, length: int) -> int:
    """Sample a random index for a sequence of given length.

    Args:
        rng: The random generator.
        length: The sequence length.

    Returns:
        Random index in range [0, length).

    Raises:
        ValueError: If length <= 0.
    """
    if length <= 0:
        raise ValueError("Cannot sample index from empty sequence")
    return rng.randrange(length)


__all__ = [
    # Constants
    "SEED_BIT_WIDTH",
    "SEED_MASK",
    # Protocols
    "RandomBitsSource",
    # Boundary functions
    "resolve_seed",
    "resolve_seed_deterministic",
    # Derivation
    "derive_seed",
    # RNG operations (impure)
    "create_rng",
    "sample_random_float",
    "sample_random_int",
    "sample_random_index",
]
