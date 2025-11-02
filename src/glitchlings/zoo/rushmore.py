from __future__ import annotations

import math
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, cast

from ._rust_extensions import get_rust_operation
from ._text_utils import (
    WordToken,
    collect_word_tokens,
    split_preserving_whitespace,
    split_token_edges,
)
from .core import AttackWave, Glitchling


@unique
class RushmoreMode(Enum):
    """Enumerates Rushmore's selectable attack behaviours."""

    DELETE = "delete"
    DUPLICATE = "duplicate"
    SWAP = "swap"

    @classmethod
    def execution_order(cls) -> tuple["RushmoreMode", ...]:
        """Return the deterministic application order for Rushmore modes."""
        return (cls.DELETE, cls.DUPLICATE, cls.SWAP)


_MODE_ALIASES: dict[str, RushmoreMode] = {
    "delete": RushmoreMode.DELETE,
    "drop": RushmoreMode.DELETE,
    "rushmore": RushmoreMode.DELETE,
    "duplicate": RushmoreMode.DUPLICATE,
    "reduplicate": RushmoreMode.DUPLICATE,
    "reduple": RushmoreMode.DUPLICATE,
    "repeat": RushmoreMode.DUPLICATE,
    "swap": RushmoreMode.SWAP,
    "adjacent": RushmoreMode.SWAP,
    "adjax": RushmoreMode.SWAP,
}

_DEFAULT_RATES: dict[RushmoreMode, float] = {
    RushmoreMode.DELETE: 0.01,
    RushmoreMode.DUPLICATE: 0.01,
    RushmoreMode.SWAP: 0.05,
}


@dataclass(frozen=True)
class RushmoreRuntimeConfig:
    """Resolved Rushmore configuration used by both Python and Rust paths."""

    modes: tuple[RushmoreMode, ...]
    rates: dict[RushmoreMode, float]
    delete_unweighted: bool
    duplicate_unweighted: bool

    def has_mode(self, mode: RushmoreMode) -> bool:
        return mode in self.rates

    def to_pipeline_descriptor(self) -> dict[str, Any] | None:
        if not self.modes:
            return None

        if len(self.modes) == 1:
            mode = self.modes[0]
            rate = self.rates.get(mode)
            if rate is None:
                return None
            if mode is RushmoreMode.DELETE:
                return {
                    "type": "delete",
                    "rate": rate,
                    "unweighted": self.delete_unweighted,
                }
            if mode is RushmoreMode.DUPLICATE:
                return {
                    "type": "reduplicate",
                    "rate": rate,
                    "unweighted": self.duplicate_unweighted,
                }
            if mode is RushmoreMode.SWAP:
                return {
                    "type": "swap_adjacent",
                    "rate": rate,
                }
            return None

        descriptor: dict[str, Any] = {
            "type": "rushmore_combo",
            "modes": [mode.value for mode in self.modes],
        }
        if self.has_mode(RushmoreMode.DELETE):
            descriptor["delete"] = {
                "rate": self.rates[RushmoreMode.DELETE],
                "unweighted": self.delete_unweighted,
            }
        if self.has_mode(RushmoreMode.DUPLICATE):
            descriptor["duplicate"] = {
                "rate": self.rates[RushmoreMode.DUPLICATE],
                "unweighted": self.duplicate_unweighted,
            }
        if self.has_mode(RushmoreMode.SWAP):
            descriptor["swap"] = {"rate": self.rates[RushmoreMode.SWAP]}
        return descriptor


def _normalize_mode_item(value: RushmoreMode | str) -> list[RushmoreMode]:
    if isinstance(value, RushmoreMode):
        return [value]

    text = str(value).strip().lower()
    if not text:
        return []

    if text in {"all", "any", "full"}:
        return list(RushmoreMode.execution_order())

    tokens = [token for token in re.split(r"[+,\s]+", text) if token]
    if not tokens:
        return []

    modes: list[RushmoreMode] = []
    for token in tokens:
        mode = _MODE_ALIASES.get(token)
        if mode is None:
            raise ValueError(f"Unsupported Rushmore mode '{value}'")
        modes.append(mode)
    return modes


