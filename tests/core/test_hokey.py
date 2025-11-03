"""Tests for the Hokey expressive lengthening glitchling."""

from __future__ import annotations

import importlib
import random

import pytest

hokey_module = importlib.import_module("glitchlings.zoo.hokey")
core_module = importlib.import_module("glitchlings.zoo.core")


def test_hokey_extends_high_scoring_tokens():
    """Tokens with high lexical prior should be stretched when rate is high."""
    text = "wow that was so cool and so fun"
    result, events = hokey_module.extend_vowels(
        text,
        rate=1.0,
        seed=123,
        return_trace=True,
    )

    assert result != text
    stretched_tokens = {event.original for event in events}
    assert {"wow", "so", "cool"}.issubset(stretched_tokens)


def test_hokey_trace_reflects_output_changes():
    """Returned trace matches the stretched surface form."""
    text = "she is so so happy!!!"
    output, events = hokey_module.extend_vowels(text, rate=1.0, seed=7, return_trace=True)

    for event in events:
        assert event.stretched in output
        assert len(event.stretched) > len(event.original)
        assert event.repeats >= 2
        assert event.site.category in {"vowel", "digraph", "coda", "cvce"}


def test_hokey_downweights_long_words():
    """Extremely long words should be ignored even with aggressive rate."""
    text = "hi there supercalifragilisticexpialidocious"
    output, events = hokey_module.extend_vowels(
        text,
        rate=1.0,
        word_length_threshold=5,
        seed=11,
        return_trace=True,
    )

    assert output != "hi there supercalifragilisticexpialidocious"
    assert all("supercalifragilisticexpialidocious" not in event.stretched for event in events)


def test_hokey_sentiment_amplifies_length():
    """Positive sentiment context should yield longer stretches than negative."""
    positive = "wow I am so happy and excited!!! she is so cool"
    negative = "ugh I am so tired and angry... she is so cool"

    pos_output, pos_events = hokey_module.extend_vowels(
        positive,
        rate=0.9,
        seed=99,
        return_trace=True,
    )
    neg_output, neg_events = hokey_module.extend_vowels(
        negative,
        rate=0.9,
        seed=99,
        return_trace=True,
    )

    assert neg_output != negative

    # Find the stretch event corresponding to the final "so" token
    assert any(event.original == "so" for event in pos_events)
    assert any(event.original == "so" for event in neg_events)
    pos_so = max(
        (event for event in pos_events if event.original == "so"),
        key=lambda event: event.token_index,
    )
    neg_so = max(
        (event for event in neg_events if event.original == "so"),
        key=lambda event: event.token_index,
    )

    assert len(pos_output) > len(positive)
    assert pos_so.repeats >= neg_so.repeats


def test_hokey_is_deterministic_with_seed():
    """Hokey should produce identical output when seeded."""
    text = "cool code is so fun and neat"
    seed = 321

    result1 = hokey_module.extend_vowels(text, rate=0.6, seed=seed)
    result2 = hokey_module.extend_vowels(text, rate=0.6, seed=seed)

    assert result1 == result2


def test_hokey_handles_empty_text():
    """Empty input returns an empty output and trace."""
    output, events = hokey_module.extend_vowels("", return_trace=True)
    assert output == ""
    assert events == []


def test_hokey_handles_text_without_vowels():
    """Words without vowels can be stretched via coda heuristics."""
    text = "hmm brr"
    output = hokey_module.extend_vowels(text, rate=1.0, seed=42)
    assert output != text
    assert output.count('m') > text.count('m')
    assert output.count('r') > text.count('r')


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
