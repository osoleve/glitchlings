import importlib
import random

import pytest

reduple_module = importlib.import_module("glitchlings.zoo.reduple")
rushmore_module = importlib.import_module("glitchlings.zoo.rushmore")
scannequin_module = importlib.import_module("glitchlings.zoo.scannequin")
redactyl_module = importlib.import_module("glitchlings.zoo.redactyl")


def test_reduple_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = reduple_module._python_reduplicate_words(
        text,
        reduplication_rate=0.5,
        rng=random.Random(123),
    )
    result = reduple_module.reduplicate_words(text, reduplication_rate=0.5, seed=123)
    assert (
        result
        == expected
        == "The The quick quick brown brown fox fox jumps over over the lazy lazy dog."
    )


def test_reduple_respects_explicit_rng():
    text = "Repeat me"
    expected = reduple_module._python_reduplicate_words(
        text,
        reduplication_rate=1.0,
        rng=random.Random(99),
    )
    result = reduple_module.reduplicate_words(
        text,
        reduplication_rate=1.0,
        rng=random.Random(99),
    )
    assert result == expected == "Repeat Repeat me me"


def test_rushmore_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = rushmore_module._python_delete_random_words(
        text,
        max_deletion_rate=0.5,
        rng=random.Random(123),
    )
    result = rushmore_module.delete_random_words(
        text, max_deletion_rate=0.5, seed=123
    )
    assert result == expected == "The over lazy."


def test_scannequin_matches_python_fallback():
    text = "The m rn"
    expected = scannequin_module._python_ocr_artifacts(
        text,
        error_rate=1.0,
        rng=random.Random(1),
    )
    result = scannequin_module.ocr_artifacts(text, error_rate=1.0, seed=1)
    assert result == expected == "Tlie rn m"


def test_redactyl_matches_python_fallback():
    text = "The quick brown fox jumps over the lazy dog."
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        redaction_rate=0.5,
        merge_adjacent=False,
        rng=random.Random(123),
    )
    result = redactyl_module.redact_words(text, redaction_rate=0.5, seed=123)
    assert (
        result
        == expected
        == "███ quick brown ███ █████ over the lazy ███."
    )


def test_redactyl_merge_adjacent_blocks():
    text = "redact these words"
    expected = redactyl_module._python_redact_words(
        text,
        replacement_char=redactyl_module.FULL_BLOCK,
        redaction_rate=1.0,
        merge_adjacent=True,
        rng=random.Random(7),
    )
    result = redactyl_module.redact_words(
        text,
        redaction_rate=1.0,
        merge_adjacent=True,
        seed=7,
    )
    assert result == expected == "█████████████████"


def test_redactyl_empty_text_raises_value_error():
    with pytest.raises(ValueError):
        redactyl_module.redact_words("", seed=1)
