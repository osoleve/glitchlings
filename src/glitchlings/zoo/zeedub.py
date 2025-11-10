from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Callable, cast

from ._rust_extensions import get_rust_operation, resolve_seed
from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

# Load the mandatory Rust implementation
_inject_zero_widths_rust = cast(
    Callable[[str, float, list[str], int | None], str],
    get_rust_operation("inject_zero_widths"),
)

_DEFAULT_ZERO_WIDTH_CHARACTERS: tuple[str, ...] = (
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
    "\u2060",  # WORD JOINER
)


def insert_zero_widths(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    characters: Sequence[str] | None = None,
) -> str:
    """Inject zero-width characters between non-space character pairs."""
    effective_rate = 0.02 if rate is None else rate

    palette: Sequence[str] = (
        tuple(characters) if characters is not None else _DEFAULT_ZERO_WIDTH_CHARACTERS
    )

    cleaned_palette = tuple(char for char in palette if char)
    if not cleaned_palette or not text:
        return text

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    seed_value = resolve_seed(seed, rng)
    return _inject_zero_widths_rust(text, clamped_rate, list(cleaned_palette), seed_value)


class Zeedub(Glitchling):
    """Glitchling that plants zero-width glyphs inside words."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        characters: Sequence[str] | None = None,
    ) -> None:
        effective_rate = 0.02 if rate is None else rate
        super().__init__(
            name="Zeedub",
            corruption_function=insert_zero_widths,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LAST,
            seed=seed,
            rate=effective_rate,
            characters=tuple(characters) if characters is not None else None,
        )

    def pipeline_operation(self) -> PipelineOperationPayload | None:
        rate_value = self.kwargs.get("rate")
        rate = 0.02 if rate_value is None else float(rate_value)

        raw_characters = self.kwargs.get("characters")
        if raw_characters is None:
            palette = tuple(_DEFAULT_ZERO_WIDTH_CHARACTERS)
        else:
            palette = tuple(str(char) for char in raw_characters if char)

        if not palette:
            return None

        return cast(
            PipelineOperationPayload,
            {
                "type": "zwj",
                "rate": rate,
                "characters": list(palette),
            },
        )


zeedub = Zeedub()


__all__ = ["Zeedub", "zeedub", "insert_zero_widths"]
