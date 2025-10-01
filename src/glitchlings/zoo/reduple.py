import re
import random

from .core import Glitchling, AttackWave

try:
    from glitchlings._zoo_rust import reduplicate_words as _reduplicate_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _reduplicate_words_rust = None


def _python_reduplicate_words(
    text: str,
    *,
    reduplication_rate: float,
    rng: random.Random,
) -> str:
    """Randomly reduplicate words in the text.

    Parameters
    - text: Input text.
    - reduplication_rate: Max proportion of words to reduplicate (default 0.05).
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
        if rng.random() < reduplication_rate:
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
    reduplication_rate: float = 0.05,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Randomly reduplicate words in the text.

    Falls back to the Python implementation when the optional Rust
    extension is unavailable.
    """

    if rng is None:
        rng = random.Random(seed)

    if _reduplicate_words_rust is not None:
        return _reduplicate_words_rust(text, reduplication_rate, rng)

    return _python_reduplicate_words(
        text,
        reduplication_rate=reduplication_rate,
        rng=rng,
    )


class Reduple(Glitchling):
    """Glitchling that repeats words to simulate stuttering speech."""

    def __init__(
        self,
        *,
        reduplication_rate: float = 0.05,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            name="Reduple",
            corruption_function=reduplicate_words,
            scope=AttackWave.WORD,
            seed=seed,
            reduplication_rate=reduplication_rate,
        )


reduple = Reduple()


__all__ = ["Reduple", "reduple"]
