from __future__ import annotations

import math
from typing import cast

from glitchlings import typogre, zeedub
from glitchlings.zoo.zeedub import _DEFAULT_ZERO_WIDTH_CHARACTERS


def test_mim1c_rate_bounds(fresh_glitchling, sample_text):
    """Test that Mim1c respects rate parameter bounds."""
    m = fresh_glitchling("mim1c")
    m.set_param("seed", 7)
    m.set_param("rate", 0.02)
    out = cast(str, m(sample_text))
    # Should change no more than ~2% of alnum characters
    alnum = [c for c in sample_text if c.isalnum()]
    paired_changes = sum(1 for a, b in zip(sample_text, out) if a != b and a.isalnum())
    if len(out) > len(sample_text):
        tail_alnum = sum(1 for c in out[len(sample_text):] if c.isalnum())
    else:
        tail_alnum = sum(1 for c in sample_text[len(out):] if c.isalnum())
    changed = paired_changes + tail_alnum
    assert changed <= int(len(alnum) * 0.02) + 2  # slack for discrete rounding


def test_mim1c_respects_banned_characters(fresh_glitchling):
    """Test that Mim1c respects banned_characters parameter."""
    m = fresh_glitchling("mim1c")
    m.set_param("seed", 2)
    m.set_param("rate", 1.0)
    m.set_param("banned_characters", ["ａ"])

    banned = {"ａ"}
    out = cast(str, m("ａ"))
    assert not any(char in banned for char in out)


def test_rushmore_rate_decreases_tokens(fresh_glitchling):
    """Test that Rushmore respects rate parameter for token deletion."""
    text = "a b c d e f g h"
    glitch = fresh_glitchling("rushmore")
    glitch.set_param("seed", 5)
    glitch.set_param("rate", 0.5)
    out = cast(str, glitch(text))
    assert len(out.split()) <= len(text.split())


def test_rushmore_max_deletion_cap(fresh_glitchling):
    """Test that Rushmore respects maximum deletion cap."""
    text = "alpha beta gamma delta epsilon zeta eta theta"
    words = text.split()
    candidate_count = max(len(words) - 1, 0)
    rushmore = fresh_glitchling("rushmore")

    for rate, seed in [(0.1, 3), (0.5, 11), (1.0, 17)]:
        glitch = rushmore.clone()
        glitch.set_param("seed", seed)
        glitch.set_param("rate", rate)
        out = cast(str, glitch(text))

        removed = len(words) - len(out.split())
        allowed = min(candidate_count, math.floor(candidate_count * rate))
        assert removed <= allowed


def test_rushmore_preserves_leading_token_and_spacing(fresh_glitchling):
    """Test that Rushmore preserves the leading token and spacing."""
    text = "Alpha, beta; gamma: delta epsilon zeta"
    seeds = (0, 3, 11, 21)
    template = fresh_glitchling("rushmore")
    template.set_param("rate", 1.0)
    words = text.split()
    for seed in seeds:
        glitch = template.clone()
        glitch.set_param("seed", seed)
        out = cast(str, glitch(text))
        leading = out.split()[0]
        original_core = "".join(ch for ch in words[0] if ch.isalnum())
        result_core = "".join(ch for ch in leading if ch.isalnum())
        assert leading
        assert result_core == original_core
        assert "  " not in out
        for marker in (" ,", " ;", " :", " ."):
            assert marker not in out
        assert out == out.strip()


def test_redactyl_replacement_char_and_merge(fresh_glitchling):
    """Test that Redactyl respects replacement_char and merge_adjacent parameters."""
    text = "alpha beta gamma"
    glitch = fresh_glitchling("redactyl")
    glitch.set_param("seed", 2)
    glitch.set_param("rate", 1.0)
    glitch.set_param("replacement_char", "#")
    glitch.set_param("merge_adjacent", True)
    out = cast(str, glitch(text))
    assert set(out) <= {"#", " "}
    assert "# #" not in out  # merged


def test_scannequin_rate_increases_changes(fresh_glitchling, sample_text):
    """Test that Scannequin increases changes with higher rates."""
    scannequin = fresh_glitchling("scannequin")

    # count character diffs vs original
    def diff_count(a: str, b: str) -> int:
        return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))

    low_glitch = scannequin.clone()
    low_glitch.set_param("seed", 7)
    low_glitch.set_param("rate", 0.005)
    low = cast(str, low_glitch(sample_text))

    high_glitch = scannequin.clone()
    high_glitch.set_param("seed", 7)
    high_glitch.set_param("rate", 0.05)
    high = cast(str, high_glitch(sample_text))

    assert diff_count(sample_text, high) >= diff_count(sample_text, low)


def _count_zero_width(text: str) -> int:
    return sum(text.count(ch) for ch in _DEFAULT_ZERO_WIDTH_CHARACTERS)


def test_zeedub_rate_increases_insertions(sample_text):
    low_glitch = zeedub.clone()
    low_glitch.set_param("seed", 11)
    low_glitch.set_param("rate", 0.004)
    low = cast(str, low_glitch(sample_text))

    high_glitch = zeedub.clone()
    high_glitch.set_param("seed", 11)
    high_glitch.set_param("rate", 0.05)
    high = cast(str, high_glitch(sample_text))

    assert _count_zero_width(high) >= _count_zero_width(low)


def test_zeedub_pipeline_descriptor_defaults():
    instance = zeedub.clone()
    instance.set_param("rate", 0.05)
    descriptor = instance.pipeline_operation()
    assert descriptor == {
        "type": "zwj",
        "rate": 0.05,
        "characters": list(_DEFAULT_ZERO_WIDTH_CHARACTERS),
    }


def test_zeedub_pipeline_descriptor_filters_custom_characters():
    instance = zeedub.clone()
    instance.set_param("rate", 0.02)
    instance.set_param("characters", ["", "\u200b", "\u200c"])
    descriptor = instance.pipeline_operation()
    assert descriptor is not None
    assert descriptor["characters"] == ["\u200b", "\u200c"]


def test_typogre_pipeline_descriptor_includes_layout():
    instance = typogre.clone()
    instance.set_param("rate", 0.01)
    instance.set_param("keyboard", "QWERTY")
    descriptor = instance.pipeline_operation()
    assert descriptor is not None
    assert descriptor["type"] == "typo"
    assert descriptor["keyboard"] == "QWERTY"
    layout = descriptor["layout"]
    assert "a" in layout and isinstance(layout["a"], list)
    assert "q" in layout and all(isinstance(entry, str) for entry in layout["q"])
