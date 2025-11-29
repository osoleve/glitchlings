import random
from typing import Any, cast

from glitchlings.constants import DEFAULT_REDACTYL_CHAR, DEFAULT_REDACTYL_RATE
from glitchlings.internal.rust_ffi import redact_words_rust, resolve_seed

from .core import AttackWave, Glitchling, PipelineOperationPayload

# Backwards compatibility alias
FULL_BLOCK = DEFAULT_REDACTYL_CHAR


def redact_words(
    text: str,
    replacement_char: str | None = DEFAULT_REDACTYL_CHAR,
    rate: float | None = None,
    merge_adjacent: bool | None = False,
    seed: int = 151,
    rng: random.Random | None = None,
    *,
    unweighted: bool = False,
) -> str:
    """Redact random words by replacing their characters."""
    effective_rate = DEFAULT_REDACTYL_RATE if rate is None else rate

    replacement = DEFAULT_REDACTYL_CHAR if replacement_char is None else str(replacement_char)
    merge = False if merge_adjacent is None else bool(merge_adjacent)

    clamped_rate = max(0.0, min(effective_rate, 1.0))
    unweighted_flag = bool(unweighted)

    return redact_words_rust(
        text,
        replacement,
        clamped_rate,
        merge,
        unweighted_flag,
        resolve_seed(seed, rng),
    )


class Redactyl(Glitchling):
    """Glitchling that redacts words with block characters."""

    flavor = "Some things are better left ████████."

    def __init__(
        self,
        *,
        replacement_char: str = DEFAULT_REDACTYL_CHAR,
        rate: float | None = None,
        merge_adjacent: bool = False,
        seed: int = 151,
        unweighted: bool = False,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_REDACTYL_RATE if rate is None else rate
        super().__init__(
            name="Redactyl",
            corruption_function=redact_words,
            scope=AttackWave.WORD,
            seed=seed,
            replacement_char=replacement_char,
            rate=effective_rate,
            merge_adjacent=merge_adjacent,
            unweighted=unweighted,
            **kwargs,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        replacement_char_value = self.kwargs.get("replacement_char", DEFAULT_REDACTYL_CHAR)
        rate_value = self.kwargs.get("rate", DEFAULT_REDACTYL_RATE)
        merge_value = self.kwargs.get("merge_adjacent", False)

        replacement_char = str(
            DEFAULT_REDACTYL_CHAR if replacement_char_value is None else replacement_char_value
        )
        rate = float(DEFAULT_REDACTYL_RATE if rate_value is None else rate_value)
        merge_adjacent = bool(merge_value)
        unweighted = bool(self.kwargs.get("unweighted", False))

        return cast(
            PipelineOperationPayload,
            {
                "type": "redact",
                "replacement_char": replacement_char,
                "rate": rate,
                "merge_adjacent": merge_adjacent,
                "unweighted": unweighted,
            },
        )


redactyl = Redactyl()


__all__ = ["Redactyl", "redactyl", "redact_words"]
