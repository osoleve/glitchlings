"""Tests for zoo/rng.py RNG boundary layer."""

from __future__ import annotations

import random

import pytest

from glitchlings.zoo.rng import (
    SEED_BIT_WIDTH,
    SEED_MASK,
    create_rng,
    derive_seed,
    resolve_seed,
    resolve_seed_deterministic,
    sample_random_float,
    sample_random_index,
    sample_random_int,
)


class TestConstants:
    """Tests for RNG constants."""

    def test_seed_bit_width(self) -> None:
        assert SEED_BIT_WIDTH == 64

    def test_seed_mask(self) -> None:
        assert SEED_MASK == 0xFFFFFFFFFFFFFFFF


class TestResolveSeed:
    """Tests for resolve_seed boundary function."""

    def test_explicit_seed_returned(self) -> None:
        assert resolve_seed(42, None) == 42

    def test_explicit_seed_takes_precedence(self) -> None:
        rng = random.Random(12345)
        assert resolve_seed(42, rng) == 42

    def test_large_seed_masked(self) -> None:
        large_seed = 2**70 + 123
        result = resolve_seed(large_seed, None)
        assert result == 123  # Only lower 64 bits

    def test_rng_sampling(self) -> None:
        rng = random.Random(12345)
        result = resolve_seed(None, rng)
        # Result should be a 64-bit int
        assert 0 <= result <= SEED_MASK

    def test_rng_sampling_deterministic(self) -> None:
        rng1 = random.Random(12345)
        rng2 = random.Random(12345)
        assert resolve_seed(None, rng1) == resolve_seed(None, rng2)

    def test_none_none_uses_global_random(self) -> None:
        # Just verify it returns something without crashing
        result = resolve_seed(None, None)
        assert 0 <= result <= SEED_MASK


class TestResolveSeedDeterministic:
    """Tests for resolve_seed_deterministic."""

    def test_explicit_seed_returned(self) -> None:
        assert resolve_seed_deterministic(42, None) == 42

    def test_rng_sampling(self) -> None:
        rng = random.Random(12345)
        result = resolve_seed_deterministic(None, rng)
        assert 0 <= result <= SEED_MASK

    def test_raises_when_both_none(self) -> None:
        with pytest.raises(ValueError, match="deterministic"):
            resolve_seed_deterministic(None, None)


class TestDeriveSeed:
    """Tests for derive_seed derivation function."""

    def test_derive_from_int(self) -> None:
        seed1 = derive_seed(12345, 0)
        seed2 = derive_seed(12345, 1)
        # Different components should produce different seeds
        assert seed1 != seed2

    def test_derive_deterministic(self) -> None:
        seed1 = derive_seed(12345, 0, 1)
        seed2 = derive_seed(12345, 0, 1)
        assert seed1 == seed2

    def test_derive_from_string(self) -> None:
        seed = derive_seed(12345, "typogre")
        assert 0 <= seed <= SEED_MASK

    def test_derive_different_strings_different_seeds(self) -> None:
        seed1 = derive_seed(12345, "typogre")
        seed2 = derive_seed(12345, "mim1c")
        assert seed1 != seed2

    def test_derive_multiple_components(self) -> None:
        seed = derive_seed(12345, 0, "child", 99)
        assert 0 <= seed <= SEED_MASK


class TestCreateRng:
    """Tests for create_rng helper."""

    def test_creates_random_instance(self) -> None:
        rng = create_rng(42)
        assert isinstance(rng, random.Random)

    def test_deterministic(self) -> None:
        rng1 = create_rng(42)
        rng2 = create_rng(42)
        assert rng1.random() == rng2.random()


class TestRandomSampling:
    """Tests for random sampling helpers."""

    def test_sample_random_float_range(self) -> None:
        rng = random.Random(42)
        for _ in range(100):
            val = sample_random_float(rng)
            assert 0.0 <= val < 1.0

    def test_sample_random_int_range(self) -> None:
        rng = random.Random(42)
        for _ in range(100):
            val = sample_random_int(rng, low=5, high=10)
            assert 5 <= val <= 10

    def test_sample_random_index_range(self) -> None:
        rng = random.Random(42)
        for _ in range(100):
            idx = sample_random_index(rng, 10)
            assert 0 <= idx < 10

    def test_sample_random_index_empty_raises(self) -> None:
        rng = random.Random(42)
        with pytest.raises(ValueError, match="empty"):
            sample_random_index(rng, 0)

    def test_sample_random_index_negative_raises(self) -> None:
        rng = random.Random(42)
        with pytest.raises(ValueError, match="empty"):
            sample_random_index(rng, -1)
