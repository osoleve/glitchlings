import re
import random
from .core import Glitchling, AttackWave


def reduplicate_words(
    text: str,
    reduplication_rate: float = 0.05,
    seed: int | None = None,
    rng: random.Random | None = None,
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
    if rng is None:
        rng = random.Random(seed)

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
