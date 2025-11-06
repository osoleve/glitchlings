from __future__ import annotations

import importlib

import pytest

from glitchlings.lexicon import Lexicon
from glitchlings.lexicon.vector import VectorLexicon

jargoyle_module = importlib.import_module("glitchlings.zoo.jargoyle")
substitute_random_synonyms = jargoyle_module.substitute_random_synonyms


class TrackingLexicon(Lexicon):
    def __init__(self, *, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self.reseed_calls: list[int | None] = []

    def reseed(self, seed: int | None) -> None:
        self.reseed_calls.append(seed)
        super().reseed(seed)

    def get_synonyms(
        self, word: str, pos: str | None = None, n: int = 5
    ) -> list[str]:
        candidates = [f"{word}_syn_{idx}" for idx in range(1, 6)]
        return self._deterministic_sample(candidates, limit=n, word=word, pos=pos)


def _clean_tokens(text: str) -> list[str]:
    return [token.strip(".,") for token in text.split()]


@pytest.fixture()
def vector_lexicon() -> VectorLexicon:
    embeddings = {
        "alpha": [1.0, 0.0],
        "beta": [0.9, 0.1],
        "gamma": [0.0, 1.0],
        "delta": [-1.0, 0.0],
    }
    return VectorLexicon(source=embeddings, max_neighbors=2, min_similarity=0.05)


def test_jargoyle_constructor_uses_configured_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = TrackingLexicon(seed=777)
    requested_seeds: list[int | None] = []

    def _fake_default(seed: int | None = None) -> TrackingLexicon:
        requested_seeds.append(seed)
        return configured

    monkeypatch.setattr(jargoyle_module, "get_default_lexicon", _fake_default)

    glitch = jargoyle_module.Jargoyle(seed=123)

    assert requested_seeds == [123]
    assert glitch.lexicon is configured
    assert getattr(glitch, "_owns_lexicon") is True
    assert configured.seed == 123


def test_jargoyle_multiple_pos_targets_change_words():
    text = "They sing happy songs."
    result = substitute_random_synonyms(
        text,
        rate=1.0,
        part_of_speech=("v", "a"),
        seed=123,
    )

    original_tokens = _clean_tokens(text)
    result_tokens = _clean_tokens(result)

    # Expect both verb and adjective replacements to differ from input
    changed = {
        orig for orig, new in zip(original_tokens, result_tokens) if orig != new
    }
    assert {"sing", "happy"} <= changed


def test_jargoyle_any_includes_all_supported_pos():
    text = "They sing happy songs quickly."
    result = substitute_random_synonyms(
        text,
        rate=1.0,
        part_of_speech="any",
        seed=99,
    )

    original_tokens = _clean_tokens(text)
    result_tokens = _clean_tokens(result)

    changed = {
        orig for orig, new in zip(original_tokens, result_tokens) if orig != new
    }
    assert {"sing", "happy", "songs", "quickly"} <= changed


def test_jargoyle_custom_lexicon_deterministic(vector_lexicon: VectorLexicon) -> None:
    text = "alpha beta"

    first = substitute_random_synonyms(
        text,
        rate=1.0,
        seed=2024,
        lexicon=vector_lexicon,
    )
    second = substitute_random_synonyms(
        text,
        rate=1.0,
        seed=2024,
        lexicon=vector_lexicon,
    )

    assert first == second
    assert first != text


def test_dependencies_available_uses_default_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyLexicon(Lexicon):
        def __init__(self) -> None:
            super().__init__()

        def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
            return []

    module = importlib.import_module("glitchlings.zoo.jargoyle")
    monkeypatch.setattr(module, "_lexicon_dependencies_available", lambda: False)
    monkeypatch.setattr(module, "WordNetLexicon", None)
    monkeypatch.setattr(module, "get_default_lexicon", lambda seed=None: DummyLexicon())

    assert jargoyle_module.dependencies_available()


def test_dependencies_available_false_when_no_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("glitchlings.zoo.jargoyle")
    monkeypatch.setattr(module, "_lexicon_dependencies_available", lambda: False)
    monkeypatch.setattr(module, "WordNetLexicon", None)

    def _raise(seed=None):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(module, "get_default_lexicon", _raise)

    assert not jargoyle_module.dependencies_available()


def test_jargoyle_rate_above_one_clamped(vector_lexicon: VectorLexicon) -> None:
    text = "alpha beta gamma"

    result = substitute_random_synonyms(
        text,
        rate=2.0,
        seed=77,
        lexicon=vector_lexicon,
    )

    assert result != text
    original_tokens = _clean_tokens(text)
    result_tokens = _clean_tokens(result)
    assert len(result_tokens) == len(original_tokens)
    assert all(orig != new for orig, new in zip(original_tokens, result_tokens))


def test_small_rate_allows_replacements_for_short_inputs() -> None:
    text = "alpha beta"
    lexicon = TrackingLexicon()

    result = substitute_random_synonyms(
        text,
        rate=0.1,
        seed=123,
        lexicon=lexicon,
    )

    assert result != text


def test_substitute_random_synonyms_restores_external_seed() -> None:
    text = "alpha beta"
    lexicon = TrackingLexicon(seed=777)
    original_seed = lexicon.seed

    result = substitute_random_synonyms(
        text,
        rate=1.0,
        seed=2024,
        lexicon=lexicon,
    )

    assert result != text
    assert lexicon.seed == original_seed
    # Expect two reseed calls: one to override, one to restore.
    assert lexicon.reseed_calls[0] == 2024
    assert lexicon.reseed_calls[-1] == original_seed


def test_jargoyle_preserves_external_lexicon_seed_when_seed_cleared() -> None:
    external_seed = 314
    lexicon = TrackingLexicon(seed=external_seed)

    glitch = jargoyle_module.Jargoyle(lexicon=lexicon, seed=None)
    assert lexicon.seed == external_seed
    assert lexicon.reseed_calls == []

    glitch.set_param("seed", 99)
    assert lexicon.seed == 99

    glitch.set_param("seed", None)
    assert lexicon.seed == external_seed
    assert lexicon.reseed_calls[-2:] == [99, external_seed]


def test_jargoyle_restores_external_lexicon_seed_when_original_none() -> None:
    lexicon = TrackingLexicon(seed=None)

    glitch = jargoyle_module.Jargoyle(lexicon=lexicon, seed=None)
    assert lexicon.seed is None
    assert lexicon.reseed_calls == []

    glitch.set_param("seed", 42)
    assert lexicon.seed == 42

    glitch.set_param("seed", None)
    assert lexicon.seed is None
    assert lexicon.reseed_calls[-2:] == [42, None]
