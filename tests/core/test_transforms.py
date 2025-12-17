"""Tests for zoo/transforms.py pure text transformation functions."""

from __future__ import annotations

from glitchlings.util.keyboards import build_keyboard_neighbor_map
from glitchlings.zoo.transforms import (
    WordToken,
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


class TestTextTokenization:
    """Tests for text tokenization functions."""

    def test_split_preserving_whitespace_basic(self) -> None:
        result = split_preserving_whitespace("hello world")
        assert result == ["hello", " ", "world"]

    def test_split_preserving_whitespace_multiple_spaces(self) -> None:
        result = split_preserving_whitespace("hello  world")
        assert result == ["hello", "  ", "world"]

    def test_split_preserving_whitespace_empty(self) -> None:
        result = split_preserving_whitespace("")
        assert result == [""]

    def test_split_preserving_whitespace_no_spaces(self) -> None:
        result = split_preserving_whitespace("hello")
        assert result == ["hello"]

    def test_split_preserving_whitespace_leading_space(self) -> None:
        result = split_preserving_whitespace(" hello")
        assert result == ["", " ", "hello"]

    def test_split_token_edges_simple(self) -> None:
        prefix, core, suffix = split_token_edges("hello")
        assert (prefix, core, suffix) == ("", "hello", "")

    def test_split_token_edges_with_quotes(self) -> None:
        prefix, core, suffix = split_token_edges('"hello"')
        assert (prefix, core, suffix) == ('"', "hello", '"')

    def test_split_token_edges_with_punctuation(self) -> None:
        prefix, core, suffix = split_token_edges("...test!")
        assert (prefix, core, suffix) == ("...", "test", "!")

    def test_split_token_edges_empty(self) -> None:
        prefix, core, suffix = split_token_edges("")
        assert (prefix, core, suffix) == ("", "", "")

    def test_compute_core_length_word(self) -> None:
        assert compute_core_length("hello") == 5

    def test_compute_core_length_with_punctuation(self) -> None:
        assert compute_core_length('"hello"') == 5

    def test_compute_core_length_empty(self) -> None:
        assert compute_core_length("") == 1  # minimum 1

    def test_compute_core_length_whitespace(self) -> None:
        assert compute_core_length("   ") == 3

    def test_collect_word_tokens_basic(self) -> None:
        tokens = split_preserving_whitespace("hello world")
        word_tokens = collect_word_tokens(tokens)
        assert len(word_tokens) == 2
        assert word_tokens[0].core == "hello"
        assert word_tokens[1].core == "world"

    def test_collect_word_tokens_skip_first(self) -> None:
        tokens = split_preserving_whitespace("hello world test")
        word_tokens = collect_word_tokens(tokens, skip_first_word=True)
        assert len(word_tokens) == 2
        assert word_tokens[0].core == "world"

    def test_word_token_has_core(self) -> None:
        token = WordToken(index=0, prefix="", core="test", suffix="", core_length=4)
        assert token.has_core is True

    def test_word_token_no_core(self) -> None:
        token = WordToken(index=0, prefix="...", core="", suffix="", core_length=3)
        assert token.has_core is False

    def test_reassemble_tokens(self) -> None:
        tokens = ["hello", " ", "world"]
        assert reassemble_tokens(tokens) == "hello world"

    def test_reassemble_empty(self) -> None:
        assert reassemble_tokens([]) == ""

    def test_roundtrip_tokenization(self) -> None:
        """Verify that split + reassemble preserves original text."""
        original = "  Hello,   world!  "
        tokens = split_preserving_whitespace(original)
        reassembled = reassemble_tokens(tokens)
        assert reassembled == original


class TestKeyboardProcessing:
    """Tests for keyboard layout functions."""

    def test_build_keyboard_neighbor_map_simple(self) -> None:
        rows = ["abc", " de"]
        neighbors = build_keyboard_neighbor_map(rows)
        # 'a' should neighbor 'b' and 'd'
        assert "b" in neighbors["a"]
        assert "d" in neighbors["a"]

    def test_build_keyboard_neighbor_map_lowercase(self) -> None:
        rows = ["ABC"]
        neighbors = build_keyboard_neighbor_map(rows)
        assert "a" in neighbors
        assert "b" in neighbors
        assert "c" in neighbors

    def test_build_keyboard_neighbor_map_ignores_spaces(self) -> None:
        rows = ["a b"]  # space between a and b
        neighbors = build_keyboard_neighbor_map(rows)
        # b is not a neighbor of a (space between them)
        assert "b" not in neighbors.get("a", [])


class TestStringDiffs:
    """Tests for string difference computation."""

    def test_compute_string_diffs_no_changes(self) -> None:
        result = compute_string_diffs("hello", "hello")
        assert result == []

    def test_compute_string_diffs_replacement(self) -> None:
        result = compute_string_diffs("cat", "bat")
        assert len(result) == 1
        assert result[0][0][0] == "replace"

    def test_compute_string_diffs_deletion(self) -> None:
        result = compute_string_diffs("hello", "helo")
        assert len(result) == 1
        # Should have a delete operation for 'l'
        tags = [op[0] for op in result[0]]
        assert "delete" in tags

    def test_compute_string_diffs_insertion(self) -> None:
        result = compute_string_diffs("helo", "hello")
        assert len(result) == 1
        tags = [op[0] for op in result[0]]
        assert "insert" in tags


class TestSequenceOperations:
    """Tests for sequence helper functions."""

    def test_stable_deduplicate_preserves_order(self) -> None:
        result = stable_deduplicate([3, 1, 4, 1, 5, 9, 2, 6, 5])
        assert result == [3, 1, 4, 5, 9, 2, 6]

    def test_stable_deduplicate_empty(self) -> None:
        assert stable_deduplicate([]) == []

    def test_stable_deduplicate_no_duplicates(self) -> None:
        result = stable_deduplicate([1, 2, 3])
        assert result == [1, 2, 3]

    def test_stable_deduplicate_strings(self) -> None:
        result = stable_deduplicate(["a", "b", "a", "c"])
        assert result == ["a", "b", "c"]

    def test_interleave_lists_equal_length(self) -> None:
        result = interleave_lists([1, 2], ["a", "b"])
        assert result == [1, "a", 2, "b"]

    def test_interleave_lists_primary_longer(self) -> None:
        result = interleave_lists([1, 2, 3], ["a"])
        assert result == [1, "a", 2, 3]

    def test_interleave_lists_secondary_longer(self) -> None:
        result = interleave_lists([1], ["a", "b", "c"])
        assert result == [1, "a", "b", "c"]

    def test_interleave_lists_secondary_first(self) -> None:
        result = interleave_lists([1, 2], ["a", "b"], secondary_first=True)
        assert result == ["a", 1, "b", 2]

    def test_interleave_lists_empty(self) -> None:
        assert interleave_lists([], []) == []


class TestMappingHelpers:
    """Tests for mapping helper functions."""

    def test_invert_mapping_basic(self) -> None:
        mapping = {"a": ["x", "y"], "b": ["z"]}
        inverted = invert_mapping(mapping)
        assert inverted == {"x": "a", "y": "a", "z": "b"}

    def test_invert_mapping_empty(self) -> None:
        assert invert_mapping({}) == {}

    def test_invert_mapping_collision(self) -> None:
        # Later keys win on collision
        mapping = {"a": ["x"], "b": ["x"]}
        inverted = invert_mapping(mapping)
        assert inverted["x"] == "b"
