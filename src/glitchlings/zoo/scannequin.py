import random
from typing import Any, cast

from glitchlings.constants import DEFAULT_SCANNEQUIN_RATE
from glitchlings.internal.rust_ffi import ocr_artifacts_rust, resolve_seed

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def ocr_artifacts(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce OCR-like artifacts into text.

    Uses the Rust implementation for performance and determinism.
    """
    if not text:
        return text

    effective_rate = DEFAULT_SCANNEQUIN_RATE if rate is None else rate

    clamped_rate = max(0.0, effective_rate)

    return ocr_artifacts_rust(text, clamped_rate, resolve_seed(seed, rng))


class Scannequin(Glitchling):
    """Glitchling that simulates OCR artifacts using common confusions."""

    flavor = "Isn't it weird how the word 'bed' looks like a bed?"

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_SCANNEQUIN_RATE if rate is None else rate
        super().__init__(
            name="Scannequin",
            corruption_function=ocr_artifacts,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LATE,
            seed=seed,
            rate=effective_rate,
            **kwargs,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        rate_value = self.kwargs.get("rate", DEFAULT_SCANNEQUIN_RATE)
        rate = DEFAULT_SCANNEQUIN_RATE if rate_value is None else float(rate_value)

        return cast(
            PipelineOperationPayload,
            {"type": "ocr", "rate": rate},
        )


scannequin = Scannequin()


__all__ = ["Scannequin", "scannequin", "ocr_artifacts"]
