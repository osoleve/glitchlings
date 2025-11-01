"""Rushmore glitchling with configurable attack modes."""

from __future__ import annotations

import math
import random
import re
from typing import Any, Iterable, cast

from ._rust_extensions import get_rust_operation
from ._text_utils import (
    WordToken,
    collect_word_tokens,
    split_preserving_whitespace,
    split_token_edges,
)
from .core import AttackWave, Glitchling

# Load Rust-accelerated operations if available
_delete_random_words_rust = get_rust_operation("delete_random_words")
_reduplicate_words_rust = get_rust_operation("reduplicate_words")
_swap_adjacent_words_rust = get_rust_operation("swap_adjacent_words")

_VALID_ATTACK_MODES = {"delete", "duplicate", "swap", "all"}


def _normalise_attack_mode(value: str | None) -> str:
    """Return a canonical attack mode value."""

    if value is None:
        return "all"

    mode = value.lower().strip()
    if mode not in _VALID_ATTACK_MODES:
        supported = ", ".join(sorted(_VALID_ATTACK_MODES))
        raise ValueError(
            f"Unsupported Rushmore attack_mode '{value}'. Supported: {supported}"
        )
    return mode


def _attack_sequence(mode: str) -> Iterable[str]:
    if mode == "all":
        return ("duplicate", "delete", "swap")
    return (mode,)


def _python_delete_random_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
    unweighted: bool = False,
) -> str:
    """Delete random words from the input text while preserving whitespace."""

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return text

    tokens = split_preserving_whitespace(text)
    word_tokens = collect_word_tokens(tokens, skip_first_word=True)

    weighted_tokens: list[tuple[int, float, WordToken]] = []
    for token in word_tokens:
        weight = 1.0 if unweighted else 1.0 / float(token.core_length)
        weighted_tokens.append((token.index, weight, token))

    if not weighted_tokens:
        return text

    allowed_deletions = min(
        len(weighted_tokens), math.floor(len(weighted_tokens) * effective_rate)
    )
    if allowed_deletions <= 0:
        return text

    mean_weight = sum(weight for _, weight, _ in weighted_tokens) / len(weighted_tokens)

    deletions = 0
    for index, weight, token in weighted_tokens:
        if deletions >= allowed_deletions:
            break

        if effective_rate >= 1.0:
            probability = 1.0
        else:
            if mean_weight <= 0.0:
                probability = effective_rate
            else:
                probability = min(1.0, effective_rate * (weight / mean_weight))
        if rng.random() >= probability:
            continue

        prefix = token.prefix.strip()
        suffix = token.suffix.strip()
        tokens[index] = f"{prefix}{suffix}"

        deletions += 1

    text = "".join(tokens)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text


def _python_reduplicate_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
    unweighted: bool = False,
) -> str:
    tokens = split_preserving_whitespace(text)
    word_tokens = collect_word_tokens(tokens)

    weighted_tokens: list[tuple[int, float, WordToken]] = []
    for token in word_tokens:
        weight = 1.0 if unweighted else 1.0 / float(token.core_length)
        weighted_tokens.append((token.index, weight, token))

    if not weighted_tokens:
        return "".join(tokens)

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return "".join(tokens)

    mean_weight = sum(weight for _, weight, _ in weighted_tokens) / len(weighted_tokens)

    for index, weight, token in weighted_tokens:
        if effective_rate >= 1.0:
            probability = 1.0
        else:
            if mean_weight <= 0.0:
                probability = effective_rate
            else:
                probability = min(1.0, effective_rate * (weight / mean_weight))
        if rng.random() >= probability:
            continue

        prefix, core, suffix = token.prefix, token.core, token.suffix
        tokens[index] = f"{prefix}{core} {core}{suffix}"
    return "".join(tokens)


def _python_swap_adjacent_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    tokens = split_preserving_whitespace(text)
    if len(tokens) < 2:
        return text

    word_indices: list[int] = []
    for index, token in enumerate(tokens):
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


def delete_random_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    unweighted: bool = False,
) -> str:
    """Delete random words from the input text.

    Uses the optional Rust implementation when available.
    """

    effective_rate = 0.01 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    if _delete_random_words_rust is not None:
        return cast(str, _delete_random_words_rust(text, clamped_rate, unweighted_flag, rng))

    return _python_delete_random_words(
        text,
        rate=clamped_rate,
        rng=rng,
        unweighted=unweighted_flag,
    )


def reduplicate_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    unweighted: bool = False,
) -> str:
    """Randomly reduplicate words in the text."""

    effective_rate = 0.01 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    if _reduplicate_words_rust is not None:
        return cast(str, _reduplicate_words_rust(text, clamped_rate, unweighted_flag, rng))

    return _python_reduplicate_words(
        text,
        rate=clamped_rate,
        rng=rng,
        unweighted=unweighted_flag,
    )


def swap_adjacent_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Swap adjacent word cores while preserving spacing and punctuation."""

    effective_rate = 0.5 if rate is None else rate
    clamped_rate = max(0.0, min(effective_rate, 1.0))

    if rng is None:
        rng = random.Random(seed)

    if _swap_adjacent_words_rust is not None:
        return cast(str, _swap_adjacent_words_rust(text, clamped_rate, rng))

    return _python_swap_adjacent_words(text, rate=clamped_rate, rng=rng)


def rushmore_attacks(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    unweighted: bool = False,
    attack_mode: str | None = None,
) -> str:
    """Apply Rushmore's configurable attack modes to the provided text."""

    mode = _normalise_attack_mode(attack_mode)
    effective_rate = 0.01 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)

    text_cursor = text
    for operation in _attack_sequence(mode):
        if operation == "delete":
            text_cursor = delete_random_words(
                text_cursor,
                rate=effective_rate,
                rng=rng,
                unweighted=unweighted,
            )
        elif operation == "duplicate":
            text_cursor = reduplicate_words(
                text_cursor,
                rate=effective_rate,
                rng=rng,
                unweighted=unweighted,
            )
        elif operation == "swap":
            text_cursor = swap_adjacent_words(
                text_cursor,
                rate=effective_rate,
                rng=rng,
            )
        else:  # pragma: no cover - defensive guard against future edits
            raise AssertionError(f"Unknown Rushmore attack operation '{operation}'")

    return text_cursor


class Rushmore(Glitchling):
    """Glitchling that orchestrates deletions, duplicates, and swaps."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
        attack_mode: str | None = None,
    ) -> None:
        effective_rate = 0.01 if rate is None else rate
        canonical_mode = _normalise_attack_mode(attack_mode)
        super().__init__(
            name="Rushmore",
            corruption_function=rushmore_attacks,
            scope=AttackWave.WORD,
            seed=seed,
            rate=effective_rate,
            unweighted=unweighted,
            attack_mode=canonical_mode,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None

        mode = _normalise_attack_mode(self.kwargs.get("attack_mode"))
        unweighted = bool(self.kwargs.get("unweighted", False))

        if mode == "delete":
            return {"type": "delete", "rate": float(rate), "unweighted": unweighted}
        if mode == "duplicate":
            return {"type": "reduplicate", "rate": float(rate), "unweighted": unweighted}
        if mode == "swap":
            return {"type": "swap_adjacent", "rate": float(rate)}

        # When combining operations we fall back to the Python implementation.
        return None


rushmore = Rushmore()


__all__ = [
    "Rushmore",
    "rushmore",
    "rushmore_attacks",
    "delete_random_words",
    "reduplicate_words",
    "swap_adjacent_words",
]
