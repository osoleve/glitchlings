"""Homophone substitution glitchling implementation."""

from __future__ import annotations

import math
import random
from typing import Any, Sequence, cast

from glitchlings.lexicon import apply_casing

from ._rust_extensions import get_rust_operation
from .assets import load_homophone_groups
from ._text_utils import collect_word_tokens, split_preserving_whitespace
from .core import AttackOrder, AttackWave, Glitchling

_DEFAULT_RATE = 0.02
_DEFAULT_WEIGHTING = "flat"

_homophone_groups: tuple[tuple[str, ...], ...] = load_homophone_groups()


def _normalise_group(group: Sequence[str]) -> tuple[str, ...]:
    """Return a tuple of lowercase homophones preserving original order."""

    # Use dict.fromkeys to preserve the original ordering while de-duplicating.
    return tuple(dict.fromkeys(word.lower() for word in group if word))


def _build_dictionary(groups: Sequence[Sequence[str]]) -> dict[str, tuple[str, ...]]:
    """Return a mapping from word -> alternative homophones."""

    dictionary: dict[str, tuple[str, ...]] = {}
    for group in groups:
        normalised = _normalise_group(group)
        if len(normalised) < 2:
            continue
        for word in normalised:
            alternatives = tuple(candidate for candidate in normalised if candidate != word)
            if alternatives:
                dictionary[word] = alternatives
    return dictionary


_homophone_dictionary = _build_dictionary(_homophone_groups)
_ekkokin_rust = get_rust_operation("ekkokin_homophones")


def _normalise_weighting(weighting: str | None) -> str:
    if weighting is None:
        return _DEFAULT_WEIGHTING
    lowered = weighting.lower()
    if lowered not in _VALID_WEIGHTINGS:
        options = ", ".join(sorted(_VALID_WEIGHTINGS))
        raise ValueError(f"Unsupported weighting '{weighting}'. Expected one of: {options}")
    return lowered
  
  
def _apply_casing(template: str, candidate: str) -> str:
    """Return ``candidate`` adjusted to mirror the casing pattern of ``template``."""

    if not candidate:
        return candidate
    if template.isupper():
        return candidate.upper()
    if template.islower():
        return candidate.lower()
    if template[:1].isupper() and template[1:].islower():
        return candidate.capitalize()
    return candidate


def _choose_alternative(
    *,
    group: Sequence[str],
    source_word: str,
    rng: random.Random,
) -> str | None:
    """Return a replacement for ``source_word`` drawn from ``group``."""

    lowered = source_word.lower()
    candidates = [candidate for candidate in group if candidate != lowered]
    if not candidates:
        return None
    index = rng.randrange(len(candidates))
    replacement = candidates[index]
    return _apply_casing(source_word, replacement)


def _python_substitute_homophones(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    """Replace words in ``text`` with curated homophones."""

    del weighting  # Reserved for future weighting strategies.

    if not text:
        return text

    if math.isnan(rate):
        return text

    clamped_rate = max(0.0, min(1.0, rate))
    if clamped_rate <= 0.0:
        return text

    tokens = split_preserving_whitespace(text)
    candidates = collect_word_tokens(tokens)
    if not candidates:
        return text

    mutated = False

    for candidate in candidates:
        if not candidate.has_core:
            continue

        options = _homophone_dictionary.get(candidate.core.lower())
        if options is None:
            continue

        if rng.random() >= clamped_rate:
            continue

        replacement = rng.choice(options)
        adjusted = apply_casing(candidate.core, replacement)
        tokens[candidate.index] = f"{candidate.prefix}{adjusted}{candidate.suffix}"
        mutated = True

    if not mutated:
        return text

    return "".join(tokens)
def _maybe_replace_token(
    token: WordToken,
    rate: float,
    rng: random.Random,
) -> str | None:
    lookup = _homophone_lookup.get(token.core.lower())
    if lookup is None:
        return None
    if rng.random() >= rate:
        return None
    replacement_core = _choose_alternative(
        group=lookup,
        source_word=token.core,
        rng=rng,
    )
    if replacement_core is None:
        return None
    return f"{token.prefix}{replacement_core}{token.suffix}"


def substitute_homophones(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace words in ``text`` with curated homophones."""

    effective_rate = _DEFAULT_RATE if rate is None else rate

    active_rng = rng if rng is not None else random.Random(seed)

    clamped_rate = 0.0 if math.isnan(effective_rate) else max(0.0, min(1.0, effective_rate))
    if _ekkokin_rust is not None:
        return cast(
            str,
            _ekkokin_rust(text, clamped_rate, _DEFAULT_WEIGHTING, active_rng),
        )
    return _python_substitute_homophones(
        text,
        rate=clamped_rate,
        rng=active_rng,
    )


class Ekkokin(Glitchling):
    """Glitchling that swaps words for curated homophones."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        effective_rate = _DEFAULT_RATE if rate is None else rate
        super().__init__(
            name="Ekkokin",
            corruption_function=substitute_homophones,
            scope=AttackWave.WORD,
            order=AttackOrder.EARLY,
            seed=seed,
            pipeline_operation=_build_pipeline_descriptor,
            rate=effective_rate,
        )


def _build_pipeline_descriptor(glitch: Glitchling) -> dict[str, object] | None:
    rate = glitch.kwargs.get("rate")
    if rate is None:
        return None
    return {
        "type": "ekkokin",
        "rate": float(rate),
        "weighting": _DEFAULT_WEIGHTING,
    }


ekkokin = Ekkokin()


__all__ = [
    "Ekkokin",
    "ekkokin",
    "substitute_homophones",
    "_python_substitute_homophones",
]
