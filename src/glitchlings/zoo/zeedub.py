from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any, Literal, cast

from glitchlings.constants import (
    DEFAULT_ZEEDUB_MAX_CONSECUTIVE,
    DEFAULT_ZEEDUB_PLACEMENT,
    DEFAULT_ZEEDUB_RATE,
    DEFAULT_ZEEDUB_VISIBILITY,
    ZEEDUB_DEFAULT_ZERO_WIDTHS,
)
from glitchlings.internal.rust_ffi import (
    inject_zero_widths_rust,
    resolve_seed,
)

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload
from .validation import (
    normalize_zeedub_max_consecutive,
    normalize_zeedub_placement,
    normalize_zeedub_visibility,
)

_DEFAULT_ZERO_WIDTH_CHARACTERS: tuple[str, ...] = ZEEDUB_DEFAULT_ZERO_WIDTHS


def insert_zero_widths(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    characters: Sequence[str] | None = None,
    visibility: str | None = None,
    placement: str | None = None,
    max_consecutive: int | None = None,
) -> str:
    """Inject zero-width characters between non-space character pairs.

    Args:
        text: Input text.
        rate: Probability of injection at each eligible position.
        seed: Deterministic seed.
        rng: Optional random.Random instance for seed derivation.
        characters: Custom palette of zero-width characters.
        visibility: Visibility mode ('glyphless', 'with_joiners', 'semi_visible').
            When characters is empty, auto-populates palette from this mode.
        placement: Placement mode ('random', 'grapheme_boundary', 'script_aware').
        max_consecutive: Maximum consecutive insertions (0 for unlimited, default 4).

    Returns:
        Text with injected zero-width characters.
    """
    effective_rate = DEFAULT_ZEEDUB_RATE if rate is None else rate

    palette: Sequence[str] = (
        tuple(characters) if characters is not None else ZEEDUB_DEFAULT_ZERO_WIDTHS
    )

    cleaned_palette = tuple(char for char in palette if char)
    if not text:
        return text

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    seed_value = resolve_seed(seed, rng)
    return inject_zero_widths_rust(
        text,
        clamped_rate,
        list(cleaned_palette),
        seed_value,
        visibility=visibility,
        placement=placement,
        max_consecutive=max_consecutive,
    )


class Zeedub(Glitchling):
    """Glitchling that plants zero-width glyphs inside words.

    Zeedub supports three placement modes:

    - **random** (default): Insert between any adjacent non-whitespace characters
    - **grapheme_boundary**: Only insert at grapheme cluster boundaries (safer)
    - **script_aware**: ZWJ/ZWNJ only where linguistically meaningful

    And three visibility modes:

    - **glyphless** (default): ZWSP, ZWNJ, ZWJ, WJ, CGJ—true invisibles only
    - **with_joiners**: Adds variation selectors (VS1–VS16)
    - **semi_visible**: Adds hair space, thin space, narrow NBSP

    By default, caps consecutive invisible insertions at 4 to prevent
    pathological sequences. Set max_consecutive=0 to disable this limit.
    """

    flavor = "I'm invoking my right to remain silent."

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        characters: Sequence[str] | None = None,
        visibility: Literal["glyphless", "with_joiners", "semi_visible"] | None = None,
        placement: Literal["random", "grapheme_boundary", "script_aware"] | None = None,
        max_consecutive: int | None = None,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_ZEEDUB_RATE if rate is None else rate
        effective_visibility = normalize_zeedub_visibility(visibility, DEFAULT_ZEEDUB_VISIBILITY)
        effective_placement = normalize_zeedub_placement(placement, DEFAULT_ZEEDUB_PLACEMENT)
        effective_max_consecutive = normalize_zeedub_max_consecutive(
            max_consecutive, DEFAULT_ZEEDUB_MAX_CONSECUTIVE
        )

        super().__init__(
            name="Zeedub",
            corruption_function=insert_zero_widths,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LAST,
            seed=seed,
            rate=effective_rate,
            characters=tuple(characters) if characters is not None else None,
            visibility=effective_visibility,
            placement=effective_placement,
            max_consecutive=effective_max_consecutive,
            **kwargs,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        rate = float(self.kwargs.get("rate", DEFAULT_ZEEDUB_RATE))

        raw_characters = self.kwargs.get("characters")
        palette = (
            tuple(ZEEDUB_DEFAULT_ZERO_WIDTHS)
            if raw_characters is None
            else tuple(str(char) for char in raw_characters if char)
        )

        visibility = str(self.kwargs.get("visibility", DEFAULT_ZEEDUB_VISIBILITY))
        placement = str(self.kwargs.get("placement", DEFAULT_ZEEDUB_PLACEMENT))
        max_consecutive = int(self.kwargs.get("max_consecutive", DEFAULT_ZEEDUB_MAX_CONSECUTIVE))

        return cast(
            PipelineOperationPayload,
            {
                "type": "zwj",
                "rate": rate,
                "characters": list(palette),
                "visibility": visibility,
                "placement": placement,
                "max_consecutive": max_consecutive,
            },
        )


zeedub = Zeedub()


__all__ = ["Zeedub", "zeedub", "insert_zero_widths"]
