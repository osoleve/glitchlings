import random
import re
from .core import Glitchling, AttackWave


def delete_random_words(
    text: str,
    max_deletion_rate: float = 0.01,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Delete random words from the input text.

    Parameters
    - text: The input text.
    - max_deletion_rate: The maximum proportion of words to delete (default 0.01).
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.
    """
    if rng is None:
        rng = random.Random(seed)

    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators

    for i in range(
        2, len(tokens), 2
    ):  # Every other token is a word, but skip the first word
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        # Only consider actual words for deletion
        if rng.random() < max_deletion_rate:
            # Check if word has trailing punctuation
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


rushmore = Glitchling("rushmore", delete_random_words, scope=AttackWave.WORD)
