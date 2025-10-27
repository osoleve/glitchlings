from __future__ import annotations

import random
from typing import Any, cast

from ._rate import resolve_rate
from ._rust_extensions import get_rust_operation
from ._text_utils import split_preserving_whitespace, split_token_edges
from .core import AttackWave, Glitchling

# Load Rust-accelerated operation if available
_swap_adjacent_words_rust = get_rust_operation("swap_adjacent_words")


def _python_swap_adjacent_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    """Swap the cores of adjacent words while keeping affixes and spacing intact."""
    tokens = split_preserving_whitespace(text)
    if len(tokens) < 2:
        return text

    word_indices: list[int] = []
    for index in range(len(tokens)):
        token = tokens[index]
        if not token or token.isspace():
            continue
        if index % 2 == 0:
            word_indices.append(index)

    if len(word_indices) < 2:
        return text

    clamped = max(0.0, min(rate, 1.0))
    if clamped <= 0.0:
        return text

    for cursor in range(0, len(word_indices) - 1, 2):
        left_index = word_indices[cursor]
        right_index = word_indices[cursor + 1]

        left_token = tokens[left_index]
        right_token = tokens[right_index]

        left_prefix, left_core, left_suffix = split_token_edges(left_token)
        right_prefix, right_core, right_suffix = split_token_edges(right_token)

        if not left_core or not right_core:
            continue

        should_swap = clamped >= 1.0 or rng.random() < clamped
        if not should_swap:
            continue

        tokens[left_index] = f"{left_prefix}{right_core}{left_suffix}"
        tokens[right_index] = f"{right_prefix}{left_core}{right_suffix}"

    return "".join(tokens)


def swap_adjacent_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Swap adjacent word cores while preserving spacing and punctuation."""
    effective_rate = resolve_rate(rate=rate, default=0.5)
    clamped_rate = max(0.0, min(effective_rate, 1.0))

    if rng is None:
        rng = random.Random(seed)

    if _swap_adjacent_words_rust is not None:
        return cast(str, _swap_adjacent_words_rust(text, clamped_rate, rng))

    return _python_swap_adjacent_words(text, rate=clamped_rate, rng=rng)


class Adjax(Glitchling):
    """Glitchling that swaps adjacent words to scramble local semantics."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        effective_rate = resolve_rate(rate=rate, default=0.5)
        super().__init__(
            name="Adjax",
            corruption_function=swap_adjacent_words,
            scope=AttackWave.WORD,
            seed=seed,
            rate=effective_rate,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None
        return {
            "type": "swap_adjacent",
            "swap_rate": float(rate),
        }


adjax = Adjax()


__all__ = ["Adjax", "adjax", "swap_adjacent_words"]
