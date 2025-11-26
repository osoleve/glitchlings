"""Spectroll glitchling: Color term swapping.

.. deprecated:: 0.10.0
    Spectroll is now a thin wrapper around :class:`Jargoyle` with
    ``lexemes="colors"``. Use Jargoyle directly for new code.
"""

from __future__ import annotations

import random
import warnings
from typing import cast

from glitchlings.internal.rust_ffi import jargoyle_drift_rust, resolve_seed

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def swap_colors(
    text: str,
    *,
    mode: str = "literal",
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Delegate colour swapping to the compiled Rust implementation.

    .. deprecated:: 0.10.0
        Use :func:`jargoyle_drift` with ``lexemes="colors"`` instead.
    """

    normalized_mode = mode or "literal"
    resolved_seed: int | None
    if normalized_mode.lower() == "drift":
        resolved_seed = resolve_seed(seed, rng)
    else:
        resolved_seed = None

    # Use new Jargoyle backend with colors dictionary
    return jargoyle_drift_rust(text, "colors", normalized_mode, 1.0, resolved_seed)


class Spectroll(Glitchling):
    """Glitchling that remaps colour terms.

    .. deprecated:: 0.10.0
        Use :class:`Jargoyle` with ``lexemes="colors"`` instead::

            from glitchlings import Jargoyle
            jargoyle = Jargoyle(lexemes="colors", mode="literal")

    Spectroll is now a thin wrapper around Jargoyle that maintains
    backward compatibility with existing code.
    """

    flavor = "The colors, Duke, the colors!</br>*I'm colorblind, kid.*"

    def __init__(
        self,
        *,
        mode: str = "literal",
        seed: int | None = None,
    ) -> None:
        warnings.warn(
            "Spectroll is deprecated. Use Jargoyle(lexemes='colors') instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        """Return the pipeline descriptor.

        Uses the new Jargoyle operation type with colors lexemes.
        """
        mode_value = self.kwargs.get("mode", "literal")
        return cast(
            PipelineOperationPayload,
            {
                "type": "jargoyle",
                "lexemes": "colors",
                "mode": str(mode_value),
                "rate": 1.0,
            },
        )


spectroll = Spectroll()


__all__ = ["Spectroll", "spectroll", "swap_colors"]
