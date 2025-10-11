from __future__ import annotations

import math
import random
from collections.abc import Sequence

from .core import Glitchling, AttackWave, AttackOrder
from ._rate import resolve_rate

try:
    from glitchlings._zoo_rust import inject_zero_widths as _inject_zero_widths_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _inject_zero_widths_rust = None

_DEFAULT_ZERO_WIDTH_CHARACTERS: tuple[str, ...] = (
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
    "\u2060",  # WORD JOINER
)


def _python_insert_zero_widths(
    text: str,
    *,
    rate: float,
    rng: random.Random,
    characters: Sequence[str],
) -> str:
    if not text:
        return text

    palette = [char for char in characters if char]
    if not palette:
        return text

    positions = [
        index + 1
        for index in range(len(text) - 1)
        if not text[index].isspace() and not text[index + 1].isspace()
    ]
    if not positions:
        return text

    total = len(positions)
    clamped_rate = max(0.0, rate)
    if clamped_rate <= 0.0:
        return text

    target = clamped_rate * total
    count = math.floor(target)
    remainder = target - count
    if remainder > 0.0 and rng.random() < remainder:
        count += 1
    count = min(total, count)

    if count <= 0:
        return text

    chosen = rng.sample(positions, count)
    chosen.sort()

    chars = list(text)
    for position in reversed(chosen):
        chars.insert(position, rng.choice(palette))

    return "".join(chars)


def insert_zero_widths(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    characters: Sequence[str] | None = None,
) -> str:
    """Inject zero-width characters between non-space character pairs."""

    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=None,
        default=0.02,
        legacy_name="rate",
    )

    if rng is None:
        rng = random.Random(seed)

    palette: Sequence[str] = (
        tuple(characters) if characters is not None else _DEFAULT_ZERO_WIDTH_CHARACTERS
    )

    cleaned_palette = tuple(char for char in palette if char)
    if not cleaned_palette or not text:
        return text

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    if _inject_zero_widths_rust is not None:
        return _inject_zero_widths_rust(text, clamped_rate, list(cleaned_palette), rng)

    return _python_insert_zero_widths(
        text,
        rate=clamped_rate,
        rng=rng,
        characters=cleaned_palette,
    )


class Zeedub(Glitchling):
    """Glitchling that plants zero-width glyphs inside words."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        characters: Sequence[str] | None = None,
    ) -> None:
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=None,
            default=0.02,
            legacy_name="rate",
        )
        super().__init__(
            name="Zeedub",
            corruption_function=insert_zero_widths,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LAST,
            seed=seed,
            rate=effective_rate,
            characters=tuple(characters) if characters is not None else None,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None

        raw_characters = self.kwargs.get("characters")
        if raw_characters is None:
            palette = tuple(_DEFAULT_ZERO_WIDTH_CHARACTERS)
        else:
            palette = tuple(str(char) for char in raw_characters if char)

        if not palette:
            return None

        return {
            "type": "zwj",
            "rate": float(rate),
            "characters": list(palette),
        }


zeedub = Zeedub()


__all__ = ["Zeedub", "zeedub", "insert_zero_widths"]
