import math
import random
import re

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

    if rate <= 0.0:
        return text

    tokens = re.split(r"(\s+)", text)  # Split but keep separators for later rejoin

    candidate_indices: list[int] = []
    for i in range(2, len(tokens), 2):  # Every other token is a word, skip the first word
        word = tokens[i]
        if not word or word.isspace():
            continue

        candidate_indices.append(i)

    allowed_deletions = min(
        len(candidate_indices), math.floor(len(candidate_indices) * rate)
    )
    if allowed_deletions <= 0:
        return text

    deletions = 0
    for i in candidate_indices:
        if rng.random() < rate:
            word = tokens[i]
            match = re.match(r"^(\W*)(.*?)(\W*)$", word)
            if match:
                prefix, _, suffix = match.groups()
                tokens[i] = f"{prefix.strip()}{suffix.strip()}"
            else:
                tokens[i] = ""

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


rushmore = Rushmore()


__all__ = ["Rushmore", "rushmore"]
