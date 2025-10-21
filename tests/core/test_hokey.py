"""Tests for the Hokey glitchling (vowel extension for emphasis)."""

from __future__ import annotations

import importlib
import random

import pytest

hokey_module = importlib.import_module("glitchlings.zoo.hokey")
core_module = importlib.import_module("glitchlings.zoo.core")


def test_hokey_extends_vowels_in_short_words():
    """Verify that Hokey extends vowels in short words."""
    text = "cool code is so fun"
    rng = random.Random(42)
    result = hokey_module._python_extend_vowels(text, rate=1.0, rng=rng)

    # With rate=1.0, all short words should be affected
    assert result != text
    # The result should be longer than the original
    assert len(result) > len(text)
    # Should contain extended vowels
    assert any(c * 3 in result for c in "aeiou")


def test_hokey_respects_rate_parameter():
    """Verify that the rate parameter controls how many words are affected."""
    text = "cool code is so fun"

    # Rate of 0.0 should not affect any words
    rng_zero = random.Random(123)
    result_zero = hokey_module._python_extend_vowels(text, rate=0.0, rng=rng_zero)
    assert result_zero == text

    # Rate of 1.0 should affect more words than rate of 0.3
    rng_low = random.Random(123)
    result_low = hokey_module._python_extend_vowels(text, rate=0.3, rng=rng_low)

    rng_high = random.Random(123)
    result_high = hokey_module._python_extend_vowels(text, rate=1.0, rng=rng_high)

    # Higher rate should result in more changes
    assert len(result_high) >= len(result_low)


def test_hokey_is_deterministic():
    """Verify that Hokey produces identical output with the same seed."""
    text = "cool code is so fun and neat"
    seed = 999

    result1 = hokey_module.extend_vowels(text, rate=0.5, seed=seed)
    result2 = hokey_module.extend_vowels(text, rate=0.5, seed=seed)

    assert result1 == result2


def test_hokey_python_fallback_with_explicit_rng():
    """Verify that explicit RNG parameter works correctly."""
    text = "wow this is cool"
    rng1 = random.Random(555)
    rng2 = random.Random(555)

    result1 = hokey_module._python_extend_vowels(text, rate=0.8, rng=rng1)
    result2 = hokey_module._python_extend_vowels(text, rate=0.8, rng=rng2)

    assert result1 == result2


def test_hokey_preserves_whitespace_and_punctuation():
    """Verify that Hokey preserves spacing and punctuation."""
    text = "Hello, world! How are you?"
    result = hokey_module.extend_vowels(text, rate=1.0, seed=42)

    # Should preserve commas, exclamation marks, question marks
    assert "," in result
    assert "!" in result
    assert "?" in result
    # Should preserve general structure
    assert result.startswith("H")


def test_hokey_handles_empty_text():
    """Verify that Hokey handles empty text gracefully."""
    result = hokey_module.extend_vowels("", rate=0.5, seed=42)
    assert result == ""


def test_hokey_handles_text_without_vowels():
    """Verify that Hokey handles text without vowels."""
    text = "xyz qrs"
    result = hokey_module.extend_vowels(text, rate=1.0, seed=42)
    # Should return unchanged if no vowels found
    assert result == text


def test_hokey_pipeline_descriptor():
    """Verify that Hokey provides correct pipeline operation descriptor."""
    glitch = hokey_module.Hokey(seed=2024)
    descriptor = glitch.pipeline_operation()

    assert descriptor is not None
    assert descriptor["type"] == "hokey"
    assert "rate" in descriptor
    assert "extension_min" in descriptor
    assert "extension_max" in descriptor
    assert "word_length_threshold" in descriptor


def test_hokey_class_initialization():
    """Verify that Hokey class initializes correctly with parameters."""
    glitch = hokey_module.Hokey(
        rate=0.7,
        extension_min=3,
        extension_max=6,
        word_length_threshold=8,
        seed=123
    )

    assert glitch.name == "Hokey"
    assert glitch.level == core_module.AttackWave.CHARACTER
    assert glitch.order == core_module.AttackOrder.FIRST
    assert glitch.seed == 123


def test_hokey_invokes_python_fallback_when_rust_unavailable(monkeypatch):
    """Verify that Hokey falls back to Python implementation when Rust is unavailable."""
    monkeypatch.setattr(hokey_module, "_hokey_rust", None, raising=False)

    text = "cool beans"
    seed = 99
    derived = core_module.Gaggle.derive_seed(seed, hokey_module.hokey.name, 0)

    # Use the same parameters as the default Hokey glitchling
    expected = hokey_module._python_extend_vowels(
        text,
        rate=0.3,  # Default rate
        extension_min=2,
        extension_max=5,
        word_length_threshold=6,
        rng=random.Random(derived)
    )

    glitch = hokey_module.Hokey(seed=seed)
    glitch.reset_rng(seed)
    result = glitch(text)

    assert result == expected


def test_hokey_respects_word_length_threshold():
    """Verify that only short words are affected based on threshold."""
    # "supercalifragilisticexpialidocious" is very long, should not be affected
    # "hi" is very short, should be affected
    text = "hi there supercalifragilisticexpialidocious"

    result = hokey_module.extend_vowels(
        text,
        rate=1.0,
        word_length_threshold=5,
        seed=42
    )

    # The long word should remain unchanged
    assert "supercalifragilisticexpialidocious" in result
    # Short words should be affected (text should be longer)
    assert len(result) > len(text)


def test_hokey_glitchling_can_be_called_directly():
    """Verify that Hokey instances are callable."""
    glitch = hokey_module.Hokey(rate=0.5, seed=123)
    text = "cool stuff"
    result = glitch(text)

    assert isinstance(result, str)
    # Should potentially modify the text (though with low rate might not)
    assert len(result) >= len(text)
