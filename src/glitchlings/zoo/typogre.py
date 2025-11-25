from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import cast

from glitchlings.constants import DEFAULT_TYPOGRE_KEYBOARD, DEFAULT_TYPOGRE_RATE
from glitchlings.internal.rust_ffi import fatfinger_rust, resolve_seed

from ..util import KEYNEIGHBORS
from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def fatfinger(
    text: str,
    rate: float | None = None,
    keyboard: str = DEFAULT_TYPOGRE_KEYBOARD,
    layout: Mapping[str, Sequence[str]] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Introduce character-level "fat finger" edits with a Rust fast path."""
    effective_rate = DEFAULT_TYPOGRE_RATE if rate is None else rate

    if not text:
        return ""

    clamped_rate = max(0.0, effective_rate)
    if clamped_rate == 0.0:
        return text

    layout_mapping = layout if layout is not None else getattr(KEYNEIGHBORS, keyboard)

    return fatfinger_rust(
        text,
        clamped_rate,
        layout_mapping,
        resolve_seed(seed, rng),
    )


class Typogre(Glitchling):
    """Glitchling that introduces deterministic keyboard-typing errors."""

    flavor = "What a nice word, would be a shame if something happened to it..."

    def __init__(
        self,
        *,
        rate: float | None = None,
        keyboard: str = DEFAULT_TYPOGRE_KEYBOARD,
        seed: int | None = None,
    ) -> None:
        effective_rate = DEFAULT_TYPOGRE_RATE if rate is None else rate
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
        rate = DEFAULT_TYPOGRE_RATE if rate_value is None else float(rate_value)
        keyboard = self.kwargs.get("keyboard", DEFAULT_TYPOGRE_KEYBOARD)
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
