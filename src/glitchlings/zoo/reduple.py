from __future__ import annotations

from collections.abc import Iterable

from .rushmore import (
    Rushmore,
    RushmoreMode,
    _normalize_modes,
    _python_reduplicate_words,
    reduplicate_words,
)


class Reduple(Rushmore):
    """Compatibility wrapper for Rushmore's duplication mode."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        seed: int | None = None,
        unweighted: bool = False,
        modes: RushmoreMode | str | Iterable[RushmoreMode | str] | None = None,
        duplicate_rate: float | None = None,
        duplicate_unweighted: bool | None = None,
    ) -> None:
        if modes is not None:
            normalized = _normalize_modes(modes)
            if any(mode is not RushmoreMode.DUPLICATE for mode in normalized):
                raise ValueError("Reduple only supports the 'duplicate' mode")

        effective_rate = 0.01 if rate is None else rate
        active_duplicate_rate = (
            duplicate_rate if duplicate_rate is not None else effective_rate
        )
        active_duplicate_unweighted = (
            duplicate_unweighted if duplicate_unweighted is not None else unweighted
        )
        super().__init__(
            name="Reduple",
            modes=RushmoreMode.DUPLICATE,
            rate=effective_rate,
            duplicate_rate=active_duplicate_rate,
            seed=seed,
            unweighted=unweighted,
            duplicate_unweighted=active_duplicate_unweighted,
        )
        self.kwargs.pop("delete_rate", None)
        self.kwargs.pop("delete_unweighted", None)
        self.kwargs.pop("swap_rate", None)


reduple = Reduple()


__all__ = ["Reduple", "reduple", "reduplicate_words", "_python_reduplicate_words"]
