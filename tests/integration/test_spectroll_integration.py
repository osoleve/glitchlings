from __future__ import annotations

from glitchlings import summon
from glitchlings.main import list_glitchlings
from glitchlings.spectroll import Spectroll
from glitchlings.zoo import BUILTIN_GLITCHLINGS, DEFAULT_GLITCHLING_NAMES


def test_spectroll_registered_in_registry() -> None:
    assert "spectroll" in BUILTIN_GLITCHLINGS
    entry = BUILTIN_GLITCHLINGS["spectroll"]
    assert isinstance(entry, Spectroll)
    assert "spectroll" in DEFAULT_GLITCHLING_NAMES


def test_gaggle_dispatches_spectroll() -> None:
    gaggle = summon(["Spectroll"], seed=808)
    result = gaggle("red green blue")
    assert result == "blue lime red"


def test_cli_lists_spectroll(capsys) -> None:
    list_glitchlings()
    captured = capsys.readouterr()
    assert "Spectroll" in captured.out
