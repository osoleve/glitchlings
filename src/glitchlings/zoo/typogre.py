from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any, cast

from glitchlings.constants import (
    DEFAULT_TYPOGRE_KEYBOARD,
    DEFAULT_TYPOGRE_MOTOR_WEIGHTING,
    DEFAULT_TYPOGRE_RATE,
)
from glitchlings.internal.rust_ffi import keyboard_typo_rust, resolve_seed

from ..util import (
    KEYNEIGHBORS,
    MOTOR_WEIGHTS,
    SHIFT_MAPS,
    get_serialized_layout,
    get_serialized_shift_map,
)
from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload


def _resolve_slip_exit_rate(
    shift_slip_rate: float,
    shift_slip_exit_rate: float | None,
) -> float:
    """Derive the slip exit rate, defaulting to a burst-friendly value."""

    if shift_slip_exit_rate is not None:
        return max(0.0, shift_slip_exit_rate)
    return max(0.0, shift_slip_rate * 0.5)


def _resolve_motor_weighting(motor_weighting: str | None) -> str:
    """Resolve motor weighting mode, validating against known modes."""
    if motor_weighting is None:
        return DEFAULT_TYPOGRE_MOTOR_WEIGHTING

    normalized = motor_weighting.lower().replace("-", "_").replace(" ", "_")
    if normalized not in MOTOR_WEIGHTS:
        valid_modes = ", ".join(sorted(MOTOR_WEIGHTS.keys()))
        message = f"Unknown motor weighting '{motor_weighting}'. Valid modes: {valid_modes}"
        raise ValueError(message)
    return normalized


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
    motor_weighting: str | None = None,
) -> str:
    """Introduce character-level "fat finger" edits with a Rust fast path.

    Args:
        text: Input text to corrupt.
        rate: Probability of corrupting each character (default 0.02).
        keyboard: Keyboard layout name for adjacency mapping.
        layout: Custom keyboard neighbor mapping (overrides keyboard).
        seed: Deterministic seed for reproducible results.
        rng: Random generator (alternative to seed).
        shift_slip_rate: Probability of entering a shifted burst.
        shift_slip_exit_rate: Probability of releasing shift during a burst.
        shift_map: Custom unshifted->shifted character mapping.
        motor_weighting: Weighting mode for error sampling based on finger/hand
            coordination. One of 'uniform' (default), 'wet_ink', or 'hastily_edited'.

    Returns:
        Text with simulated typing errors.
    """
    effective_rate = DEFAULT_TYPOGRE_RATE if rate is None else rate

    if not text:
        return ""

    layout_mapping = layout if layout is not None else getattr(KEYNEIGHBORS, keyboard)
    slip_rate = max(0.0, shift_slip_rate)
    slip_exit_rate = _resolve_slip_exit_rate(slip_rate, shift_slip_exit_rate)
    slip_map = shift_map if shift_map is not None else getattr(SHIFT_MAPS, keyboard, None)
    resolved_motor_weighting = _resolve_motor_weighting(motor_weighting)

    clamped_rate = max(0.0, effective_rate)
    if slip_rate == 0.0 and clamped_rate == 0.0:
        return text

    return keyboard_typo_rust(
        text,
        clamped_rate,
        layout_mapping,
        resolve_seed(seed, rng),
        shift_slip_rate=slip_rate,
        shift_slip_exit_rate=slip_exit_rate,
        shift_map=slip_map,
        motor_weighting=resolved_motor_weighting,
    )


class Typogre(Glitchling):
    """Glitchling that introduces deterministic keyboard-typing errors.

    Args:
        rate: Probability of corrupting each character (default 0.02).
        keyboard: Keyboard layout name for adjacency mapping.
        shift_slip_rate: Probability of entering a shifted burst.
        shift_slip_exit_rate: Probability of releasing shift during a burst.
        motor_weighting: Weighting mode for error sampling based on finger/hand
            coordination. One of:
            - 'uniform': All neighbors equally likely (default, original behavior).
            - 'wet_ink': Simulates uncorrected errors - same-finger errors are
              caught and corrected, cross-hand errors slip through.
            - 'hastily_edited': Simulates raw typing before correction - same-finger
              errors occur most often.
        seed: Deterministic seed for reproducible results.
    """

    flavor = "What a nice word, would be a shame if something happened to it..."

    def __init__(
        self,
        *,
        rate: float | None = None,
        keyboard: str = DEFAULT_TYPOGRE_KEYBOARD,
        shift_slip_rate: float = 0.0,
        shift_slip_exit_rate: float | None = None,
        motor_weighting: str | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_TYPOGRE_RATE if rate is None else rate
        resolved_motor_weighting = _resolve_motor_weighting(motor_weighting)
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
            motor_weighting=resolved_motor_weighting,
            **kwargs,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        rate_value = self.kwargs.get("rate")
        rate = DEFAULT_TYPOGRE_RATE if rate_value is None else float(rate_value)
        keyboard = str(self.kwargs.get("keyboard", DEFAULT_TYPOGRE_KEYBOARD))

        # Use pre-serialized layout (cached at module load time)
        serialized_layout = get_serialized_layout(keyboard)
        if serialized_layout is None:
            message = f"Unknown keyboard layout '{keyboard}' for Typogre pipeline"
            raise RuntimeError(message)

        shift_slip_rate = float(self.kwargs.get("shift_slip_rate", 0.0) or 0.0)
        shift_slip_exit_rate = self.kwargs.get("shift_slip_exit_rate")
        resolved_exit_rate = _resolve_slip_exit_rate(shift_slip_rate, shift_slip_exit_rate)

        # Use pre-serialized shift map (already a dict, no copy needed)
        serialized_shift_map = get_serialized_shift_map(keyboard)
        if shift_slip_rate > 0.0 and serialized_shift_map is None:
            message = f"Unknown shift map layout '{keyboard}' for Typogre pipeline"
            raise RuntimeError(message)

        motor_weighting = self.kwargs.get("motor_weighting", DEFAULT_TYPOGRE_MOTOR_WEIGHTING)

        return cast(
            PipelineOperationPayload,
            {
                "type": "typo",
                "rate": float(rate),
                "keyboard": keyboard,
                "layout": serialized_layout,
                "shift_slip_rate": shift_slip_rate,
                "shift_slip_exit_rate": float(resolved_exit_rate),
                "shift_map": serialized_shift_map,
                "motor_weighting": str(motor_weighting),
            },
        )


typogre = Typogre()


__all__ = ["Typogre", "typogre", "fatfinger"]
