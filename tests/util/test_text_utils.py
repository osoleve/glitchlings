import pytest

from glitchlings.zoo._text_utils import (
    collect_word_tokens,
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


def test_collect_word_tokens_computes_core_length_with_fallbacks():
    tokens = split_preserving_whitespace("alpha ... (beta)")
    word_tokens = collect_word_tokens(tokens)

    assert [token.core_length for token in word_tokens] == [5, 3, 4]


def test_collect_word_tokens_respects_skip_first_word():
    tokens = split_preserving_whitespace("alpha beta gamma")
    word_tokens = collect_word_tokens(tokens, skip_first_word=True)

    assert [token.core for token in word_tokens] == ["beta", "gamma"]
    assert [token.core_length for token in word_tokens] == [4, 5]


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
