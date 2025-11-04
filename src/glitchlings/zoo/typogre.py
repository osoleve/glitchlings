from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import cast

from ..util import KEYNEIGHBORS
from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

_fatfinger_rust = get_rust_operation("fatfinger")

def fatfinger(
    text: str,
    rate: float | None = None,
    keyboard: str = "CURATOR_QWERTY",
    layout: Mapping[str, Sequence[str]] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce character-level "fat finger" edits with a Rust fast path."""
    effective_rate = 0.02 if rate is None else rate

    if rng is None:
        rng = random.Random(seed)
    if not text:
        return ""

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    layout_mapping = layout if layout is not None else getattr(KEYNEIGHBORS, keyboard)

    return cast(
            str,
            _fatfinger_rust(
                text,
                max_change_rate=clamped_rate,
                layout=layout_mapping,
                rng=rng,
            ),
        )


class Typogre(Glitchling):
    """Glitchling that introduces deterministic keyboard-typing errors."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        keyboard: str = "CURATOR_QWERTY",
        seed: int | None = None,
    ) -> None:
        effective_rate = 0.02 if rate is None else rate
        super().__init__(
            name="Typogre",
            corruption_function=fatfinger,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.EARLY,
            seed=seed,
            rate=effective_rate,
            keyboard=keyboard,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        rate_value = self.kwargs.get("rate")
        rate = 0.02 if rate_value is None else float(rate_value)
        keyboard = self.kwargs.get("keyboard", "CURATOR_QWERTY")
        layout = getattr(KEYNEIGHBORS, str(keyboard), None)
        if layout is None:
            message = f"Unknown keyboard layout '{keyboard}' for Typogre pipeline"
            raise RuntimeError(message)

        serialized_layout = {key: list(value) for key, value in layout.items()}

        return cast(
            PipelineOperationPayload,
            {
                "type": "typo",
                "rate": float(rate),
                "keyboard": str(keyboard),
                "layout": serialized_layout,
            },
        )


typogre = Typogre()


__all__ = ["Typogre", "typogre", "fatfinger"]
