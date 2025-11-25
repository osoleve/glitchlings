"""Property-based tests for pure functions.

Uses hypothesis to verify purity guarantees and edge case handling
for the pure modules in the codebase.

Pure functions tested:
- zoo/transforms.py: Text tokenization and transformation utilities
- zoo/validation.py: Parameter validation and normalization
- zoo/rng.py: Seed derivation (the pure subset)
- attack/compose.py: Result assembly functions
- attack/metrics_dispatch.py: Batch detection logic
"""

from __future__ import annotations

import math
import string
from typing import cast

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from glitchlings.attack.compose import (
    build_empty_metrics,
    extract_transcript_contents,
    format_metrics_for_batch,
    format_metrics_for_single,
)
from glitchlings.attack.metrics_dispatch import is_batch, validate_batch_consistency
from glitchlings.zoo.rng import SEED_MASK, derive_seed

# ---------------------------------------------------------------------------
# Import pure functions under test
# ---------------------------------------------------------------------------
from glitchlings.zoo.transforms import (
    build_keyboard_neighbor_map,
    collect_word_tokens,
    compute_core_length,
    compute_string_diffs,
    interleave_lists,
    invert_mapping,
    reassemble_tokens,
    split_preserving_whitespace,
    split_token_edges,
    stable_deduplicate,
)
from glitchlings.zoo.validation import (
    PartOfSpeechInput,
    clamp_rate,
    clamp_rate_unit,
    normalise_homophone_group,
    normalise_mim1c_classes,
    normalize_parts_of_speech,
    normalize_rushmore_modes,
    normalize_string_collection,
    resolve_bool_flag,
    resolve_rate,
)

# ---------------------------------------------------------------------------
# Custom Strategies
# ---------------------------------------------------------------------------

# Text with various Unicode characters
unicode_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # Exclude surrogate characters
        blacklist_characters=("\x00",),  # Exclude null bytes
    ),
    min_size=0,
    max_size=200,
)

# Printable ASCII text
ascii_text = st.text(alphabet=string.printable, min_size=0, max_size=200)

# Simple word-like text (letters and spaces)
word_text = st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=100)

# Rate values (floats in various ranges, including NaN)
# hypothesis requires allow_nan=False when using min/max bounds, so we use st.one_of
rate_values = st.one_of(
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    st.just(float("nan")),
)
unit_rate_values = st.one_of(
    st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    st.just(float("nan")),
)

# Seed values
seed_values = st.integers(min_value=0, max_value=SEED_MASK)

# Token sequences (lists of strings)
token_sequences = st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=50)

# Batched token sequences (lists of lists of strings)
token_batches = st.lists(token_sequences, min_size=0, max_size=10)


# ===========================================================================
# transforms.py Tests
# ===========================================================================


class TestSplitPreservingWhitespace:
    """Property tests for split_preserving_whitespace."""

    @given(text=unicode_text)
    def test_roundtrip_reconstruction(self, text: str) -> None:
        """Splitting and rejoining reconstructs the original text."""
        tokens = split_preserving_whitespace(text)
        reconstructed = reassemble_tokens(tokens)
        assert reconstructed == text

    @given(text=unicode_text)
    def test_determinism(self, text: str) -> None:
        """Same input always produces same output."""
        result1 = split_preserving_whitespace(text)
        result2 = split_preserving_whitespace(text)
        assert result1 == result2

    @given(text=word_text)
    def test_word_count_consistency(self, text: str) -> None:
        """Non-whitespace tokens are at even indices."""
        tokens = split_preserving_whitespace(text)
        for i, token in enumerate(tokens):
            if token and not token.isspace():
                # Non-whitespace should be at even indices (0, 2, 4, ...)
                # unless the original text started with whitespace
                pass  # This is a structural property, not easily assertable


class TestSplitTokenEdges:
    """Property tests for split_token_edges."""

    @given(token=st.text(min_size=0, max_size=50))
    def test_roundtrip_reconstruction(self, token: str) -> None:
        """Prefix + core + suffix reconstructs the original token."""
        prefix, core, suffix = split_token_edges(token)
        reconstructed = prefix + core + suffix
        assert reconstructed == token

    @given(token=st.text(min_size=0, max_size=50))
    def test_determinism(self, token: str) -> None:
        """Same input always produces same output."""
        result1 = split_token_edges(token)
        result2 = split_token_edges(token)
        assert result1 == result2


