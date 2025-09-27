import re
import random
from .core import Glitchling, AttackWave

FULL_BLOCK = "█"


def redact_words(
    text: str,
    replacement_char: str = FULL_BLOCK,
    redaction_rate: float = 0.05,
    merge_adjacent: bool = False,
    seed: int = 151,
    rng: random.Random | None = None,
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
    if rng is None:
        rng = random.Random(seed)

    # Preserve exact spacing and punctuation by using regex
    tokens = re.split(r"(\s+)", text)  # Split but keep separators
    num_tokens = len(tokens)
    to_redact = rng.sample(
        range(num_tokens), k=max(1, int(num_tokens * redaction_rate))
    )
    to_redact.sort()
    to_redact = [i * 2 for i in to_redact]  # Adjust for separators

    for i in to_redact:
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


redactyl = Glitchling(
    name="Redactyl",
    corruption_function=redact_words,
    replacement_char=FULL_BLOCK,
    redaction_rate=0.05,
    scope=AttackWave.WORD,
    seed=151,
)
