import math
import random
import re
from typing import Any

from ._rate import resolve_rate
from ._text_utils import (
    split_preserving_whitespace,
    split_token_edges,
    token_core_length,
)
from .core import AttackWave, Glitchling

try:
    from glitchlings._zoo_rust import delete_random_words as _delete_random_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _delete_random_words_rust = None


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

    candidate_data: list[tuple[int, float]] = []
    for i in range(2, len(tokens), 2):
        word = tokens[i]
        if not word or word.isspace():
            continue

        length = token_core_length(word)
        weight = 1.0 if unweighted else 1.0 / length
        candidate_data.append((i, weight))

    if not candidate_data:
        return text

    allowed_deletions = min(
        len(candidate_data), math.floor(len(candidate_data) * effective_rate)
    )
    if allowed_deletions <= 0:
        return text

    mean_weight = sum(weight for _, weight in candidate_data) / len(candidate_data)

    deletions = 0
    for index, weight in candidate_data:
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

        word = tokens[index]
        prefix, _, suffix = split_token_edges(word)
        tokens[index] = f"{prefix.strip()}{suffix.strip()}"

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
    *,
    max_deletion_rate: float | None = None,
    unweighted: bool = False,
) -> str:
    """Delete random words from the input text.

    Uses the optional Rust implementation when available.
    """

    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=max_deletion_rate,
        default=0.01,
        legacy_name="max_deletion_rate",
    )

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    if _delete_random_words_rust is not None:
        return _delete_random_words_rust(text, clamped_rate, unweighted_flag, rng)

    return _python_delete_random_words(
        text,
        rate=clamped_rate,
        rng=rng,
        unweighted=unweighted_flag,
    )


class Rushmore(Glitchling):
    """Glitchling that deletes words to simulate missing information."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        max_deletion_rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
    ) -> None:
        self._param_aliases = {"max_deletion_rate": "rate"}
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=max_deletion_rate,
            default=0.01,
            legacy_name="max_deletion_rate",
        )
        super().__init__(
            name="Rushmore",
            corruption_function=delete_random_words,
            scope=AttackWave.WORD,
            seed=seed,
            rate=effective_rate,
            unweighted=unweighted,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            rate = self.kwargs.get("max_deletion_rate")
        if rate is None:
            return None
        unweighted = bool(self.kwargs.get("unweighted", False))
        return {
            "type": "delete",
            "max_deletion_rate": float(rate),
            "unweighted": unweighted,
        }


rushmore = Rushmore()


__all__ = ["Rushmore", "rushmore"]