def _normalize_modes(
    modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None,
) -> tuple[RushmoreMode, ...]:
    if modes is None:
        candidates: Sequence[RushmoreMode | str] = (RushmoreMode.DELETE,)
    elif isinstance(modes, (RushmoreMode, str)):
        candidates = (modes,)
    else:
        collected = tuple(modes)
        candidates = collected if collected else (RushmoreMode.DELETE,)

    resolved: list[RushmoreMode] = []
    seen: set[RushmoreMode] = set()
    for candidate in candidates:
        for mode in _normalize_mode_item(candidate):
            if mode not in seen:
                seen.add(mode)
                resolved.append(mode)

    if not resolved:
        return (RushmoreMode.DELETE,)
    return tuple(resolved)


def _resolve_rate(
    *,
    mode: RushmoreMode,
    global_rate: float | None,
    specific_rate: float | None,
) -> float | None:
    baseline = specific_rate if specific_rate is not None else global_rate
    if baseline is None:
        return None

    value = float(baseline)
    value = max(0.0, value)
    if mode is RushmoreMode.SWAP:
        value = min(1.0, value)
    return value


def _resolve_rate_with_defaults(
    *,
    mode: RushmoreMode,
    global_rate: float | None,
    specific_rate: float | None,
) -> float:
    baseline = specific_rate if specific_rate is not None else global_rate
    if baseline is None:
        baseline = _DEFAULT_RATES[mode]

    value = float(baseline)
    value = max(0.0, value)
    if mode is RushmoreMode.SWAP:
        value = min(1.0, value)
    return value


def _resolve_rushmore_config(
    *,
    modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None,
    rate: float | None,
    delete_rate: float | None,
    duplicate_rate: float | None,
    swap_rate: float | None,
    unweighted: bool,
    delete_unweighted: bool | None,
    duplicate_unweighted: bool | None,
    allow_defaults: bool,
) -> RushmoreRuntimeConfig | None:
    normalized_modes = _normalize_modes(modes)
    global_rate = float(rate) if rate is not None else None

    rates: dict[RushmoreMode, float] = {}
    for mode in normalized_modes:
        if allow_defaults:
            if mode is RushmoreMode.DELETE:
                resolved = _resolve_rate_with_defaults(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=delete_rate,
                )
            elif mode is RushmoreMode.DUPLICATE:
                resolved = _resolve_rate_with_defaults(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=duplicate_rate,
                )
            else:
                resolved = _resolve_rate_with_defaults(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=swap_rate,
                )
        else:
            if mode is RushmoreMode.DELETE:
                resolved = _resolve_rate(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=delete_rate,
                )
            elif mode is RushmoreMode.DUPLICATE:
                resolved = _resolve_rate(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=duplicate_rate,
                )
            else:
                resolved = _resolve_rate(
                    mode=mode,
                    global_rate=global_rate,
                    specific_rate=swap_rate,
                )
            if resolved is None:
                return None
        if resolved is None:
            return None
        rates[mode] = resolved

    delete_flag = bool(delete_unweighted if delete_unweighted is not None else unweighted)
    duplicate_flag = bool(duplicate_unweighted if duplicate_unweighted is not None else unweighted)

    return RushmoreRuntimeConfig(
        modes=normalized_modes,
        rates=rates,
        delete_unweighted=delete_flag,
        duplicate_unweighted=duplicate_flag,
    )


# Load Rust-accelerated operations if available
_delete_random_words_rust = get_rust_operation("delete_random_words")
_reduplicate_words_rust = get_rust_operation("reduplicate_words")
_swap_adjacent_words_rust = get_rust_operation("swap_adjacent_words")


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

    allowed_deletions = min(len(weighted_tokens), math.floor(len(weighted_tokens) * effective_rate))
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


