from __future__ import annotations

import importlib
import random
import re
from pathlib import Path

import pytest

core_module = importlib.import_module("glitchlings.zoo.core")
wherewolf_module = importlib.import_module("glitchlings.zoo.wherewolf")
glitchlings_package = importlib.import_module("glitchlings")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOMOPHONE_SOURCE = PROJECT_ROOT / "src" / "glitchlings" / "assets" / "wiki_homophones.txt"


def _parse_homophones(line: str) -> set[str]:
    tokens = {match for match in re.findall(r"[a-z']+", line.lower()) if match not in {"and"}}
    return tokens


def homophones_for(word: str) -> set[str]:
    assert HOMOPHONE_SOURCE.exists(), "homophone reference file is missing"
    for line in HOMOPHONE_SOURCE.read_text(encoding="utf-8").splitlines():
        words = _parse_homophones(line)
        if word in words:
            return words
    pytest.fail(f"No homophone entry found for '{word}' in {HOMOPHONE_SOURCE}")


def split_tokens(text: str) -> list[str]:
    return re.findall(r"\w+|\W+", text)


TRACKED_WORDS = {"allowed", "write", "heir"}
HOMOPHONE_SETS = {word: homophones_for(word) for word in TRACKED_WORDS}


def test_wherewolf_exports_word_level_glitchling() -> None:
    glitch = wherewolf_module.Wherewolf(seed=1337)

    assert glitch.level is core_module.AttackWave.WORD
    assert glitch.order is core_module.AttackOrder.EARLY

    assert wherewolf_module.wherewolf.level is core_module.AttackWave.WORD
    assert wherewolf_module.wherewolf.order is core_module.AttackOrder.EARLY

    assert hasattr(glitchlings_package, "Wherewolf")
    assert hasattr(glitchlings_package, "wherewolf")

    descriptor = glitch.pipeline_operation()
    assert descriptor == {
        "type": "wherewolf",
        "rate": pytest.approx(glitch.kwargs["rate"]),
        "weighting": "flat",
    }


@pytest.mark.parametrize("word", sorted(TRACKED_WORDS))
def test_reference_homophones_include_word(word: str) -> None:
    homophones = HOMOPHONE_SETS[word]
    assert word in homophones
    assert len(homophones) >= 2


def test_wherewolf_replaces_words_with_homophones() -> None:
    text = "Allowed writers write about the heir."

    glitch = wherewolf_module.Wherewolf(rate=1.0, seed=404)
    glitch.reset_rng(404)

    result = glitch(text)

    assert result != text

    before_tokens = split_tokens(text)
    after_tokens = split_tokens(result)

    assert len(before_tokens) == len(after_tokens)

    changed: dict[str, str] = {}

    for before, after in zip(before_tokens, after_tokens):
        lower_before = before.lower()
        lower_after = after.lower()

        if lower_before in TRACKED_WORDS:
            changed[lower_before] = lower_after
            homophone_options = HOMOPHONE_SETS[lower_before]
            assert lower_after in homophone_options
            assert lower_after != lower_before
        else:
            assert before == after

    assert set(changed) == TRACKED_WORDS


@pytest.mark.parametrize("source", ["allowed", "Allowed", "ALLOWED"])
def test_substitute_homophones_preserves_source_casing(source: str) -> None:
    result = wherewolf_module.substitute_homophones(source, rate=1.0, rng=random.Random(17))

    assert result != source
    alternatives = {candidate for candidate in HOMOPHONE_SETS["allowed"] if candidate != "allowed"}
    assert result.lower() in alternatives

    if source.isupper():
        assert result.isupper()
    elif source.islower():
        assert result.islower()
    elif source[:1].isupper() and source[1:].islower():
        assert result[:1].isupper()
        assert result[1:].islower()
    else:  # pragma: no cover - defensive guard for unexpected casing
        pytest.fail(f"Unhandled casing pattern in source word: {source}")
