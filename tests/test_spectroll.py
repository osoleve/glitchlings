import pytest

from glitchlings.spectroll import swap_colors


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("red balloon", "blue balloon"),
        ("Green light", "Lime light"),
        ("BLUE sky", "RED sky"),
        ("A yellow submarine.", "A purple submarine."),
    ],
)
def test_basic_swaps(text: str, expected: str) -> None:
    assert swap_colors(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a reddish hue", "a blueish hue"),
        ("lush greenery", "lush limeery"),
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