def delete_random_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    unweighted: bool = False,
) -> str:
    """Delete random words from the input text."""
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


def _python_reduplicate_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
    unweighted: bool = False,
) -> str:
    """Randomly reduplicate words in the text."""
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


def rushmore_attack(
    text: str,
    *,
    modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
    rate: float | None = None,
    delete_rate: float | None = None,
    duplicate_rate: float | None = None,
    swap_rate: float | None = None,
    unweighted: bool = False,
    delete_unweighted: bool | None = None,
    duplicate_unweighted: bool | None = None,
    rng: random.Random,
) -> str:
    """Apply the configured Rushmore attack modes to ``text``."""
    config = _resolve_rushmore_config(
        modes=modes,
        rate=rate,
        delete_rate=delete_rate,
        duplicate_rate=duplicate_rate,
        swap_rate=swap_rate,
        unweighted=unweighted,
        delete_unweighted=delete_unweighted,
        duplicate_unweighted=duplicate_unweighted,
        allow_defaults=True,
    )
    if config is None:
        return text

    result = text
    for mode in RushmoreMode.execution_order():
        if not config.has_mode(mode):
            continue

        rate_value = config.rates[mode]
        if rate_value <= 0.0:
            continue

        if mode is RushmoreMode.DELETE:
            result = delete_random_words(
                result,
                rate=rate_value,
                rng=rng,
                unweighted=config.delete_unweighted,
            )
        elif mode is RushmoreMode.DUPLICATE:
            result = reduplicate_words(
                result,
                rate=rate_value,
                rng=rng,
                unweighted=config.duplicate_unweighted,
            )
        else:
            result = swap_adjacent_words(result, rate=rate_value, rng=rng)

    return result


def _rushmore_pipeline_descriptor(glitchling: Glitchling) -> dict[str, Any] | None:
    config = _resolve_rushmore_config(
        modes=glitchling.kwargs.get("modes"),
        rate=glitchling.kwargs.get("rate"),
        delete_rate=glitchling.kwargs.get("delete_rate"),
        duplicate_rate=glitchling.kwargs.get("duplicate_rate"),
        swap_rate=glitchling.kwargs.get("swap_rate"),
        unweighted=glitchling.kwargs.get("unweighted", False),
        delete_unweighted=glitchling.kwargs.get("delete_unweighted"),
        duplicate_unweighted=glitchling.kwargs.get("duplicate_unweighted"),
        allow_defaults=False,
    )
    if config is None:
        return None
    return config.to_pipeline_descriptor()


class Rushmore(Glitchling):
    """Glitchling that bundles deletion, duplication, and swap attacks."""

    _param_aliases = {"mode": "modes"}

    def __init__(
        self,
        *,
        name: str = "Rushmore",
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        rate: float | None = None,
        delete_rate: float | None = None,
        duplicate_rate: float | None = None,
        swap_rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
        delete_unweighted: bool | None = None,
        duplicate_unweighted: bool | None = None,
    ) -> None:
        normalized_modes = _normalize_modes(modes)
        super().__init__(
            name=name,
            corruption_function=rushmore_attack,
            scope=AttackWave.WORD,
            seed=seed,
            pipeline_operation=_rushmore_pipeline_descriptor,
            modes=normalized_modes,
            rate=rate,
            delete_rate=delete_rate,
            duplicate_rate=duplicate_rate,
            swap_rate=swap_rate,
            unweighted=unweighted,
            delete_unweighted=delete_unweighted,
            duplicate_unweighted=duplicate_unweighted,
        )


rushmore = Rushmore()


__all__ = [
    "Rushmore",
    "rushmore",
    "RushmoreMode",
    "rushmore_attack",
    "delete_random_words",
    "_python_delete_random_words",
    "reduplicate_words",
    "_python_reduplicate_words",
    "swap_adjacent_words",
    "_python_swap_adjacent_words",
]
