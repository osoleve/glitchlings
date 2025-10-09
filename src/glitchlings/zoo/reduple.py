import re
import random
from typing import Any

from .core import Glitchling, AttackWave
from ._rate import resolve_rate

try:
    from glitchlings._zoo_rust import reduplicate_words as _reduplicate_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _reduplicate_words_rust = None


def _python_reduplicate_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    """Randomly reduplicate words in the text.

    Parameters
    - text: Input text.
    - rate: Max proportion of words to reduplicate (default 0.05).
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.

    Notes
    - Preserves spacing and punctuation by tokenizing with separators.
    - Deterministic when run with a fixed seed or via Gaggle.
    """
    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators

    candidate_weights = []
    for i in range(0, len(tokens), 2):  # Every other token is a word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        core = match.group(2) if match else word
        core_length = len(core) if core else len(word)
        if core_length <= 0:
            core_length = len(word.strip()) or len(word)
        if core_length <= 0:
            core_length = 1
        weight = 1.0 / core_length
        candidate_weights.append((i, weight))

    if not candidate_weights:
        return "".join(tokens)

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return "".join(tokens)

    mean_weight = sum(weight for _, weight in candidate_weights) / len(candidate_weights)

    for index, weight in candidate_weights:
        if effective_rate >= 1.0:
            probability = 1.0
        else:
            probability = min(1.0, effective_rate * (weight / mean_weight))
        if rng.random() >= probability:
            continue

        word = tokens[index]
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, core, suffix = match.groups()
            # Reduplicate with a space: "word" -> "word word"
            tokens[index] = f"{prefix}{core} {core}{suffix}"
        else:
            tokens[index] = f"{word} {word}"
    return "".join(tokens)


def reduplicate_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    reduplication_rate: float | None = None,
) -> str:
    """Randomly reduplicate words in the text.

    Falls back to the Python implementation when the optional Rust
    extension is unavailable.
    """

    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=reduplication_rate,
        default=0.05,
        legacy_name="reduplication_rate",
    )

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)

    if _reduplicate_words_rust is not None:
        return _reduplicate_words_rust(text, clamped_rate, rng)

    return _python_reduplicate_words(
        text,
        rate=clamped_rate,
        rng=rng,
    )


class Reduple(Glitchling):
    """Glitchling that repeats words to simulate stuttering speech."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        reduplication_rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        self._param_aliases = {"reduplication_rate": "rate"}
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=reduplication_rate,
            default=0.05,
            legacy_name="reduplication_rate",
        )
        super().__init__(
            name="Reduple",
            corruption_function=reduplicate_words,
            scope=AttackWave.WORD,
            seed=seed,
            rate=effective_rate,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None
        return {"type": "reduplicate", "reduplication_rate": float(rate)}



reduple = Reduple()


__all__ = ["Reduple", "reduple"]
