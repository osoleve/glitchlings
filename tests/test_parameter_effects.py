from typing import cast
from glitchlings import typogre, mim1c, reduple, rushmore, redactyl, scannequin


def _count_blocks(s: str, block_char: str = "\u2588") -> int:
    return s.count(block_char)


def test_mim1c_replacement_rate_bounds(sample_text):
    m = mim1c.clone()
    m.set_param("seed", 7)
    m.set_param("replacement_rate", 0.02)
    out = cast(str, m(sample_text))
    # Should change no more than ~2% of alnum characters
    alnum = [c for c in sample_text if c.isalnum()]
    changed = sum(1 for a, b in zip(sample_text, out) if a != b and a.isalnum())
    assert changed <= int(len(alnum) * 0.02) + 2  # slack for discrete rounding


def test_reduple_rate_increases_tokens():
    text = "a b c d e f g h"
    reduple.set_param("seed", 5)
    reduple.set_param("reduplication_rate", 0.5)
    out = cast(str, reduple(text))
    assert len(out.split()) >= len(text.split())


def test_rushmore_rate_decreases_tokens():
    text = "a b c d e f g h"
    rushmore.set_param("seed", 5)
    rushmore.set_param("max_deletion_rate", 0.5)
    out = cast(str, rushmore(text))
    assert len(out.split()) <= len(text.split())


def test_redactyl_replacement_char_and_merge():
    text = "alpha beta gamma"
    redactyl.set_param("seed", 2)
    redactyl.set_param("redaction_rate", 1.0)
    redactyl.set_param("replacement_char", "#")
    redactyl.set_param("merge_adjacent", True)
    out = cast(str, redactyl(text))
    assert set(out) <= {"#", " "}
    assert "# #" not in out  # merged


def test_scannequin_error_rate_increases_changes(sample_text):
    # count character diffs vs original
    def diff_count(a: str, b: str) -> int:
        return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))

    scannequin.set_param("seed", 7)
    scannequin.set_param("error_rate", 0.005)
    low = cast(str, scannequin(sample_text))

    scannequin.set_param("seed", 7)
    scannequin.set_param("error_rate", 0.05)
    high = cast(str, scannequin(sample_text))

    assert diff_count(sample_text, high) >= diff_count(sample_text, low)
