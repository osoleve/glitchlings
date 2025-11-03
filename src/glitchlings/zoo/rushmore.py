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


@dataclass(frozen=True)
class _WeightedWordToken:
    """Internal helper that bundles weighting metadata with a token."""

    token: WordToken
    weight: float


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


def _resolve_mode_rate(
    *,
    mode: RushmoreMode,
    global_rate: float | None,
    specific_rate: float | None,
    allow_default: bool,
) -> float | None:
    baseline = specific_rate if specific_rate is not None else global_rate
    if baseline is None:
        if not allow_default:
            return None
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

    mode_specific_rates: dict[RushmoreMode, float | None] = {
        RushmoreMode.DELETE: delete_rate,
        RushmoreMode.DUPLICATE: duplicate_rate,
        RushmoreMode.SWAP: swap_rate,
    }

    rates: dict[RushmoreMode, float] = {}
    for mode in normalized_modes:
        resolved = _resolve_mode_rate(
            mode=mode,
            global_rate=global_rate,
            specific_rate=mode_specific_rates[mode],
            allow_default=allow_defaults,
        )
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


def _build_weighted_word_tokens(
    tokens: Sequence[str],
    *,
    skip_first_word: bool,
    unweighted: bool,
) -> tuple[list[_WeightedWordToken], float]:
    word_tokens = collect_word_tokens(tokens, skip_first_word=skip_first_word)
    weighted: list[_WeightedWordToken] = []
    for token in word_tokens:
        weight = 1.0 if unweighted else 1.0 / float(token.core_length)
        weighted.append(_WeightedWordToken(token=token, weight=weight))

    if not weighted:
        return [], 0.0

    mean_weight = sum(candidate.weight for candidate in weighted) / len(weighted)
    return weighted, mean_weight


def _calculate_weighted_probability(
    *,
    effective_rate: float,
    weight: float,
    mean_weight: float,
) -> float:
    if effective_rate >= 1.0:
        return 1.0
    if mean_weight <= 0.0:
        return min(1.0, effective_rate)
    return min(1.0, effective_rate * (weight / mean_weight))


def _merge_whitespace_tokens(left: str, right: str) -> str:
    def _score(value: str) -> tuple[int, int]:
        has_special = 1 if any(ch in value for ch in ("\n", "\r", "\t")) else 0
        return (has_special, len(value))

    if not left:
        return right
    if not right:
        return left

    left_score = _score(left)
    right_score = _score(right)
    return left if left_score >= right_score else right


def _remove_word_token(tokens: list[str], token: WordToken) -> None:
    replacement = f"{token.prefix}{token.suffix}"
    tokens[token.index] = replacement
    if replacement:
        return

    prev_index = token.index - 1 if token.index > 0 else None
    next_index = token.index + 1 if token.index + 1 < len(tokens) else None

    prev_whitespace = tokens[prev_index] if isinstance(prev_index, int) else None
    next_whitespace = tokens[next_index] if isinstance(next_index, int) else None

    if prev_index is not None and next_index is not None:
        if (
            prev_whitespace
            and prev_whitespace.isspace()
            and next_whitespace
            and next_whitespace.isspace()
        ):
            tokens[prev_index] = _merge_whitespace_tokens(prev_whitespace, next_whitespace)
            tokens[next_index] = ""
        elif next_whitespace and next_whitespace.isspace():
            tokens[next_index] = ""
        elif prev_whitespace and prev_whitespace.isspace():
            tokens[prev_index] = ""


def _compose_text_from_tokens(tokens: Sequence[str]) -> str:
    composed: list[str] = []
    for token in tokens:
        if not token:
            continue
        if token.isspace():
            if not composed:
                continue
            if composed[-1].isspace():
                composed[-1] = _merge_whitespace_tokens(composed[-1], token)
            else:
                composed.append(token)
            continue
        if composed and composed[-1].isspace() and token[0] in ".,;:":
            composed.pop()
        composed.append(token)

    while composed and composed[-1].isspace():
        composed.pop()
    return "".join(composed)


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
    weighted_tokens, mean_weight = _build_weighted_word_tokens(
        tokens,
        skip_first_word=True,
        unweighted=unweighted,
    )
    if not weighted_tokens:
        return text

    allowed_deletions = min(
        len(weighted_tokens),
        math.floor(len(weighted_tokens) * effective_rate),
    )
    if allowed_deletions <= 0:
        return text

    deletions = 0
    for candidate in weighted_tokens:
        if deletions >= allowed_deletions:
            break

        probability = _calculate_weighted_probability(
            effective_rate=effective_rate,
            weight=candidate.weight,
            mean_weight=mean_weight,
        )
        if rng.random() >= probability:
            continue

        _remove_word_token(tokens, candidate.token)

        deletions += 1

    return _compose_text_from_tokens(tokens)


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
    weighted_tokens, mean_weight = _build_weighted_word_tokens(
        tokens,
        skip_first_word=False,
        unweighted=unweighted,
    )

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return "".join(tokens)
    if not weighted_tokens:
        return "".join(tokens)

    for candidate in weighted_tokens:
        probability = _calculate_weighted_probability(
            effective_rate=effective_rate,
            weight=candidate.weight,
            mean_weight=mean_weight,
        )
        if rng.random() >= probability:
            continue

        token = candidate.token
        tokens[token.index] = f"{token.prefix}{token.core} {token.core}{token.suffix}"
    return _compose_text_from_tokens(tokens)


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
    word_tokens = [token for token in collect_word_tokens(tokens) if token.has_core]
    if len(word_tokens) < 2:
        return text

    clamped = max(0.0, min(rate, 1.0))
    if clamped <= 0.0:
        return text

    for cursor in range(0, len(word_tokens) - 1, 2):
        left = word_tokens[cursor]
        right = word_tokens[cursor + 1]

        should_swap = clamped >= 1.0 or rng.random() < clamped
        if not should_swap:
            continue

        tokens[left.index] = f"{left.prefix}{right.core}{left.suffix}"
        tokens[right.index] = f"{right.prefix}{left.core}{right.suffix}"

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
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Apply the configured Rushmore attack modes to ``text``."""
    if rng is None:
        rng = random.Random(seed)

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
    for mode in config.modes:
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
