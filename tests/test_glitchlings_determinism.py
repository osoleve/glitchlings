from typing import cast
from glitchlings import (
    typogre,
    mim1c,
    jargoyle,
    reduple,
    rushmore,
    redactyl,
    scannequin,
)


def _twice(fn, text: str, seed: int = 42) -> tuple[str, str]:
    fn.reset_rng(seed)
    out1 = cast(str, fn(text))
    fn.reset_rng(seed)
    out2 = cast(str, fn(text))
    return out1, out2


def test_typogre_determinism(sample_text):
    typogre.set_param("seed", 42)
    typogre.set_param("max_change_rate", 0.03)
    typogre.set_param("preserve_first_last", True)
    a, b = _twice(typogre, sample_text)
    assert a == b


def test_mim1c_determinism(sample_text):
    mim1c.set_param("seed", 42)
    mim1c.set_param("replacement_rate", 0.03)
    mim1c.set_param("classes", ["LATIN", "GREEK", "CYRILLIC"])  # explicit default
    a, b = _twice(mim1c, sample_text)
    assert a == b


def test_jargoyle_determinism(sample_text):
    jargoyle.set_param("seed", 42)
    jargoyle.set_param("replacement_rate", 0.05)
    a, b = _twice(jargoyle, sample_text)
    assert a == b


def test_reduple_determinism(sample_text):
    reduple.set_param("seed", 42)
    reduple.set_param("reduplication_rate", 0.05)
    a, b = _twice(reduple, sample_text)
    assert a == b


def test_rushmore_determinism(sample_text):
    rushmore.set_param("seed", 42)
    rushmore.set_param("max_deletion_rate", 0.01)
    a, b = _twice(rushmore, sample_text)
    assert a == b


def test_redactyl_determinism(sample_text):
    redactyl.set_param("seed", 42)
    redactyl.set_param("redaction_rate", 0.05)
    a, b = _twice(redactyl, sample_text)
    assert a == b


def test_scannequin_determinism(sample_text):
    scannequin.set_param("seed", 42)
    scannequin.set_param("error_rate", 0.03)
    a, b = _twice(scannequin, sample_text)
    assert a == b