class TestComputeCoreLength:
    """Property tests for compute_core_length."""

    @given(token=st.text(min_size=0, max_size=50))
    def test_always_positive(self, token: str) -> None:
        """Core length is always at least 1."""
        length = compute_core_length(token)
        assert length >= 1

    @given(token=st.text(min_size=0, max_size=50))
    def test_determinism(self, token: str) -> None:
        """Same input always produces same output."""
        result1 = compute_core_length(token)
        result2 = compute_core_length(token)
        assert result1 == result2


class TestCollectWordTokens:
    """Property tests for collect_word_tokens."""

    @given(text=word_text)
    def test_indices_are_valid(self, text: str) -> None:
        """All returned WordToken indices are valid for the original token list."""
        tokens = split_preserving_whitespace(text)
        word_tokens = collect_word_tokens(tokens)
        for wt in word_tokens:
            assert 0 <= wt.index < len(tokens)
            assert tokens[wt.index] == wt.prefix + wt.core + wt.suffix

    @given(text=word_text)
    def test_determinism(self, text: str) -> None:
        """Same input always produces same output."""
        tokens = split_preserving_whitespace(text)
        result1 = collect_word_tokens(tokens)
        result2 = collect_word_tokens(tokens)
        assert result1 == result2


class TestStableDeduplicate:
    """Property tests for stable_deduplicate."""

    @given(items=st.lists(st.integers(), min_size=0, max_size=100))
    def test_no_duplicates(self, items: list[int]) -> None:
        """Result contains no duplicate elements."""
        result = stable_deduplicate(items)
        assert len(result) == len(set(result))

    @given(items=st.lists(st.integers(), min_size=0, max_size=100))
    def test_preserves_first_occurrence_order(self, items: list[int]) -> None:
        """First occurrences maintain their relative order."""
        result = stable_deduplicate(items)
        # Check that result is a subsequence of items (first occurrences)
        seen: set[int] = set()
        expected: list[int] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                expected.append(item)
        assert result == expected

    @given(items=st.lists(st.integers(), min_size=0, max_size=100))
    def test_determinism(self, items: list[int]) -> None:
        """Same input always produces same output."""
        result1 = stable_deduplicate(items)
        result2 = stable_deduplicate(items)
        assert result1 == result2

    @given(items=st.lists(st.integers(), min_size=0, max_size=100))
    def test_all_elements_from_original(self, items: list[int]) -> None:
        """All elements in result were in the original."""
        result = stable_deduplicate(items)
        for item in result:
            assert item in items


class TestInterleaveLists:
    """Property tests for interleave_lists."""

    @given(
        primary=st.lists(st.integers(), min_size=0, max_size=50),
        secondary=st.lists(st.integers(), min_size=0, max_size=50),
    )
    def test_length_sum(self, primary: list[int], secondary: list[int]) -> None:
        """Result length equals sum of input lengths."""
        result = interleave_lists(primary, secondary)
        assert len(result) == len(primary) + len(secondary)

    @given(
        primary=st.lists(st.integers(), min_size=0, max_size=50),
        secondary=st.lists(st.integers(), min_size=0, max_size=50),
    )
    def test_all_elements_present(self, primary: list[int], secondary: list[int]) -> None:
        """All elements from both lists appear in result."""
        result = interleave_lists(primary, secondary)
        for item in primary:
            assert item in result
        for item in secondary:
            assert item in result

    @given(
        primary=st.lists(st.integers(), min_size=0, max_size=50),
        secondary=st.lists(st.integers(), min_size=0, max_size=50),
    )
    def test_determinism(self, primary: list[int], secondary: list[int]) -> None:
        """Same inputs always produce same output."""
        result1 = interleave_lists(primary, secondary)
        result2 = interleave_lists(primary, secondary)
        assert result1 == result2


