import random
from typing import cast

from ._rust_extensions import get_rust_operation
from .core import AttackWave, Glitchling, PipelineOperationPayload

FULL_BLOCK = "█"

# Load the mandatory Rust implementation
_redact_words_rust = get_rust_operation("redact_words")

def redact_words(
    text: str,
    replacement_char: str = FULL_BLOCK,
    rate: float | None = None,
    merge_adjacent: bool = False,
    seed: int = 151,
    rng: random.Random | None = None,
    *,
    unweighted: bool = False,
) -> str:
    """Redact random words by replacing their characters."""
    effective_rate = 0.025 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, min(effective_rate, 1.0))
    unweighted_flag = bool(unweighted)

    return cast(
        str,
        _redact_words_rust(
            text,
            replacement_char,
            clamped_rate,
            merge_adjacent,
            unweighted_flag,
            rng,
        ),
    )


class Redactyl(Glitchling):
    """Glitchling that redacts words with block characters."""

    def __init__(
        self,
        *,
        replacement_char: str = FULL_BLOCK,
        rate: float | None = None,
        merge_adjacent: bool = False,
        seed: int = 151,
        unweighted: bool = False,
    ) -> None:
        effective_rate = 0.025 if rate is None else rate
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

    def pipeline_operation(self) -> PipelineOperationPayload | None:
        replacement_char_value = self.kwargs.get("replacement_char")
        rate_value = self.kwargs.get("rate")
        merge_value = self.kwargs.get("merge_adjacent")

        if (
            replacement_char_value is None
            or rate_value is None
            or merge_value is None
        ):
            return None

        replacement_char = str(replacement_char_value)
        rate = float(rate_value)
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
