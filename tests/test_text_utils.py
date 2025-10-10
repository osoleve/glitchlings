import pytest

from glitchlings.zoo._text_utils import (
    split_preserving_whitespace,
    split_token_edges,
    token_core_length,
)


def test_split_preserving_whitespace_preserves_internal_separators():
    tokens = split_preserving_whitespace("alpha  beta\tgamma")
    assert tokens == ["alpha", "  ", "beta", "\t", "gamma"]


def test_split_token_edges_returns_prefix_core_suffix():
    prefix, core, suffix = split_token_edges('"alpha!"')
    assert prefix == '"'
    assert core == "alpha"
    assert suffix == '!"'


def test_token_core_length_handles_edge_cases():
    assert token_core_length("alpha") == 5
    assert token_core_length("...") == 3
    assert token_core_length("") == 1


@pytest.mark.parametrize(
    "token, expected",
    [
        ("alpha", ("", "alpha", "")),
        ("...?", ("...?", "", "")),
        ("(beta)", ("(", "beta", ")")),
    ],
)
def test_split_token_edges_examples(token: str, expected: tuple[str, str, str]) -> None:
    assert split_token_edges(token) == expected
