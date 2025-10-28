import math
import random
import re
from typing import Any, cast

from ._rate import resolve_rate
from ._rust_extensions import get_rust_operation
from ._text_utils import WordToken, collect_word_tokens, split_preserving_whitespace
from .core import AttackWave, Glitchling

# Load Rust-accelerated operation if available
_delete_random_words_rust = get_rust_operation("delete_random_words")


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
    """Delete random words from the input text.

    Uses the optional Rust implementation when available.
    """
    effective_rate = resolve_rate(rate=rate, default=0.01)

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


class Rushmore(Glitchling):
    """Glitchling that deletes words to simulate missing information."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
    ) -> None:
        effective_rate = resolve_rate(rate=rate, default=0.01)
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
            return None
        unweighted = bool(self.kwargs.get("unweighted", False))
        return {
            "type": "delete",
            "max_deletion_rate": float(rate),
            "unweighted": unweighted,
        }


rushmore = Rushmore()


__all__ = ["Rushmore", "rushmore"]
