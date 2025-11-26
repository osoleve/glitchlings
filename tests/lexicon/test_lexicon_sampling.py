"""Tests for deterministic sampling functions."""

from __future__ import annotations

from glitchlings.lexicon.sampling import (
    compute_sample_indices,
    derive_sampling_seed,
    deterministic_sample,
    sample_values,
)


class TestDeriveSamplingSeed:
    """Tests for derive_sampling_seed function."""

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs always produce same output."""
        seed1 = derive_sampling_seed("hello", None, 42)
        seed2 = derive_sampling_seed("hello", None, 42)
        assert seed1 == seed2

    def test_different_words(self) -> None:
        """Different words produce different seeds."""
        seed1 = derive_sampling_seed("hello", None, 42)
        seed2 = derive_sampling_seed("world", None, 42)
        assert seed1 != seed2

    def test_different_pos(self) -> None:
        """Different POS tags produce different seeds."""
        seed1 = derive_sampling_seed("run", "n", 42)
        seed2 = derive_sampling_seed("run", "v", 42)
        assert seed1 != seed2

    def test_pos_none_vs_explicit(self) -> None:
        """None POS vs explicit POS produce different seeds."""
        seed1 = derive_sampling_seed("test", None, 42)
        seed2 = derive_sampling_seed("test", "n", 42)
        assert seed1 != seed2

    def test_different_base_seeds(self) -> None:
        """Different base seeds produce different derived seeds."""
        seed1 = derive_sampling_seed("test", None, 42)
        seed2 = derive_sampling_seed("test", None, 123)
        assert seed1 != seed2

    def test_none_base_seed(self) -> None:
        """None base seed produces deterministic output."""
        seed1 = derive_sampling_seed("hello", None, None)
        seed2 = derive_sampling_seed("hello", None, None)
        assert seed1 == seed2

    def test_case_insensitive_word(self) -> None:
        """Word is lowercased for consistency."""
        seed1 = derive_sampling_seed("Hello", None, 42)
        seed2 = derive_sampling_seed("hello", None, 42)
        assert seed1 == seed2

    def test_case_insensitive_pos(self) -> None:
        """POS is lowercased for consistency."""
        seed1 = derive_sampling_seed("run", "V", 42)
        seed2 = derive_sampling_seed("run", "v", 42)
        assert seed1 == seed2


class TestComputeSampleIndices:
    """Tests for compute_sample_indices function."""

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs always produce same indices."""
        indices1 = compute_sample_indices(10, 3, 12345)
        indices2 = compute_sample_indices(10, 3, 12345)
        assert indices1 == indices2

    def test_returns_sorted_tuple(self) -> None:
        """Indices are returned sorted."""
        indices = compute_sample_indices(100, 5, 42)
        assert indices == tuple(sorted(indices))

    def test_all_indices_in_bounds(self) -> None:
        """All indices are within collection bounds."""
        indices = compute_sample_indices(10, 5, 42)
        assert all(0 <= i < 10 for i in indices)

    def test_correct_sample_size(self) -> None:
        """Returns exactly sample_size indices when possible."""
        indices = compute_sample_indices(100, 5, 42)
        assert len(indices) == 5

    def test_sample_larger_than_collection(self) -> None:
        """Returns all indices when sample_size > collection_size."""
        indices = compute_sample_indices(3, 10, 42)
        assert indices == (0, 1, 2)

    def test_sample_equals_collection(self) -> None:
        """Returns all indices when sample_size == collection_size."""
        indices = compute_sample_indices(5, 5, 42)
        assert indices == (0, 1, 2, 3, 4)

    def test_empty_collection(self) -> None:
        """Returns empty tuple for empty collection."""
        indices = compute_sample_indices(0, 5, 42)
        assert indices == ()

    def test_no_duplicates(self) -> None:
        """All indices are unique."""
        indices = compute_sample_indices(100, 20, 42)
        assert len(indices) == len(set(indices))

    def test_different_seeds_different_indices(self) -> None:
        """Different seeds produce different indices."""
        indices1 = compute_sample_indices(100, 5, 42)
        indices2 = compute_sample_indices(100, 5, 123)
        assert indices1 != indices2


class TestSampleValues:
    """Tests for sample_values function."""

    def test_basic_selection(self) -> None:
        """Selects values at given indices."""
        values = ["a", "b", "c", "d", "e"]
        result = sample_values(values, [0, 2, 4])
        assert result == ["a", "c", "e"]

    def test_empty_indices(self) -> None:
        """Empty indices returns empty list."""
        values = ["a", "b", "c"]
        result = sample_values(values, [])
        assert result == []

    def test_skips_out_of_bounds(self) -> None:
        """Out-of-bounds indices are skipped."""
        values = ["a", "b", "c"]
        result = sample_values(values, [0, 1, 5, 10])
        assert result == ["a", "b"]

    def test_skips_negative_indices(self) -> None:
        """Negative indices are skipped."""
        values = ["a", "b", "c"]
        result = sample_values(values, [-1, 0, 1])
        assert result == ["a", "b"]

    def test_preserves_order(self) -> None:
        """Values are returned in index order."""
        values = ["e", "d", "c", "b", "a"]
        result = sample_values(values, [4, 2, 0])
        assert result == ["a", "c", "e"]


class TestDeterministicSample:
    """Tests for deterministic_sample convenience function."""

    def test_basic_sampling(self) -> None:
        """Returns sampled values."""
        values = ["a", "b", "c", "d", "e"]
        result = deterministic_sample(values, limit=3, word="test", pos=None, base_seed=42)
        assert len(result) == 3
        assert all(v in values for v in result)

    def test_deterministic(self) -> None:
        """Same inputs produce same output."""
        values = ["a", "b", "c", "d", "e"]
        result1 = deterministic_sample(values, limit=3, word="test", pos=None, base_seed=42)
        result2 = deterministic_sample(values, limit=3, word="test", pos=None, base_seed=42)
        assert result1 == result2

    def test_limit_zero(self) -> None:
        """Zero limit returns empty list."""
        values = ["a", "b", "c"]
        result = deterministic_sample(values, limit=0, word="test", pos=None, base_seed=42)
        assert result == []

    def test_limit_negative(self) -> None:
        """Negative limit returns empty list."""
        values = ["a", "b", "c"]
        result = deterministic_sample(values, limit=-1, word="test", pos=None, base_seed=42)
        assert result == []

    def test_limit_exceeds_values(self) -> None:
        """Limit exceeding values returns all values."""
        values = ["a", "b", "c"]
        result = deterministic_sample(values, limit=10, word="test", pos=None, base_seed=42)
        assert result == ["a", "b", "c"]

    def test_different_words_different_samples(self) -> None:
        """Different words produce different samples."""
        values = list("abcdefghij")
        result1 = deterministic_sample(values, limit=3, word="hello", pos=None, base_seed=42)
        result2 = deterministic_sample(values, limit=3, word="world", pos=None, base_seed=42)
        assert result1 != result2

    def test_preserves_sorted_order(self) -> None:
        """Samples are returned in original order."""
        values = ["a", "b", "c", "d", "e"]
        result = deterministic_sample(values, limit=3, word="test", pos=None, base_seed=42)
        # Check that result values appear in same relative order as input
        indices = [values.index(v) for v in result]
        assert indices == sorted(indices)
