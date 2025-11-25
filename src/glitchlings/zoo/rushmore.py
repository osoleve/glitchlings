from __future__ import annotations

import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, cast

from glitchlings.constants import RUSHMORE_DEFAULT_RATES
from glitchlings.internal.rust import get_rust_operation, resolve_seed

from ._text_utils import WordToken
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
    "repeat": RushmoreMode.DUPLICATE,
    "swap": RushmoreMode.SWAP,
    "adjacent": RushmoreMode.SWAP,
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

    def to_pipeline_descriptor(self) -> dict[str, Any]:
        if not self.modes:
            raise RuntimeError("Rushmore configuration is missing attack modes")

        if len(self.modes) == 1:
            mode = self.modes[0]
            rate = self.rates.get(mode)
            if rate is None:
                message = f"Rushmore mode {mode!r} is missing a configured rate"
                raise RuntimeError(message)
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
            message = f"Rushmore mode {mode!r} is not serialisable"
            raise RuntimeError(message)

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
        baseline = RUSHMORE_DEFAULT_RATES[mode.value]

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


# Load the mandatory Rust operations
_delete_random_words_rust = get_rust_operation("delete_random_words")
_reduplicate_words_rust = get_rust_operation("reduplicate_words")
_swap_adjacent_words_rust = get_rust_operation("swap_adjacent_words")


def delete_random_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    unweighted: bool = False,
) -> str:
    """Delete random words from the input text."""
    effective_rate = 0.01 if rate is None else rate

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    seed_value = resolve_seed(seed, rng)
    return cast(str, _delete_random_words_rust(text, clamped_rate, unweighted_flag, seed_value))


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

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    seed_value = resolve_seed(seed, rng)
    return cast(str, _reduplicate_words_rust(text, clamped_rate, unweighted_flag, seed_value))


def swap_adjacent_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Swap adjacent word cores while preserving spacing and punctuation."""
    effective_rate = 0.5 if rate is None else rate
    clamped_rate = max(0.0, min(effective_rate, 1.0))

    seed_value = resolve_seed(seed, rng)
    return cast(str, _swap_adjacent_words_rust(text, clamped_rate, seed_value))


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

    mode_rng = rng
    if mode_rng is None and seed is not None:
        mode_rng = random.Random(resolve_seed(seed, None))

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
                rng=mode_rng,
                unweighted=config.delete_unweighted,
            )
        elif mode is RushmoreMode.DUPLICATE:
            result = reduplicate_words(
                result,
                rate=rate_value,
                rng=mode_rng,
                unweighted=config.duplicate_unweighted,
            )
        else:
            result = swap_adjacent_words(
                result,
                rate=rate_value,
                rng=mode_rng,
            )

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
    "reduplicate_words",
    "swap_adjacent_words",
]
