import math
import random
import re

from .core import Glitchling, AttackWave

try:
    from glitchlings._zoo_rust import delete_random_words as _delete_random_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _delete_random_words_rust = None


def _python_delete_random_words(
    text: str,
    *,
    max_deletion_rate: float,
    rng: random.Random,
) -> str:
    """Delete random words from the input text.

    Parameters
    - text: The input text.
    - max_deletion_rate: The maximum proportion of words to delete (default 0.01).
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.
    """
    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators

    candidate_indices: list[int] = []
    for i in range(2, len(tokens), 2):  # Every other token is a word, skip the first word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        candidate_indices.append(i)

    max_deletions = min(
        len(candidate_indices),
        math.floor(len(candidate_indices) * max_deletion_rate),
    )
    if max_deletions <= 0:
        indices_to_delete: list[int] = []
    else:
        indices_to_delete = rng.sample(candidate_indices, max_deletions)

    for i in indices_to_delete:
        word = tokens[i]
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, _, suffix = match.groups()
            tokens[i] = f"{prefix.strip()}{suffix.strip()}"
        else:
            tokens[i] = ""

    text = "".join(tokens)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text


def delete_random_words(
    text: str,
    max_deletion_rate: float = 0.01,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Delete random words from the input text.

    Uses the optional Rust implementation when available.
    """

    if rng is None:
        rng = random.Random(seed)

    if _delete_random_words_rust is not None:
        return _delete_random_words_rust(text, max_deletion_rate, rng)

    return _python_delete_random_words(
        text,
        max_deletion_rate=max_deletion_rate,
        rng=rng,
    )


class Rushmore(Glitchling):
    """Glitchling that deletes words to simulate missing information."""

    def __init__(
        self,
        *,
        max_deletion_rate: float = 0.01,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            name="Rushmore",
            corruption_function=delete_random_words,
            scope=AttackWave.WORD,
            seed=seed,
            max_deletion_rate=max_deletion_rate,
        )


rushmore = Rushmore()


__all__ = ["Rushmore", "rushmore"]
