import re
import random

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

    for i in range(0, len(tokens), 2):  # Every other token is a word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        # Only consider actual words for reduplication
        if rng.random() < rate:
            # Check if word has trailing punctuation
            match = re.match(r"^(\W*)(.*?)(\W*)$", word)
            if match:
                prefix, core, suffix = match.groups()
                # Reduplicate with a space: "word" -> "word word"
                tokens[i] = f"{prefix}{core} {core}{suffix}"
            else:
                tokens[i] = f"{word} {word}"
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


reduple = Reduple()


__all__ = ["Reduple", "reduple"]
