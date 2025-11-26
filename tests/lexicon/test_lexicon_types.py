"""Tests for pure lexicon type definitions."""

from __future__ import annotations

import pytest

from glitchlings.lexicon.types import (
    CacheSnapshot,
    SynonymProvider,
    SynonymQuery,
    SynonymResult,
    empty_cache,
)


class TestSynonymQuery:
    """Tests for SynonymQuery dataclass."""

    def test_default_values(self) -> None:
        query = SynonymQuery(word="hello")
        assert query.word == "hello"
        assert query.pos is None
        assert query.limit == 5

    def test_custom_values(self) -> None:
        query = SynonymQuery(word="run", pos="v", limit=10)
        assert query.word == "run"
        assert query.pos == "v"
        assert query.limit == 10

    def test_frozen(self) -> None:
        query = SynonymQuery(word="test")
        with pytest.raises(AttributeError):
            query.word = "changed"  # type: ignore[misc]


class TestSynonymResult:
    """Tests for SynonymResult dataclass."""

    def test_basic_creation(self) -> None:
        result = SynonymResult(
            word="happy",
            synonyms=("joyful", "glad", "pleased"),
        )
        assert result.word == "happy"
        assert result.synonyms == ("joyful", "glad", "pleased")
        assert result.pos is None
        assert result.seed_material is None

    def test_with_all_fields(self) -> None:
        result = SynonymResult(
            word="run",
            synonyms=("sprint", "jog", "dash"),
            pos="v",
            seed_material="abc123",
        )
        assert result.pos == "v"
        assert result.seed_material == "abc123"

    def test_sample_with_valid_indices(self) -> None:
        result = SynonymResult(
            word="test",
            synonyms=("a", "b", "c", "d", "e"),
        )
        sampled = result.sample([0, 2, 4])
        assert sampled == ("a", "c", "e")

    def test_sample_ignores_out_of_bounds(self) -> None:
        result = SynonymResult(
            word="test",
            synonyms=("a", "b", "c"),
        )
        sampled = result.sample([0, 1, 5, 10])
        assert sampled == ("a", "b")

    def test_sample_empty_indices(self) -> None:
        result = SynonymResult(
            word="test",
            synonyms=("a", "b", "c"),
        )
        sampled = result.sample([])
        assert sampled == ()

    def test_frozen(self) -> None:
        result = SynonymResult(word="test", synonyms=("a",))
        with pytest.raises(AttributeError):
            result.word = "changed"  # type: ignore[misc]


class TestCacheSnapshot:
    """Tests for CacheSnapshot dataclass."""

    def test_empty_cache(self) -> None:
        snapshot = empty_cache()
        assert snapshot.entries == {}
        assert snapshot.checksum is None

    def test_with_entries(self) -> None:
        entries = {"hello": ["hi", "hey"], "bye": ["goodbye"]}
        snapshot = CacheSnapshot(entries=entries, checksum="abc123")
        assert snapshot.entries == entries
        assert snapshot.checksum == "abc123"

    def test_frozen(self) -> None:
        snapshot = CacheSnapshot(entries={}, checksum=None)
        with pytest.raises(AttributeError):
            snapshot.checksum = "changed"  # type: ignore[misc]


class TestSynonymProviderProtocol:
    """Tests for SynonymProvider protocol."""

    def test_protocol_compliance(self) -> None:
        class MockProvider:
            def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
                return [f"{word}_syn"]

        provider = MockProvider()
        assert isinstance(provider, SynonymProvider)

    def test_non_compliant_class(self) -> None:
        class NotAProvider:
            pass

        obj = NotAProvider()
        assert not isinstance(obj, SynonymProvider)
