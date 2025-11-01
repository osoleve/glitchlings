from collections import Counter

import pytest

from glitchlings.spectroll import swap_colors


def test_drift_mode_reproducible_with_seed() -> None:
    text = "red green blue yellow"
    first = swap_colors(text, mode="drift", seed=7)
    second = swap_colors(text, mode="drift", seed=7)
    assert first == second


def test_drift_mode_varies_with_seed() -> None:
    text = "red green blue yellow"
    outputs = {swap_colors(text, mode="drift", seed=seed) for seed in range(5)}
    assert len(outputs) >= 2


@pytest.mark.parametrize("seed,expected_counts", [(3, Counter({"orange": 1, "purple": 1, "white": 1, "teal": 1}))])
def test_drift_mode_expected_palette(seed: int, expected_counts: Counter[str]) -> None:
    text = "red blue yellow green"
    result = swap_colors(text, mode="drift", seed=seed)
    tokens = result.split()
    assert Counter(token.lower() for token in tokens) == expected_counts
