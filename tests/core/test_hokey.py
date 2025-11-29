"""Tests for the Hokey expressive lengthening glitchling."""

from __future__ import annotations

import importlib
import re

import pytest

hokey_module = importlib.import_module("glitchlings.zoo.hokey")
core_module = importlib.import_module("glitchlings.zoo.core")


def test_hokey_extends_high_scoring_tokens():
    """Tokens with high lexical prior should be stretched when rate is high."""
    text = "wow that was so cool and so fun"
    result = hokey_module.extend_vowels(
        text,
        rate=1.0,
        seed=123,
    )

    assert result != text
    assert "woww" in result
    assert "sooo" in result
    assert "cooo" in result


def test_hokey_output_contains_stretches():
    """Stretched tokens should appear longer than their originals."""
    text = "she is so so happy!!!"
    output = hokey_module.extend_vowels(text, rate=1.0, seed=7)

    original_tokens = re.findall(r"[A-Za-z]+", text)
    stretched_tokens = re.findall(r"[A-Za-z]+", output)

    assert len(original_tokens) == len(stretched_tokens)
    assert any(
        len(stretched) > len(original)
        for stretched, original in zip(stretched_tokens, original_tokens)
    )
    assert any("oo" in token for token in stretched_tokens)


def test_hokey_downweights_long_words():
    """Extremely long words should be ignored even with aggressive rate."""
    text = "hi there supercalifragilisticexpialidocious"
    output = hokey_module.extend_vowels(
        text,
        rate=1.0,
        word_length_threshold=5,
        seed=11,
    )

    assert output != "hi there supercalifragilisticexpialidocious"
    assert output.endswith("supercalifragilisticexpialidocious")


def test_hokey_sentiment_amplifies_length():
    """Positive sentiment context should yield longer stretches than negative."""
    positive = "wow I am so happy and excited!!! she is so cool"
    negative = "ugh I am so tired and angry... she is so cool"

    pos_output = hokey_module.extend_vowels(
        positive,
        rate=0.9,
        seed=99,
    )
    neg_output = hokey_module.extend_vowels(
        negative,
        rate=0.9,
        seed=99,
    )

    assert neg_output != negative

    pos_matches = list(re.finditer(r"hap+y+", pos_output.lower()))
    neg_matches = list(re.finditer(r"angry+", neg_output.lower()))

    assert pos_matches, "expected to find stretched 'happy' token"
    assert neg_matches, "expected to find stretched 'angry' token"

    pos_happy = max(len(match.group(0)) for match in pos_matches)
    neg_angry = max(len(match.group(0)) for match in neg_matches)

    assert len(pos_output) > len(positive)
    assert pos_happy > len("happy")
    assert pos_happy >= neg_angry


def test_hokey_is_deterministic_with_seed():
    """Hokey should produce identical output when seeded."""
    text = "cool code is so fun and neat"
    seed = 321

    result1 = hokey_module.extend_vowels(text, rate=0.6, seed=seed)
    result2 = hokey_module.extend_vowels(text, rate=0.6, seed=seed)

    assert result1 == result2


def test_hokey_handles_empty_text():
    """Empty input returns an empty output."""
    output = hokey_module.extend_vowels("")
    assert output == ""


def test_hokey_handles_text_without_vowels():
    """Words without vowels can be stretched via coda heuristics."""
    text = "hmm brr"
    output = hokey_module.extend_vowels(text, rate=1.0, seed=42)
    assert output != text
    assert output.count("m") > text.count("m")
    assert output.count("r") > text.count("r")


def test_hokey_pipeline_descriptor_contains_new_parameters():
    """Pipeline descriptor advertises the new base probability parameter."""
    glitch = hokey_module.Hokey(seed=2024, base_p=0.33)
    descriptor = glitch.pipeline_operation()

    assert descriptor == {
        "type": "hokey",
        "rate": pytest.approx(0.3),
        "extension_min": 2,
        "extension_max": 5,
        "word_length_threshold": 6,
        "base_p": 0.33,
    }


def test_hokey_class_initialization_tracks_parameters():
    """Hokey constructor should surface provided parameters."""
    glitch = hokey_module.Hokey(
        rate=0.7,
        extension_min=3,
        extension_max=6,
        word_length_threshold=8,
        base_p=0.4,
        seed=123,
    )

    assert glitch.name == "Hokey"
    assert glitch.level == core_module.AttackWave.CHARACTER
    assert glitch.order == core_module.AttackOrder.FIRST
    assert glitch.kwargs["base_p"] == 0.4


def test_hokey_glitchling_callable_returns_str():
    """Hokey instances remain callable and return strings."""
    glitch = hokey_module.Hokey(rate=0.5, seed=123)
    text = "cool stuff"
    result = glitch(text)

    assert isinstance(result, str)
    assert len(result) >= len(text)


def test_hokey_handles_utf8_characters_correctly():
    """UTF-8 characters should be counted properly when applying stretches."""
    text = "café cool"
    output = hokey_module.extend_vowels(
        text,
        rate=1.0,
        word_length_threshold=6,
        extension_min=2,
        extension_max=3,
        seed=42,
    )

    assert output != text
    assert len(output) > len(text)
