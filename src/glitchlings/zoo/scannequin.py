import random
import re
from typing import Any, cast

from ._ocr_confusions import load_confusion_table
from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Glitchling

# Load Rust-accelerated operation if available
_ocr_artifacts_rust = get_rust_operation("ocr_artifacts")

def ocr_artifacts(
    text: str,
    rate: float | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce OCR-like artifacts into text.

    Prefers the Rust implementation when available.
    """
    if not text:
        return text

    effective_rate = 0.02 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)

    return cast(str, _ocr_artifacts_rust(text, clamped_rate, rng))




class Scannequin(Glitchling):
    """Glitchling that simulates OCR artifacts using common confusions."""

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

    def pipeline_operation(self) -> dict[str, Any] | None:
        rate = self.kwargs.get("rate")
        if rate is None:
            return None
        return {"type": "ocr", "rate": float(rate)}


scannequin = Scannequin()


__all__ = ["Scannequin", "scannequin", "ocr_artifacts"]
