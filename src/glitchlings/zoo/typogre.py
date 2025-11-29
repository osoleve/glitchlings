from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any, cast

from glitchlings.constants import DEFAULT_TYPOGRE_KEYBOARD, DEFAULT_TYPOGRE_RATE
from glitchlings.internal.rust_ffi import fatfinger_rust, resolve_seed

from ..util import KEYNEIGHBORS, SHIFT_MAPS
from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def _resolve_slip_exit_rate(
    shift_slip_rate: float,
    shift_slip_exit_rate: float | None,
) -> float:
    """Derive the slip exit rate, defaulting to a burst-friendly value."""

    if shift_slip_exit_rate is not None:
        return max(0.0, shift_slip_exit_rate)
    return max(0.0, shift_slip_rate * 0.5)


def fatfinger(
    text: str,
    rate: float | None = None,
    keyboard: str = DEFAULT_TYPOGRE_KEYBOARD,
    layout: Mapping[str, Sequence[str]] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    shift_slip_rate: float = 0.0,
    shift_slip_exit_rate: float | None = None,
    shift_map: Mapping[str, str] | None = None,
) -> str:
    """Introduce character-level "fat finger" edits with a Rust fast path."""
    effective_rate = DEFAULT_TYPOGRE_RATE if rate is None else rate

    if not text:
        return ""

    layout_mapping = layout if layout is not None else getattr(KEYNEIGHBORS, keyboard)
    slip_rate = max(0.0, shift_slip_rate)
    slip_exit_rate = _resolve_slip_exit_rate(slip_rate, shift_slip_exit_rate)
    slip_map = shift_map if shift_map is not None else getattr(SHIFT_MAPS, keyboard, None)

    clamped_rate = max(0.0, effective_rate)
    if slip_rate == 0.0 and clamped_rate == 0.0:
        return text

    return fatfinger_rust(
        text,
        clamped_rate,
        layout_mapping,
        resolve_seed(seed, rng),
        shift_slip_rate=slip_rate,
        shift_slip_exit_rate=slip_exit_rate,
        shift_map=slip_map,
    )


class Typogre(Glitchling):
    """Glitchling that introduces deterministic keyboard-typing errors."""

    flavor = "What a nice word, would be a shame if something happened to it..."

    def __init__(
        self,
        *,
        rate: float | None = None,
        keyboard: str = DEFAULT_TYPOGRE_KEYBOARD,
        shift_slip_rate: float = 0.0,
        shift_slip_exit_rate: float | None = None,
        seed: int | None = None,
        **kwargs: Any,
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
            shift_slip_rate=max(0.0, shift_slip_rate),
            shift_slip_exit_rate=shift_slip_exit_rate,
            **kwargs,
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
        shift_slip_rate = float(self.kwargs.get("shift_slip_rate", 0.0) or 0.0)
        shift_slip_exit_rate = self.kwargs.get("shift_slip_exit_rate")
        resolved_exit_rate = _resolve_slip_exit_rate(shift_slip_rate, shift_slip_exit_rate)
        shift_map = getattr(SHIFT_MAPS, str(keyboard), None)
        if shift_slip_rate > 0.0 and shift_map is None:
            message = f"Unknown shift map layout '{keyboard}' for Typogre pipeline"
            raise RuntimeError(message)
        serialized_shift_map = dict(shift_map) if shift_map is not None else None

        return cast(
            PipelineOperationPayload,
            {
                "type": "typo",
                "rate": float(rate),
                "keyboard": str(keyboard),
                "layout": serialized_layout,
                "shift_slip_rate": shift_slip_rate,
                "shift_slip_exit_rate": float(resolved_exit_rate),
                "shift_map": serialized_shift_map,
            },
        )


typogre = Typogre()


__all__ = ["Typogre", "typogre", "fatfinger"]
