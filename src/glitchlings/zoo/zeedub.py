from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Glitchling

# Load Rust-accelerated operation if available
_inject_zero_widths_rust = get_rust_operation("inject_zero_widths")

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
    effective_rate = 0.02 if rate is None else rate

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
        getstate = getattr(rng, "getstate", None)
        setstate = getattr(rng, "setstate", None)
        snapshot = None
        if callable(getstate) and callable(setstate):
            try:
                snapshot = getstate()
            except TypeError:
                snapshot = None

        try:
            rust_result = _inject_zero_widths_rust(
                text, clamped_rate, list(cleaned_palette), rng
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            if snapshot is not None and callable(setstate):
                try:
                    setstate(snapshot)
                except (TypeError, ValueError):
                    pass
            return _python_insert_zero_widths(
                text,
                rate=clamped_rate,
                rng=rng,
                characters=cleaned_palette,
            )

        if isinstance(rust_result, str):
            return rust_result

        if snapshot is not None and callable(setstate):
            try:
                setstate(snapshot)
            except (TypeError, ValueError):
                pass
        return _python_insert_zero_widths(
            text,
            rate=clamped_rate,
            rng=rng,
            characters=cleaned_palette,
        )

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
