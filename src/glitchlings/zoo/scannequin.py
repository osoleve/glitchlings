import random
from typing import cast

from glitchlings.internal.rust import get_rust_operation, resolve_seed

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

# Load the mandatory Rust implementation
_ocr_artifacts_rust = get_rust_operation("ocr_artifacts")


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

    effective_rate = 0.02 if rate is None else rate

    clamped_rate = max(0.0, effective_rate)

    return cast(str, _ocr_artifacts_rust(text, clamped_rate, resolve_seed(seed, rng)))


class Scannequin(Glitchling):
    """Glitchling that simulates OCR artifacts using common confusions."""

    flavor = "Isn't it weird how the word 'bed' looks like a bed?"

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        effective_rate = 0.02 if rate is None else rate
        super().__init__(
            name="Scannequin",
            corruption_function=ocr_artifacts,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LATE,
            seed=seed,
            rate=effective_rate,
        )

    def pipeline_operation(self) -> PipelineOperationPayload | None:
        rate_value = self.kwargs.get("rate")
        if rate_value is None:
            return None

        return cast(
            PipelineOperationPayload,
            {"type": "ocr", "rate": float(rate_value)},
        )


scannequin = Scannequin()


__all__ = ["Scannequin", "scannequin", "ocr_artifacts"]
