import re
import random
from typing import Any

from ._rate import resolve_rate
from ._sampling import weighted_sample_without_replacement
from ._text_utils import (
    WordToken,
    collect_word_tokens,
    split_preserving_whitespace,
)
from .core import AttackWave, Glitchling

FULL_BLOCK = "█"


try:
    from glitchlings._zoo_rust import redact_words as _redact_words_rust
except ImportError:  # pragma: no cover - compiled extension not present
    _redact_words_rust = None


def _python_redact_words(
    text: str,
    *,
    replacement_char: str,
    rate: float,
    merge_adjacent: bool,
    rng: random.Random,
    unweighted: bool = False,
) -> str:
    """Redact random words by replacing their characters.

    Parameters
    - text: Input text.
    - replacement_char: The character to use for redaction (default FULL_BLOCK).
    - rate: Max proportion of words to redact (default 0.05).
    - merge_adjacent: If True, merges adjacent redactions across intervening non-word chars.
    - rng: RNG used for sampling decisions.
    - unweighted: When True, sample words uniformly instead of by length.
    """
    tokens = split_preserving_whitespace(text)
    word_tokens = collect_word_tokens(tokens)
    if not word_tokens:
        raise ValueError(
            "Cannot redact words because the input text contains no redactable words."
        )

    population = [token.index for token in word_tokens]
    weights = [
        1.0 if unweighted else float(token.core_length) for token in word_tokens
    ]

    clamped_rate = max(0.0, min(rate, 1.0))
    raw_quota = len(population) * clamped_rate
    num_to_redact = int(raw_quota)
    if clamped_rate > 0.0:
        num_to_redact = max(1, num_to_redact)
    num_to_redact = min(num_to_redact, len(population))
    if num_to_redact <= 0:
        return "".join(tokens)

    indices_to_redact = weighted_sample_without_replacement(
        population,
        weights,
        k=num_to_redact,
        rng=rng,
    )
    indices_to_redact.sort()

    token_by_index: dict[int, WordToken] = {token.index: token for token in word_tokens}

    for i in indices_to_redact:
        if i >= len(tokens):
            break

        token = token_by_index.get(i)
        if token is None:
            continue

        prefix, core, suffix = token.prefix, token.core, token.suffix
        tokens[i] = f"{prefix}{replacement_char * len(core)}{suffix}"

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
    rate: float | None = None,
    merge_adjacent: bool = False,
    seed: int = 151,
    rng: random.Random | None = None,
    *,
    redaction_rate: float | None = None,
    unweighted: bool = False,
) -> str:
    """Redact random words by replacing their characters."""

    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=redaction_rate,
        default=0.025,
        legacy_name="redaction_rate",
    )

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, min(effective_rate, 1.0))
    unweighted_flag = bool(unweighted)

    use_rust = _redact_words_rust is not None and isinstance(merge_adjacent, bool)

    if use_rust:
        return _redact_words_rust(
            text,
            replacement_char,
            clamped_rate,
            merge_adjacent,
            unweighted_flag,
            rng,
        )

    return _python_redact_words(
        text,
        replacement_char=replacement_char,
        rate=clamped_rate,
        merge_adjacent=merge_adjacent,
        rng=rng,
        unweighted=unweighted_flag,
    )


class Redactyl(Glitchling):
    """Glitchling that redacts words with block characters."""

    def __init__(
        self,
        *,
        replacement_char: str = FULL_BLOCK,
        rate: float | None = None,
        redaction_rate: float | None = None,
        merge_adjacent: bool = False,
        seed: int = 151,
        unweighted: bool = False,
    ) -> None:
        self._param_aliases = {"redaction_rate": "rate"}
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=redaction_rate,
            default=0.025,
            legacy_name="redaction_rate",
        )
        super().__init__(
            name="Redactyl",
            corruption_function=redact_words,
            scope=AttackWave.WORD,
            seed=seed,
            replacement_char=replacement_char,
            rate=effective_rate,
            merge_adjacent=merge_adjacent,
            unweighted=unweighted,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        replacement_char = self.kwargs.get("replacement_char")
        rate = self.kwargs.get("rate")
        merge_adjacent = self.kwargs.get("merge_adjacent")
        if replacement_char is None or rate is None or merge_adjacent is None:
            return None
        unweighted = bool(self.kwargs.get("unweighted", False))
        return {
            "type": "redact",
            "replacement_char": str(replacement_char),
            "redaction_rate": float(rate),
            "merge_adjacent": bool(merge_adjacent),
            "unweighted": unweighted,
        }


redactyl = Redactyl()


__all__ = ["Redactyl", "redactyl"]
