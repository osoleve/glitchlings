from __future__ import annotations

from pathlib import Path

import pytest

from glitchlings.lexicon import (
    Lexicon,
    get_default_lexicon,
    register_backend,
    unregister_backend,
)
from glitchlings.runtime_config import reload_config, reset_config


class StubLexicon(Lexicon):
    def __init__(self, *, marker: str, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self.marker = marker

    def get_synonyms(self, word: str, pos: str | None = None, n: int = 5) -> list[str]:
        return [f"{word}:{self.marker}"]


@pytest.fixture()
def _reset_configuration(monkeypatch: pytest.MonkeyPatch):
    reset_config()
    yield
    reset_config()
    monkeypatch.delenv("GLITCHLINGS_CONFIG", raising=False)


def test_default_lexicon_respects_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _reset_configuration
) -> None:
    factory_calls: list[int | None] = []

    def factory(seed: int | None) -> Lexicon:
        factory_calls.append(seed)
        return StubLexicon(marker="stub", seed=seed)

    register_backend("stub", factory)
    try:
        config_path = tmp_path / "config.toml"
        config_path.write_text("[lexicon]\npriority = [\"stub\"]\n", encoding="utf8")

        monkeypatch.setenv("GLITCHLINGS_CONFIG", str(config_path))
        reload_config()

        lexicon = get_default_lexicon(seed=2024)
        assert isinstance(lexicon, StubLexicon)
        assert lexicon.marker == "stub"
        assert factory_calls == [2024]
    finally:
        unregister_backend("stub")

