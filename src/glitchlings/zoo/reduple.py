import random
from typing import Any, cast

from ._rate import resolve_rate
from ._rust_extensions import get_rust_operation
from ._text_utils import WordToken, collect_word_tokens, split_preserving_whitespace
from .core import AttackWave, Glitchling

# Load Rust-accelerated operation if available
_reduplicate_words_rust = get_rust_operation("reduplicate_words")


def _python_reduplicate_words(
    text: str,
    *,
    rate: float,
    rng: random.Random,
    unweighted: bool = False,
) -> str:
    """Randomly reduplicate words in the text.

    Parameters
    ----------
    - text: Input text.
    - rate: Max proportion of words to reduplicate (default 0.05).
    - rng: RNG used for sampling decisions.
    - unweighted: When True, sample words uniformly instead of length-weighted.

    Notes
    -----
    - Preserves spacing and punctuation by tokenizing with separators.
    - Deterministic when run with a fixed seed or via Gaggle.

    """
    tokens = split_preserving_whitespace(text)
    word_tokens = collect_word_tokens(tokens)

    weighted_tokens: list[tuple[int, float, WordToken]] = []
    for token in word_tokens:
        weight = 1.0 if unweighted else 1.0 / float(token.core_length)
        weighted_tokens.append((token.index, weight, token))

    if not weighted_tokens:
        return "".join(tokens)

    effective_rate = max(rate, 0.0)
    if effective_rate <= 0.0:
        return "".join(tokens)

    mean_weight = sum(weight for _, weight, _ in weighted_tokens) / len(weighted_tokens)

    for index, weight, token in weighted_tokens:
        if effective_rate >= 1.0:
            probability = 1.0
        else:
            if mean_weight <= 0.0:
                probability = effective_rate
            else:
                probability = min(1.0, effective_rate * (weight / mean_weight))
        if rng.random() >= probability:
            continue

        prefix, core, suffix = token.prefix, token.core, token.suffix
        tokens[index] = f"{prefix}{core} {core}{suffix}"
    return "".join(tokens)


def reduplicate_words(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    reduplication_rate: float | None = None,
    unweighted: bool = False,
) -> str:
    """Randomly reduplicate words in the text.

    Falls back to the Python implementation when the optional Rust
    extension is unavailable.
    """
    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=reduplication_rate,
        default=0.01,
        legacy_name="reduplication_rate",
    )

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)
    unweighted_flag = bool(unweighted)

    if _reduplicate_words_rust is not None:
        return cast(str, _reduplicate_words_rust(text, clamped_rate, unweighted_flag, rng))

    return _python_reduplicate_words(
        text,
        rate=clamped_rate,
        rng=rng,
        unweighted=unweighted_flag,
    )


class Reduple(Glitchling):
    """Glitchling that repeats words to simulate stuttering speech."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        reduplication_rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
    ) -> None:
        self._param_aliases = {"reduplication_rate": "rate"}
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=reduplication_rate,
            default=0.01,
            legacy_name="reduplication_rate",
        )
        super().__init__(
            name="Reduple",
            corruption_function=reduplicate_words,
            scope=AttackWave.WORD,
            seed=seed,
            rate=effective_rate,
            unweighted=unweighted,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None
        unweighted = bool(self.kwargs.get("unweighted", False))
        return {
            "type": "reduplicate",
            "reduplication_rate": float(rate),
            "unweighted": unweighted,
        }


reduple = Reduple()


__all__ = ["Reduple", "reduple"]
