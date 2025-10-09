import math
import random
import re
from typing import Any

from .core import Glitchling, AttackWave
from ._rate import resolve_rate

try:
    from glitchlings._zoo_rust import delete_random_words as _delete_random_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _delete_random_words_rust = None


def _python_delete_random_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    """Delete random words from the input text while preserving whitespace."""

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return text

    tokens = re.split(r"(\s+)", text)  # Split but keep separators for later rejoin

    candidate_data = []
    for i in range(2, len(tokens), 2):  # Every other token is a word, skip the first word
        word = tokens[i]
        if not word or word.isspace():
            continue

        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        core = match.group(2) if match else word
        core_length = len(core) if core else len(word)
        if core_length <= 0:
            core_length = len(word.strip()) or len(word)
        if core_length <= 0:
            core_length = 1
        weight = 1.0 / core_length
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
        if effective_rate >= 1.0:
            probability = 1.0
        else:
            probability = min(1.0, effective_rate * (weight / mean_weight))
        if rng.random() >= probability:
            continue

        word = tokens[index]
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, _, suffix = match.groups()
            tokens[index] = f"{prefix.strip()}{suffix.strip()}"
        else:
            tokens[index] = ""

        deletions += 1
        if deletions >= allowed_deletions:
            break

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

    if _delete_random_words_rust is not None:
        return _delete_random_words_rust(text, clamped_rate, rng)

    return _python_delete_random_words(
        text,
        rate=clamped_rate,
        rng=rng,
    )


class Rushmore(Glitchling):
    """Glitchling that deletes words to simulate missing information."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        max_deletion_rate: float | None = None,
        seed: int | None = None,
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
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            rate = self.kwargs.get("max_deletion_rate")
        if rate is None:
            return None
        return {"type": "delete", "max_deletion_rate": float(rate)}


rushmore = Rushmore()


__all__ = ["Rushmore", "rushmore"]
