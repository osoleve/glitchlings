import importlib
import math
import random
from typing import cast
from glitchlings import typogre, mim1c, reduple, rushmore, redactyl, scannequin, zeedub

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")
from glitchlings.zoo.zeedub import _DEFAULT_ZERO_WIDTH_CHARACTERS

def _count_blocks(s: str, block_char: str = "\u2588") -> int:
    return s.count(block_char)


def test_mim1c_rate_bounds(sample_text):
    m = mim1c.clone()
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


def test_mim1c_respects_banned_characters():
    m = mim1c.clone()
    m.set_param("seed", 2)
    m.set_param("rate", 1.0)
    m.set_param("banned_characters", ["ａ"])

    banned = {"a"}
    out = cast(str, m("a"))
    assert not any(char in banned for char in out)


def test_reduple_rate_increases_tokens():
    text = "a b c d e f g h"
    reduple.set_param("seed", 5)
    reduple.set_param("rate", 0.5)
    out = cast(str, reduple(text))
    assert len(out.split()) >= len(text.split())


def test_reduple_unweighted_matches_python_reference():
    text = "alpha beta gamma delta epsilon zeta"
    seed = 1
    rate = 0.5
    weighted = reduple_module._python_reduplicate_words(
        text,
        rate=rate,
        rng=random.Random(seed),
    )
    unweighted_expected = reduple_module._python_reduplicate_words(
        text,
        rate=rate,
        rng=random.Random(seed),
        unweighted=True,
    )
    assert unweighted_expected != weighted
    instance = reduple.clone()
    instance.set_param("seed", seed)
    instance.set_param("rate", rate)
    instance.set_param("unweighted", True)
    result = cast(str, instance(text))
    assert result == unweighted_expected



def test_rushmore_rate_decreases_tokens():
    text = "a b c d e f g h"
    rushmore.set_param("seed", 5)
    rushmore.set_param("rate", 0.5)
    out = cast(str, rushmore(text))
    assert len(out.split()) <= len(text.split())


def test_rushmore_unweighted_matches_python_reference():
    text = "alpha beta gamma delta epsilon"
    seed = 11
    rate = 0.5
    weighted = rushmore_module._python_delete_random_words(
        text,
        rate=rate,
        rng=random.Random(seed),
    )
    unweighted_expected = rushmore_module._python_delete_random_words(
        text,
        rate=rate,
        rng=random.Random(seed),
        unweighted=True,
    )
    assert unweighted_expected != weighted
    instance = rushmore.clone()
    instance.set_param("seed", seed)
    instance.set_param("rate", rate)
    instance.set_param("unweighted", True)
    result = cast(str, instance(text))
    assert result == unweighted_expected



def test_rushmore_max_deletion_cap():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    words = text.split()
    candidate_count = max(len(words) - 1, 0)

    for rate, seed in [(0.1, 3), (0.5, 11), (1.0, 17)]:
        rushmore.set_param("seed", seed)
        rushmore.set_param("rate", rate)
        out = cast(str, rushmore(text))

        removed = len(words) - len(out.split())
        allowed = min(candidate_count, math.floor(candidate_count * rate))
        assert removed <= allowed


def test_rushmore_preserves_leading_token_and_spacing():
    text = "Alpha, beta; gamma: delta epsilon zeta"
    seeds = (0, 3, 11, 21)
    rushmore.set_param("rate", 1.0)
    words = text.split()
    for seed in seeds:
        rushmore.set_param("seed", seed)
        out = cast(str, rushmore(text))
        leading = out.split()[0]
        original_core = "".join(ch for ch in words[0] if ch.isalnum())
        result_core = "".join(ch for ch in leading if ch.isalnum())
        assert leading
        assert result_core == original_core
        assert "  " not in out
        for marker in (" ,", " ;", " :", " ."):
            assert marker not in out
        assert out == out.strip()


def test_redactyl_replacement_char_and_merge():
    text = "alpha beta gamma"
    redactyl.set_param("seed", 2)
    redactyl.set_param("rate", 1.0)
    redactyl.set_param("replacement_char", "#")
    redactyl.set_param("merge_adjacent", True)
    out = cast(str, redactyl(text))
    assert set(out) <= {"#", " "}
    assert "# #" not in out  # merged


def test_redactyl_unweighted_matches_python_reference():
    text = "alpha beta gamma delta epsilon"
    seed = 5
    rate = 0.5
    replacement_char = "#"
    weighted = redactyl_module._python_redact_words(
        text,
        replacement_char=replacement_char,
        rate=rate,
        merge_adjacent=False,
        rng=random.Random(seed),
    )
    unweighted_expected = redactyl_module._python_redact_words(
        text,
        replacement_char=replacement_char,
        rate=rate,
        merge_adjacent=False,
        rng=random.Random(seed),
        unweighted=True,
    )
    assert unweighted_expected != weighted
    instance = redactyl.clone()
    instance.set_param("seed", seed)
    instance.set_param("rate", rate)
    instance.set_param("replacement_char", replacement_char)
    instance.set_param("merge_adjacent", False)
    instance.set_param("unweighted", True)
    result = cast(str, instance(text))
    assert result == unweighted_expected



def test_scannequin_error_rate_increases_changes(sample_text):
    # count character diffs vs original
    def diff_count(a: str, b: str) -> int:
        return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))

    scannequin.set_param("seed", 7)
    scannequin.set_param("rate", 0.005)
    low = cast(str, scannequin(sample_text))

    scannequin.set_param("seed", 7)
    scannequin.set_param("rate", 0.05)
    high = cast(str, scannequin(sample_text))

    assert diff_count(sample_text, high) >= diff_count(sample_text, low)




def _count_zero_width(text: str) -> int:
    return sum(text.count(ch) for ch in _DEFAULT_ZERO_WIDTH_CHARACTERS)



def test_zeedub_rate_increases_insertions(sample_text):
    zeedub.set_param("seed", 11)
    zeedub.set_param("rate", 0.004)
    low = cast(str, zeedub(sample_text))

    zeedub.set_param("seed", 11)
    zeedub.set_param("rate", 0.05)
    high = cast(str, zeedub(sample_text))

    assert _count_zero_width(high) >= _count_zero_width(low)
