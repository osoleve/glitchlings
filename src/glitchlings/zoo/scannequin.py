import random
import re
from typing import Any, cast

from ._ocr_confusions import load_confusion_table
from ._rate import resolve_rate
from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Glitchling

# Load Rust-accelerated operation if available
_ocr_artifacts_rust = get_rust_operation("ocr_artifacts")


def _python_ocr_artifacts(
    text: str,
    *,
    rate: float,
    rng: random.Random,
) -> str:
    """Introduce OCR-like artifacts into text.

    Parameters
    ----------
    - text: Input text to corrupt.
    - rate: Max proportion of eligible confusion matches to replace (default 0.02).
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.

    Notes
    -----
    - Uses a curated set of common OCR confusions (rn↔m, cl↔d, O↔0, l/I/1, etc.).
    - Collects all non-overlapping candidate spans in reading order, then samples
      a subset deterministically with the provided RNG.
    - Replacements can change length (e.g., m→rn), so edits are applied from left
      to right using precomputed spans to avoid index drift.

    """
    if not text:
        return text

    # Keep the confusion definitions in a shared data file so both the Python
    # and Rust implementations stay in sync.
    confusion_table = load_confusion_table()

    # Build candidate matches as (start, end, choices)
    candidates: list[tuple[int, int, list[str]]] = []

    # To avoid double-counting overlapping patterns (like 'l' inside 'li'),
    # we will scan longer patterns first by sorting by len(src) desc.
    for src, choices in sorted(confusion_table, key=lambda p: -len(p[0])):
        pattern = re.escape(src)
        for m in re.finditer(pattern, text):
            start, end = m.span()
            candidates.append((start, end, choices))

    if not candidates:
        return text

    # Decide how many to replace
    k = int(len(candidates) * rate)
    if k <= 0:
        return text

    # Shuffle deterministically and select non-overlapping k spans
    rng.shuffle(candidates)
    chosen: list[tuple[int, int, str]] = []
    occupied: list[tuple[int, int]] = []

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return not (a[1] <= b[0] or b[1] <= a[0])

    for start, end, choices in candidates:
        if len(chosen) >= k:
            break
        span = (start, end)
        if any(overlaps(span, occ) for occ in occupied):
            continue
        replacement = rng.choice(choices)
        chosen.append((start, end, replacement))
        occupied.append(span)

    if not chosen:
        return text

    # Apply edits from left to right
    chosen.sort(key=lambda t: t[0])
    out_parts = []
    cursor = 0
    for start, end, rep in chosen:
        if cursor < start:
            out_parts.append(text[cursor:start])
        out_parts.append(rep)
        cursor = end
    if cursor < len(text):
        out_parts.append(text[cursor:])

    return "".join(out_parts)


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

    effective_rate = resolve_rate(rate=rate, default=0.02)

    if rng is None:
        rng = random.Random(seed)

    clamped_rate = max(0.0, effective_rate)

    if _ocr_artifacts_rust is not None:
        return cast(str, _ocr_artifacts_rust(text, clamped_rate, rng))

    return _python_ocr_artifacts(text, rate=clamped_rate, rng=rng)


class Scannequin(Glitchling):
    """Glitchling that simulates OCR artifacts using common confusions."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
    ) -> None:
        effective_rate = resolve_rate(rate=rate, default=0.02)
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


__all__ = ["Scannequin", "scannequin"]
