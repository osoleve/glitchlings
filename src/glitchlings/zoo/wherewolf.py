"""Homophone substitution glitchling implementation."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from glitchlings.assets import load_homophone_groups
from glitchlings.constants import DEFAULT_WHEREWOLF_RATE, DEFAULT_WHEREWOLF_WEIGHTING
from glitchlings.internal.rust_ffi import resolve_seed, substitute_homophones_rust

from .core import AttackOrder, AttackWave
from .core import Glitchling as _GlitchlingRuntime

_homophone_groups: tuple[tuple[str, ...], ...] = load_homophone_groups()


def _normalise_group(group: Sequence[str]) -> tuple[str, ...]:
    """Return a tuple of lowercase homophones preserving original order."""

    # Use dict.fromkeys to preserve the original ordering while de-duplicating.
    return tuple(dict.fromkeys(word.lower() for word in group if word))


def _build_lookup(groups: Iterable[Sequence[str]]) -> Mapping[str, tuple[str, ...]]:
    """Return a mapping from word -> homophone group."""

    lookup: dict[str, tuple[str, ...]] = {}
    for group in groups:
        normalised = _normalise_group(group)
        if len(normalised) < 2:
            continue
        for word in normalised:
            lookup[word] = normalised
    return lookup


_homophone_lookup = _build_lookup(_homophone_groups)


class _GlitchlingProtocol:
    kwargs: dict[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def reset_rng(self, seed: int | None = None) -> None: ...

    def pipeline_operation(self) -> dict[str, object] | None: ...


if TYPE_CHECKING:
    from .core import Glitchling as _GlitchlingBase
else:
    _GlitchlingBase = _GlitchlingRuntime


def substitute_homophones(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace words in ``text`` with curated homophones."""

    effective_rate = DEFAULT_WHEREWOLF_RATE if rate is None else rate

    clamped_rate = 0.0 if math.isnan(effective_rate) else max(0.0, min(1.0, effective_rate))

    return substitute_homophones_rust(
        text,
        clamped_rate,
        DEFAULT_WHEREWOLF_WEIGHTING,
        resolve_seed(seed, rng),
    )


class Wherewolf(_GlitchlingBase):
    """Glitchling that swaps words for curated homophones."""

    flavor = "Homophonic idiolectician. There leased favourite flavour? Orange."

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_WHEREWOLF_RATE if rate is None else rate
        super().__init__(
            name="Wherewolf",
            corruption_function=substitute_homophones,
            scope=AttackWave.WORD,
            order=AttackOrder.EARLY,
            seed=seed,
            pipeline_operation=_build_pipeline_descriptor,
            rate=effective_rate,
            **kwargs,
        )


def _build_pipeline_descriptor(glitch: _GlitchlingBase) -> dict[str, object]:
    rate_value = glitch.kwargs.get("rate")
    rate = DEFAULT_WHEREWOLF_RATE if rate_value is None else float(rate_value)
    return {
        "type": "wherewolf",
        "rate": rate,
        "weighting": DEFAULT_WHEREWOLF_WEIGHTING,
    }


wherewolf = Wherewolf()


__all__ = [
    "Wherewolf",
    "wherewolf",
    "substitute_homophones",
]
