from glitchlings import typogre, mim1c, reduple, rushmore, redactyl


def _count_blocks(s: str, block_char: str = "\u2588") -> int:
    return s.count(block_char)


def test_typogre_preserve_first_last():
    text = "Words stay"
    typogre.set_param("seed", 123)
    typogre.set_param("max_change_rate", 0.5)
    typogre.set_param("preserve_first_last", True)
    out = typogre(text)
    # Ensure first/last letters of each word are intact
    for orig, corr in zip(text.split(), out.split()):
        if len(orig) >= 2 and len(corr) >= 2:
            assert orig[0].lower() == corr[0].lower()
            assert orig[-1].lower() == corr[-1].lower()


def test_mim1c_replacement_rate_bounds(sample_text):
    mim1c.set_param("seed", 7)
    mim1c.set_param("replacement_rate", 0.02)
    out = mim1c(sample_text)
    # Should change no more than ~2% of alnum characters
    alnum = [c for c in sample_text if c.isalnum()]
    changed = sum(1 for a, b in zip(sample_text, out) if a != b and a.isalnum())
    assert changed <= int(len(alnum) * 0.02) + 2  # slack for discrete rounding


def test_reduple_rate_increases_tokens():
    text = "a b c d e f g h"
    reduple.set_param("seed", 5)
    reduple.set_param("reduplication_rate", 0.5)
    out = reduple(text)
    assert len(out.split()) >= len(text.split())


def test_rushmore_rate_decreases_tokens():
    text = "a b c d e f g h"
    rushmore.set_param("seed", 5)
    rushmore.set_param("max_deletion_rate", 0.5)
    out = rushmore(text)
    assert len(out.split()) <= len(text.split())


def test_redactyl_replacement_char_and_merge():
    text = "alpha beta gamma"
    redactyl.set_param("seed", 2)
    redactyl.set_param("redaction_rate", 1.0)
    redactyl.set_param("replacement_char", "#")
    redactyl.set_param("merge_adjacent", True)
    out = redactyl(text)
    assert set(out) <= {"#", " "}
    assert "# #" not in out  # merged