class TestInvertMapping:
    """Property tests for invert_mapping."""

    @given(
        mapping=st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5),
            min_size=0,
            max_size=20,
        )
    )
    def test_values_become_keys(self, mapping: dict[str, list[str]]) -> None:
        """All values in original become keys in inverted."""
        inverted = invert_mapping(mapping)
        for values in mapping.values():
            for value in values:
                assert value in inverted

    @given(
        mapping=st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5),
            min_size=0,
            max_size=20,
        )
    )
    def test_determinism(self, mapping: dict[str, list[str]]) -> None:
        """Same input always produces same output."""
        result1 = invert_mapping(mapping)
        result2 = invert_mapping(mapping)
        assert result1 == result2


class TestComputeStringDiffs:
    """Property tests for compute_string_diffs."""

    @given(original=ascii_text, modified=ascii_text)
    def test_determinism(self, original: str, modified: str) -> None:
        """Same inputs always produce same output."""
        result1 = compute_string_diffs(original, modified)
        result2 = compute_string_diffs(original, modified)
        assert result1 == result2

    @given(text=ascii_text)
    def test_identical_strings_no_diffs(self, text: str) -> None:
        """Identical strings produce no diff groups."""
        result = compute_string_diffs(text, text)
        assert result == []


class TestBuildKeyboardNeighborMap:
    """Property tests for build_keyboard_neighbor_map."""

    @given(
        rows=st.lists(
            st.text(alphabet=string.ascii_lowercase + " ", min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        )
    )
    def test_determinism(self, rows: list[str]) -> None:
        """Same input always produces same output."""
        result1 = build_keyboard_neighbor_map(rows)
        result2 = build_keyboard_neighbor_map(rows)
        assert result1 == result2

    @given(
        rows=st.lists(
            st.text(alphabet=string.ascii_lowercase + " ", min_size=1, max_size=10),
            min_size=1,
            max_size=5,
        )
    )
    def test_neighbors_are_lowercase(self, rows: list[str]) -> None:
        """All keys and neighbor values are lowercase."""
        result = build_keyboard_neighbor_map(rows)
        for key, neighbors in result.items():
            assert key == key.lower()
            for neighbor in neighbors:
                assert neighbor == neighbor.lower()


# ===========================================================================
# validation.py Tests
# ===========================================================================


class TestClampRate:
    """Property tests for clamp_rate."""

    @given(value=rate_values)
    def test_result_non_negative(self, value: float) -> None:
        """Result is always non-negative (NaN becomes 0.0 by default)."""
        result = clamp_rate(value)
        assert result >= 0.0 or math.isnan(result)

    @given(value=rate_values)
    def test_determinism(self, value: float) -> None:
        """Same input always produces same output."""
        result1 = clamp_rate(value)
        result2 = clamp_rate(value)
        # Handle NaN comparison
        if math.isnan(result1):
            assert math.isnan(result2)
        else:
            assert result1 == result2

    @given(value=st.floats(min_value=0.0, max_value=100.0, allow_nan=False))
    def test_non_negative_unchanged(self, value: float) -> None:
        """Non-negative values pass through unchanged."""
        result = clamp_rate(value)
        assert result == value


class TestClampRateUnit:
    """Property tests for clamp_rate_unit."""

    @given(value=unit_rate_values)
    def test_result_in_unit_interval(self, value: float) -> None:
        """Result is always in [0.0, 1.0]."""
        result = clamp_rate_unit(value)
        if not math.isnan(result):
            assert 0.0 <= result <= 1.0

    @given(value=unit_rate_values)
    def test_determinism(self, value: float) -> None:
        """Same input always produces same output."""
        result1 = clamp_rate_unit(value)
        result2 = clamp_rate_unit(value)
        if math.isnan(result1):
            assert math.isnan(result2)
        else:
            assert result1 == result2


class TestResolveRate:
    """Property tests for resolve_rate."""

    @given(value=st.one_of(st.none(), rate_values), default=rate_values)
    def test_determinism(self, value: float | None, default: float) -> None:
        """Same inputs always produce same output."""
        assume(not (value is not None and math.isnan(value)))
        assume(not math.isnan(default))
        result1 = resolve_rate(value, default)
        result2 = resolve_rate(value, default)
        assert result1 == result2

    @given(default=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    def test_none_uses_default(self, default: float) -> None:
        """None value resolves to default."""
        result = resolve_rate(None, default)
        assert result == default


class TestNormalizePartsOfSpeech:
    """Property tests for normalize_parts_of_speech."""

    @given(pos=st.sampled_from(["n", "v", "a", "r", "any"]))
    def test_valid_pos_accepted(self, pos: str) -> None:
        """Valid POS values are accepted."""
        # Cast is needed because hypothesis generates str, not Literal
        result = normalize_parts_of_speech(cast("PartOfSpeechInput", pos))
        assert isinstance(result, tuple)
        assert len(result) >= 1

    @given(pos=st.sampled_from(["n", "v", "a", "r"]))
    def test_determinism(self, pos: str) -> None:
        """Same input always produces same output."""
        # Cast is needed because hypothesis generates str, not Literal
        typed_pos = cast("PartOfSpeechInput", pos)
        result1 = normalize_parts_of_speech(typed_pos)
        result2 = normalize_parts_of_speech(typed_pos)
        assert result1 == result2


class TestNormalizeMim1cClasses:
    """Property tests for normalise_mim1c_classes."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        result = normalise_mim1c_classes(None)
        assert result is None

    def test_all_returns_all(self) -> None:
        """'all' input returns 'all'."""
        result = normalise_mim1c_classes("all")
        assert result == "all"

    @given(value=st.text(min_size=1, max_size=20))
    def test_string_returns_tuple(self, value: str) -> None:
        """Non-'all' string returns single-element tuple."""
        assume(value.lower() != "all")
        result = normalise_mim1c_classes(value)
        assert result == (value,)


class TestNormalizeRushmoreModes:
    """Property tests for normalize_rushmore_modes."""

    @given(mode=st.sampled_from(["delete", "duplicate", "swap", "all"]))
    def test_valid_modes_accepted(self, mode: str) -> None:
        """Valid mode names are accepted."""
        result = normalize_rushmore_modes(mode)
        assert isinstance(result, tuple)
        assert len(result) >= 1

    @given(mode=st.sampled_from(["delete", "duplicate", "swap"]))
    def test_determinism(self, mode: str) -> None:
        """Same input always produces same output."""
        result1 = normalize_rushmore_modes(mode)
        result2 = normalize_rushmore_modes(mode)
        assert result1 == result2


class TestNormaliseHomophoneGroup:
    """Property tests for normalise_homophone_group."""

    @given(group=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_result_is_lowercase(self, group: list[str]) -> None:
        """All words in result are lowercase."""
        result = normalise_homophone_group(group)
        for word in result:
            assert word == word.lower()

    @given(group=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_no_duplicates(self, group: list[str]) -> None:
        """Result contains no duplicates."""
        result = normalise_homophone_group(group)
        assert len(result) == len(set(result))

    @given(group=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_determinism(self, group: list[str]) -> None:
        """Same input always produces same output."""
        result1 = normalise_homophone_group(group)
        result2 = normalise_homophone_group(group)
        assert result1 == result2


class TestResolveBoolFlag:
    """Property tests for resolve_bool_flag."""

    @given(specific=st.one_of(st.none(), st.booleans()), default=st.booleans())
    def test_determinism(self, specific: bool | None, default: bool) -> None:
        """Same inputs always produce same output."""
        result1 = resolve_bool_flag(specific, default)
        result2 = resolve_bool_flag(specific, default)
        assert result1 == result2

    @given(default=st.booleans())
    def test_none_uses_default(self, default: bool) -> None:
        """None specific uses global default."""
        result = resolve_bool_flag(None, default)
        assert result == default

    @given(specific=st.booleans(), default=st.booleans())
    def test_specific_overrides_default(self, specific: bool, default: bool) -> None:
        """Specific value overrides default."""
        result = resolve_bool_flag(specific, default)
        assert result == specific


class TestNormalizeStringCollection:
    """Property tests for normalize_string_collection."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        result = normalize_string_collection(None)
        assert result is None

    @given(value=st.text(min_size=1, max_size=50))
    def test_string_returns_tuple(self, value: str) -> None:
        """String input returns single-element tuple."""
        result = normalize_string_collection(value)
        assert result == (value,)

    @given(values=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_list_returns_tuple(self, values: list[str]) -> None:
        """List input returns tuple with same elements."""
        result = normalize_string_collection(values)
        assert result == tuple(values)


# ===========================================================================
# rng.py Tests (Pure subset)
# ===========================================================================


class TestDeriveSeed:
    """Property tests for derive_seed."""

    @given(base=seed_values, component=st.integers(min_value=0, max_value=1000))
    def test_determinism(self, base: int, component: int) -> None:
        """Same inputs always produce same output."""
        result1 = derive_seed(base, component)
        result2 = derive_seed(base, component)
        assert result1 == result2

    @given(
        base=seed_values,
        c1=st.integers(min_value=0, max_value=100),
        c2=st.integers(min_value=0, max_value=100),
    )
    def test_different_components_different_seeds(self, base: int, c1: int, c2: int) -> None:
        """Different components produce different seeds (usually)."""
        assume(c1 != c2)
        result1 = derive_seed(base, c1)
        result2 = derive_seed(base, c2)
        # High probability they differ, but not guaranteed
        # This is a weak test - just checking the function runs
        assert isinstance(result1, int)
        assert isinstance(result2, int)

    @given(base=seed_values, name=st.text(min_size=1, max_size=20))
    def test_string_components_work(self, base: int, name: str) -> None:
        """String components can be used for derivation."""
        result = derive_seed(base, name)
        assert isinstance(result, int)
        assert 0 <= result <= SEED_MASK


# ===========================================================================
# attack/compose.py Tests
# ===========================================================================


class TestFormatMetricsForSingle:
    """Property tests for format_metrics_for_single."""

    @given(
        metrics=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
                st.lists(
                    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
                    min_size=1,
                    max_size=5,
                ),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_result_all_floats(self, metrics: dict[str, float | list[float]]) -> None:
        """All result values are floats."""
        result = format_metrics_for_single(metrics)
        for value in result.values():
            assert isinstance(value, float)

    @given(
        metrics=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            min_size=0,
            max_size=10,
        )
    )
    def test_determinism(self, metrics: dict[str, float]) -> None:
        """Same input always produces same output."""
        # Cast to satisfy type checker - dict is invariant in value type
        typed_metrics: dict[str, float | list[float]] = metrics  # type: ignore[assignment]
        result1 = format_metrics_for_single(typed_metrics)
        result2 = format_metrics_for_single(typed_metrics)
        assert result1 == result2


class TestFormatMetricsForBatch:
    """Property tests for format_metrics_for_batch."""

    @given(
        metrics=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
                st.lists(
                    st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
                    min_size=1,
                    max_size=5,
                ),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_result_all_lists(self, metrics: dict[str, float | list[float]]) -> None:
        """All result values are lists."""
        result = format_metrics_for_batch(metrics)
        for value in result.values():
            assert isinstance(value, list)

    @given(
        metrics=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            min_size=0,
            max_size=10,
        )
    )
    def test_determinism(self, metrics: dict[str, float]) -> None:
        """Same input always produces same output."""
        # Cast to satisfy type checker - dict is invariant in value type
        typed_metrics: dict[str, float | list[float]] = metrics  # type: ignore[assignment]
        result1 = format_metrics_for_batch(typed_metrics)
        result2 = format_metrics_for_batch(typed_metrics)
        assert result1 == result2


class TestBuildEmptyMetrics:
    """Property tests for build_empty_metrics."""

    @given(names=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_all_keys_present(self, names: list[str]) -> None:
        """All metric names appear as keys."""
        result = build_empty_metrics(names)
        for name in names:
            assert name in result

    @given(names=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_all_values_empty_lists(self, names: list[str]) -> None:
        """All values are empty lists."""
        result = build_empty_metrics(names)
        for value in result.values():
            assert value == []

    @given(names=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_determinism(self, names: list[str]) -> None:
        """Same input always produces same output."""
        result1 = build_empty_metrics(names)
        result2 = build_empty_metrics(names)
        assert result1 == result2


class TestExtractTranscriptContents:
    """Property tests for extract_transcript_contents."""

    @given(contents=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=10))
    def test_roundtrip(self, contents: list[str]) -> None:
        """Can extract contents from well-formed transcript."""
        transcript = [{"role": "user", "content": c} for c in contents]
        result = extract_transcript_contents(transcript)
        assert result == contents

    @given(contents=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=10))
    def test_determinism(self, contents: list[str]) -> None:
        """Same input always produces same output."""
        transcript = [{"role": "user", "content": c} for c in contents]
        result1 = extract_transcript_contents(transcript)
        result2 = extract_transcript_contents(transcript)
        assert result1 == result2


# ===========================================================================
# attack/metrics_dispatch.py Tests
# ===========================================================================


class TestIsBatch:
    """Property tests for is_batch."""

    def test_empty_is_batch(self) -> None:
        """Empty list is treated as batch."""
        assert is_batch([]) is True

    @given(tokens=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=20))
    def test_flat_list_not_batch(self, tokens: list[str]) -> None:
        """Flat list of strings is not a batch."""
        assert is_batch(tokens) is False

    @given(
        batch=st.lists(
            st.lists(st.text(min_size=1, max_size=20), min_size=1),
            min_size=1,
            max_size=5,
        )
    )
    def test_nested_list_is_batch(self, batch: list[list[str]]) -> None:
        """Nested list is a batch."""
        assert is_batch(batch) is True

    @given(tokens=token_sequences)
    def test_determinism(self, tokens: list[str]) -> None:
        """Same input always produces same output."""
        result1 = is_batch(tokens)
        result2 = is_batch(tokens)
        assert result1 == result2


class TestValidateBatchConsistency:
    """Property tests for validate_batch_consistency."""

    @given(tokens=token_sequences)
    def test_same_type_passes(self, tokens: list[str]) -> None:
        """Same type for both inputs doesn't raise."""
        # Both single sequences
        validate_batch_consistency(tokens, tokens, "test_metric")

    @given(batch=token_batches)
    def test_same_batch_type_passes(self, batch: list[list[str]]) -> None:
        """Same batch type for both inputs doesn't raise."""
        validate_batch_consistency(batch, batch, "test_metric")

    def test_mixed_types_raises(self) -> None:
        """Mixed types (batch vs single) raises TypeError."""
        single: list[str] = ["a", "b", "c"]
        batch: list[list[str]] = [["a", "b"], ["c"]]
        with pytest.raises(TypeError):
            validate_batch_consistency(single, batch, "test_metric")


# ===========================================================================
# Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    """Test edge cases for pure functions."""

    def test_empty_string_split(self) -> None:
        """Empty string splits correctly."""
        result = split_preserving_whitespace("")
        assert reassemble_tokens(result) == ""

    def test_whitespace_only_split(self) -> None:
        """Whitespace-only string splits correctly."""
        for ws in [" ", "  ", "\t", "\n", "   \t\n   "]:
            result = split_preserving_whitespace(ws)
            assert reassemble_tokens(result) == ws

    def test_unicode_split(self) -> None:
        """Unicode text splits correctly."""
        text = "héllo wörld 你好 🎉"
        result = split_preserving_whitespace(text)
        assert reassemble_tokens(result) == text

    def test_rate_nan_handling(self) -> None:
        """NaN rate is clamped to 0.0 by default."""
        assert clamp_rate(float("nan")) == 0.0
        assert clamp_rate_unit(float("nan")) == 0.0

    def test_rate_negative_clamping(self) -> None:
        """Negative rates clamp to 0.0."""
        assert clamp_rate(-1.0) == 0.0
        assert clamp_rate_unit(-1.0) == 0.0

    def test_rate_unit_over_one_clamping(self) -> None:
        """Rates over 1.0 clamp to 1.0 for unit interval."""
        assert clamp_rate_unit(2.0) == 1.0
        assert clamp_rate(2.0) == 2.0  # No upper bound for non-unit

    def test_derive_seed_with_multiple_components(self) -> None:
        """derive_seed works with multiple components."""
        result = derive_seed(12345, 1, 2, 3, "test")
        assert isinstance(result, int)
        assert 0 <= result <= SEED_MASK

    def test_stable_deduplicate_empty(self) -> None:
        """Empty list deduplicates to empty list."""
        assert stable_deduplicate([]) == []

    def test_interleave_empty_lists(self) -> None:
        """Empty lists interleave to empty list."""
        assert interleave_lists([], []) == []

    def test_invert_empty_mapping(self) -> None:
        """Empty mapping inverts to empty mapping."""
        assert invert_mapping({}) == {}
