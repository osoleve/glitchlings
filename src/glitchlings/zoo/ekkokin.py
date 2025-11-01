"""Homophone substitution glitchling implementation."""

from __future__ import annotations

import math
import random
from typing import Any, Sequence, cast

from glitchlings.lexicon import compile_replacement_pattern, substitute_from_dictionary

from ._rust_extensions import get_rust_operation
from .assets import load_homophone_groups
from .core import AttackOrder, AttackWave, Glitchling

_DEFAULT_RATE = 0.02
_DEFAULT_WEIGHTING = "flat"
_VALID_WEIGHTINGS = {_DEFAULT_WEIGHTING}

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
_homophone_pattern = compile_replacement_pattern(_homophone_dictionary.keys())
_ekkokin_rust = get_rust_operation("ekkokin_homophones")


def _normalise_weighting(weighting: str | None) -> str:
    if weighting is None:
        return _DEFAULT_WEIGHTING
    lowered = weighting.lower()
    if lowered not in _VALID_WEIGHTINGS:
        options = ", ".join(sorted(_VALID_WEIGHTINGS))
        raise ValueError(f"Unsupported weighting '{weighting}'. Expected one of: {options}")
    return lowered


def _python_substitute_homophones(
    text: str,
    *,
    rate: float,
    weighting: str,
    rng: random.Random,
) -> str:
    """Replace words in ``text`` with curated homophones."""

    del weighting  # Reserved for future weighting strategies.
    return substitute_from_dictionary(
        text,
        _homophone_dictionary,
        rate=rate,
        rng=rng,
        pattern=_homophone_pattern,
    )


def substitute_homophones(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    weighting: str | None = None,
) -> str:
    """Replace words in ``text`` with curated homophones."""

    effective_rate = _DEFAULT_RATE if rate is None else rate
    normalized_weighting = _normalise_weighting(weighting)

    active_rng = rng if rng is not None else random.Random(seed)

    clamped_rate = 0.0 if math.isnan(effective_rate) else max(0.0, min(1.0, effective_rate))
    if _ekkokin_rust is not None:
        return cast(
            str,
            _ekkokin_rust(text, clamped_rate, normalized_weighting, active_rng),
        )
    return _python_substitute_homophones(
        text,
        rate=clamped_rate,
        weighting=normalized_weighting,
        rng=active_rng,
    )


class Ekkokin(Glitchling):
    """Glitchling that swaps words for curated homophones."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        weighting: str | None = None,
    ) -> None:
        effective_rate = _DEFAULT_RATE if rate is None else rate
        normalized_weighting = _normalise_weighting(weighting)
        super().__init__(
            name="Ekkokin",
            corruption_function=substitute_homophones,
            scope=AttackWave.WORD,
            order=AttackOrder.EARLY,
            seed=seed,
            pipeline_operation=_build_pipeline_descriptor,
            rate=effective_rate,
            weighting=normalized_weighting,
        )

    def set_param(self, key: str, value: Any) -> None:
        """Normalise weighting updates before storing them on the glitchling."""
        if key == "weighting":
            value = _normalise_weighting(cast(str | None, value))
        super().set_param(key, value)


def _build_pipeline_descriptor(glitch: Glitchling) -> dict[str, object] | None:
    rate = glitch.kwargs.get("rate")
    if rate is None:
        return None
    weighting = _normalise_weighting(cast(str | None, glitch.kwargs.get("weighting")))
    return {
        "type": "ekkokin",
        "rate": float(rate),
        "weighting": str(weighting),
    }


ekkokin = Ekkokin()


__all__ = [
    "Ekkokin",
    "ekkokin",
    "substitute_homophones",
    "_python_substitute_homophones",
]
