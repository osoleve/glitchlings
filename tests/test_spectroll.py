import pytest

from collections import Counter

from glitchlings.spectroll import swap_colors


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("red balloon", "blue balloon"),
        ("Green light", "Lime light"),
        ("BLUE sky", "RED sky"),
        ("A yellow submarine.", "A purple submarine."),
        ("brown boots", "maroon boots"),
        ("PINK SUNSET", "PEACH SUNSET"),
        ("The grey sky", "The silver sky"),
    ],
)
def test_basic_swaps(text: str, expected: str) -> None:
    assert swap_colors(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a reddish hue", "a blueish hue"),
        ("lush greenery", "lush limeery"),
        ("navyish trim", "indigoish trim"),
    ],
)
def test_compound_color_forms(text: str, expected: str) -> None:
    assert swap_colors(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Red, green, and blue!", "Blue, lime, and red!"),
        ("Do you prefer Black or White?", "Do you prefer White or Black?"),
    ],
)
def test_respects_case_and_punctuation(text: str, expected: str) -> None:
    assert swap_colors(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "credit score",
        "infrared telescope",
        "troubled",  # substring overlap should not trigger
    ],
)
def test_ignores_embedded_color_names(text: str) -> None:
    assert swap_colors(text) == text


# Drift mode tests (merged from test_spectroll_drift.py)


def test_drift_mode_reproducible_with_seed() -> None:
    text = "red green blue yellow"
    first = swap_colors(text, mode="drift", seed=7)
    second = swap_colors(text, mode="drift", seed=7)
    assert first == second


def test_drift_mode_varies_with_seed() -> None:
    text = "red green blue yellow"
    outputs = {swap_colors(text, mode="drift", seed=seed) for seed in range(5)}
    assert len(outputs) >= 2


@pytest.mark.parametrize(
    "seed,expected_counts",
    [(3, Counter({"magenta": 1, "purple": 1, "lime": 1, "teal": 1}))],
)
def test_drift_mode_expected_palette(seed: int, expected_counts: Counter[str]) -> None:
    text = "red blue yellow green"
    result = swap_colors(text, mode="drift", seed=seed)
    tokens = result.split()
    assert Counter(token.lower() for token in tokens) == expected_counts
