from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .rushmore import (
    Rushmore,
    RushmoreMode,
    _normalize_modes,
    _python_swap_adjacent_words,
    swap_adjacent_words,
)


class Adjax(Rushmore):
    """Compatibility wrapper for Rushmore's adjacent swap mode."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        swap_rate: float | None = None,
        unweighted: bool = False,
    ) -> None:
        if modes is not None:
            normalized = _normalize_modes(modes)
            if any(mode is not RushmoreMode.SWAP for mode in normalized):
                raise ValueError("Adjax only supports the 'swap' mode")

        effective_rate = 0.5 if rate is None else rate
        clamped = max(0.0, min(effective_rate, 1.0))
        active_swap_rate = swap_rate if swap_rate is not None else effective_rate
        super().__init__(
            name="Adjax",
            modes=RushmoreMode.SWAP,
            rate=clamped,
            swap_rate=active_swap_rate,
            seed=seed,
            unweighted=unweighted,
        )
        self.kwargs.pop("delete_rate", None)
        self.kwargs.pop("duplicate_rate", None)
        self.kwargs.pop("delete_unweighted", None)
        self.kwargs.pop("duplicate_unweighted", None)

    def set_param(self, key: str, value: Any) -> None:
        if key == "rate":
            super().set_param("swap_rate", value)
        super().set_param(key, value)


adjax = Adjax()


__all__ = ["Adjax", "adjax", "swap_adjacent_words", "_python_swap_adjacent_words"]
