"""Homophone substitution glitchling implementation."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Sequence, cast

from ._rust_extensions import get_rust_operation
from .assets import load_homophone_groups
from .core import AttackOrder, AttackWave
from .core import Glitchling as _GlitchlingRuntime

_DEFAULT_RATE = 0.02
_DEFAULT_WEIGHTING = "flat"

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
_ekkokin_rust = cast(
    Callable[[str, float, str, random.Random], str] | None,
    get_rust_operation("ekkokin_homophones"),
)


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

    effective_rate = _DEFAULT_RATE if rate is None else rate

    active_rng = rng if rng is not None else random.Random(seed)

    clamped_rate = 0.0 if math.isnan(effective_rate) else max(0.0, min(1.0, effective_rate))

    if _ekkokin_rust is None:
        raise RuntimeError(
            "Ekkokin requires the glitchlings._zoo_rust extension. Rebuild the project "
            "with `pip install .` or `maturin develop` to enable homophone substitution.",
        )

    return _ekkokin_rust(text, clamped_rate, _DEFAULT_WEIGHTING, active_rng)
    



class Ekkokin(_GlitchlingBase):
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


def _build_pipeline_descriptor(glitch: _GlitchlingBase) -> dict[str, object] | None:
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
]
