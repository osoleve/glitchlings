"""Reusable assertion helpers for common test patterns."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from glitchlings.zoo.core import Glitchling


def assert_deterministic(glitchling: "Glitchling", text: str, seed: int) -> tuple[str, str]:
    """Assert that a glitchling produces identical output with the same seed.

    This is the primary test for verifying that a glitchling's corruption
    is deterministic when given the same seed.

    Args:
        glitchling: The glitchling instance to test
        text: Input text to corrupt
        seed: Seed value for deterministic behavior

    Returns:
        Tuple of (first_output, second_output) for additional assertions

    Raises:
        AssertionError: If outputs differ

    Example:
        >>> from glitchlings import typogre
        >>> glitch = typogre.clone()
        >>> glitch.set_param("rate", 0.05)
        >>> assert_deterministic(glitch, "test input", seed=42)
    """
    glitchling.reset_rng(seed)
    first = glitchling(text)
    glitchling.reset_rng(seed)
    second = glitchling(text)

    assert first == second, (
        f"{glitchling.name} not deterministic with seed {seed}\n"
        f"First:  {first!r}\n"
        f"Second: {second!r}"
    )

    return first, second


def assert_rate_bounded(
    original: str,
    corrupted: str,
    rate: float,
    counter_fn: Callable[[str], int],
    tolerance: float = 0.05,
) -> None:
    """Assert that corruption stays within rate bounds.

    This helper verifies that a glitchling respects its rate parameter
    by counting the number of elements (characters, words, etc.) that
    were changed and comparing it to the expected rate.

    Args:
        original: The original text
        corrupted: The corrupted text
        rate: The configured rate (e.g., 0.05 for 5%)
        counter_fn: Function that counts elements in text
            (e.g., lambda text: len(text) for character-level)
        tolerance: Acceptable deviation from rate (default 5%)

    Raises:
        AssertionError: If corruption rate is outside bounds

    Example:
        >>> original = "hello world"
        >>> corrupted = "helo world"
        >>> counter_fn = lambda text: sum(1 for c in text if c.isalnum())
        >>> assert_rate_bounded(original, corrupted, 0.1, counter_fn)
    """
    original_count = counter_fn(original)

    if original_count == 0:
        return  # No elements to corrupt

    # Calculate expected bounds
    expected_changes = original_count * rate
    max_expected = int(expected_changes + (original_count * tolerance))

    # Count actual changes (simplified - tests may need custom logic)
    # This is a basic implementation; specific glitchlings may need
    # their own change-counting logic
    actual_changes = sum(
        1 for orig_char, corr_char in zip(original, corrupted)
        if orig_char != corr_char
    )

    assert actual_changes <= max_expected, (
        f"Too many changes: {actual_changes} > {max_expected}\n"
        f"Rate: {rate}, Original count: {original_count}\n"
        f"Original: {original!r}\n"
        f"Corrupted: {corrupted!r}"
    )


def assert_text_similarity(text1: str, text2: str, max_distance: int) -> None:
    """Assert two texts are within edit distance threshold.

    Uses difflib's SequenceMatcher to compute similarity and ensures
    the texts are sufficiently similar.

    Args:
        text1: First text
        text2: Second text
        max_distance: Maximum acceptable edit distance

    Raises:
        AssertionError: If texts are too dissimilar

    Example:
        >>> assert_text_similarity("hello world", "hello world!", max_distance=1)
    """
    from difflib import SequenceMatcher

    similarity = SequenceMatcher(None, text1, text2).ratio()
    max_len = max(len(text1), len(text2), 1)
    expected_min_similarity = 1.0 - (max_distance / max_len)

    assert similarity >= expected_min_similarity, (
        f"Texts too dissimilar: {similarity:.2%} < {expected_min_similarity:.2%}\n"
        f"Text 1: {text1!r}\n"
        f"Text 2: {text2!r}"
    )


def assert_preserves_length(original: str, corrupted: str) -> None:
    """Assert that corruption preserves text length.

    Some glitchlings (like character substitution ones) should maintain
    the exact length of the input text.

    Args:
        original: The original text
        corrupted: The corrupted text

    Raises:
        AssertionError: If lengths differ
    """
    assert len(original) == len(corrupted), (
        f"Length not preserved: {len(original)} -> {len(corrupted)}\n"
        f"Original: {original!r}\n"
        f"Corrupted: {corrupted!r}"
    )


def assert_preserves_whitespace_positions(original: str, corrupted: str) -> None:
    """Assert that whitespace positions are unchanged.

    Some glitchlings should only modify non-whitespace characters,
    leaving whitespace in the same positions.

    Args:
        original: The original text
        corrupted: The corrupted text

    Raises:
        AssertionError: If whitespace positions differ
    """
    orig_ws = [i for i, c in enumerate(original) if c.isspace()]
    corr_ws = [i for i, c in enumerate(corrupted) if c.isspace()]

    assert orig_ws == corr_ws, (
        f"Whitespace positions changed\n"
        f"Original positions: {orig_ws}\n"
        f"Corrupted positions: {corr_ws}\n"
        f"Original: {original!r}\n"
        f"Corrupted: {corrupted!r}"
    )
