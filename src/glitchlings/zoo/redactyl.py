import re
import random

from .core import Glitchling, AttackWave

FULL_BLOCK = "█"


try:
    from glitchlings._zoo_rust import redact_words as _redact_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _redact_words_rust = None


def _python_redact_words(
    text: str,
    *,
    replacement_char: str,
    redaction_rate: float,
    merge_adjacent: bool,
    rng: random.Random,
) -> str:
    """Redact random words by replacing their characters.

    Parameters
    - text: Input text.
    - replacement_char: The character to use for redaction (default FULL_BLOCK).
    - redaction_rate: Max proportion of words to redact (default 0.05).
    - merge_adjacent: If True, merges adjacent redactions across intervening non-word chars.
    - seed: Seed used if `rng` not provided (default 151).
    - rng: Optional RNG; overrides seed.
    """
    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)
    word_indices = [i for i, token in enumerate(tokens) if i % 2 == 0 and token.strip()]
    if not word_indices:
        raise ValueError("Cannot redact words because the input text contains no redactable words.")
    num_to_redact = max(1, int(len(word_indices) * redaction_rate))

    # Sample from the indices of actual words
    indices_to_redact = rng.sample(word_indices, k=num_to_redact)
    indices_to_redact.sort()

    for i in indices_to_redact:
        if i >= len(tokens):
            break

        word = tokens[i]
        if not word or word.isspace():  # Skip empty or whitespace
            continue

        # Check if word has trailing punctuation
        match = re.match(r"^(\W*)(.*?)(\W*)$", word)
        if match:
            prefix, core, suffix = match.groups()
            tokens[i] = f"{prefix}{replacement_char * len(core)}{suffix}"
        else:
            tokens[i] = f"{replacement_char * len(word)}"

    text = "".join(tokens)

    if merge_adjacent:
        text = re.sub(
            rf"{replacement_char}\W+{replacement_char}",
            lambda m: replacement_char * (len(m.group(0)) - 1),
            text,
        )

    return text


def redact_words(
    text: str,
    replacement_char: str = FULL_BLOCK,
    redaction_rate: float = 0.05,
    merge_adjacent: bool = False,
    seed: int = 151,
    rng: random.Random | None = None,
) -> str:
    """Redact random words by replacing their characters."""

    if rng is None:
        rng = random.Random(seed)

    use_rust = _redact_words_rust is not None and isinstance(merge_adjacent, bool)

    if use_rust:
        return _redact_words_rust(
            text,
            replacement_char,
            redaction_rate,
            merge_adjacent,
            rng,
        )

    return _python_redact_words(
        text,
        replacement_char=replacement_char,
        redaction_rate=redaction_rate,
        merge_adjacent=merge_adjacent,
        rng=rng,
    )


class Redactyl(Glitchling):
    """Glitchling that redacts words with block characters."""

    def __init__(
        self,
        *,
        replacement_char: str = FULL_BLOCK,
        redaction_rate: float = 0.05,
        merge_adjacent: bool = False,
        seed: int = 151,
    ) -> None:
        super().__init__(
            name="Redactyl",
            corruption_function=redact_words,
            scope=AttackWave.WORD,
            seed=seed,
            replacement_char=replacement_char,
            redaction_rate=redaction_rate,
            merge_adjacent=merge_adjacent,
        )


redactyl = Redactyl()


__all__ = ["Redactyl", "redactyl"]
