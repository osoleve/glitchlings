from __future__ import annotations

import random
from typing import cast

from glitchlings.internal.rust_ffi import resolve_seed, swap_colors_rust

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def swap_colors(
    text: str,
    *,
    mode: str = "literal",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Delegate colour swapping to the compiled Rust implementation."""

    normalized_mode = mode or "literal"
    resolved_seed: int | None
    if normalized_mode.lower() == "drift":
        resolved_seed = resolve_seed(seed, rng)
    else:
        resolved_seed = None

    return swap_colors_rust(text, normalized_mode, resolved_seed)


class Spectroll(Glitchling):
    """Glitchling that remaps colour terms via the Rust backend."""

    flavor = "The colors, Duke, the colors!</br>*I'm colorblind, kid.*"

    def __init__(
        self,
        *,
        mode: str = "literal",
        seed: int | None = None,
    ) -> None:
        normalized_mode = (mode or "literal").lower()
        super().__init__(
            name="Spectroll",
            corruption_function=swap_colors,
            scope=AttackWave.WORD,
            order=AttackOrder.NORMAL,
            seed=seed,
            mode=normalized_mode,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        mode_value = self.kwargs.get("mode", "literal")
        return cast(
            PipelineOperationPayload,
            {
                "type": "spectroll",
                "mode": str(mode_value),
            },
        )


spectroll = Spectroll()


__all__ = ["Spectroll", "spectroll", "swap_colors"]
