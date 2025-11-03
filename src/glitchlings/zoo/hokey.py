"""Hokey glitchling that performs expressive lengthening."""

from __future__ import annotations

import random
from typing import Any, Callable, cast

from ..util.hokey_generator import HokeyConfig, HokeyGenerator, StretchEvent
from ..util.stretchability import StretchabilityAnalyzer
from ._rust_extensions import get_rust_operation
from .core import AttackOrder, AttackWave, Gaggle
from .core import Glitchling as GlitchlingBase

StretchResult = str | tuple[str, list[StretchEvent]]
HokeyRustCallable = Callable[[str, float, int, int, int, float, random.Random], StretchResult]

_hokey_rust = cast(HokeyRustCallable | None, get_rust_operation("hokey"))
_ANALYZER = StretchabilityAnalyzer()
_GENERATOR = HokeyGenerator(analyzer=_ANALYZER)


def extend_vowels(
    text: str,
    rate: float = 0.3,
    extension_min: int = 2,
    extension_max: int = 5,
    word_length_threshold: int = 6,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    return_trace: bool = False,
    base_p: float | None = None,
) -> str | tuple[str, list[StretchEvent]]:
    """Extend expressive segments of words for emphasis.

    Parameters
    ----------
    text : str
        Input text to transform.
    rate : float, optional
        Global selection rate for candidate words.
    extension_min : int, optional
        Minimum number of extra repetitions for the stretch unit.
    extension_max : int, optional
        Maximum number of extra repetitions for the stretch unit.
    word_length_threshold : int, optional
        Preferred maximum alphabetic length; longer words are de-emphasised but not
        excluded.
    seed : int, optional
        Deterministic seed when ``rng`` is not supplied.
    rng : random.Random, optional
        Random number generator to drive sampling.
    return_trace : bool, optional
        When ``True`` also return the stretch events for introspection.
    base_p : float, optional
        Base probability for the negative-binomial sampler (heavier tails for smaller
        values). Defaults to ``0.45``.
    """
    if not text:
        empty_trace: list[StretchEvent] = []
        return (text, empty_trace) if return_trace else text

    if rng is None:
        rng = random.Random(seed)
    base_probability = base_p if base_p is not None else 0.45

    config = HokeyConfig(
        rate=rate,
        extension_min=extension_min,
        extension_max=extension_max,
        base_p=base_probability,
        word_length_threshold=word_length_threshold,
    )

    def _generate_with_trace() -> tuple[str, list[StretchEvent]]:
        return _GENERATOR.generate(text, rng=rng, config=config)

    if return_trace:
        return _generate_with_trace()

    if _hokey_rust is not None:
        try:
            result: StretchResult = _hokey_rust(
                text,
                rate,
                extension_min,
                extension_max,
                word_length_threshold,
                base_probability,
                rng,
            )
        except RuntimeError:
            # Fall back to the Python implementation if the Rust path errors at runtime.
            pass
        else:
            if isinstance(result, tuple):
                return result[0]
            return result

    python_result, _ = _generate_with_trace()
    return python_result


class Hokey(GlitchlingBase):
    """Glitchling that stretches words using linguistic heuristics."""

    seed: int | None

    def __init__(
        self,
        *,
        rate: float = 0.3,
        extension_min: int = 2,
        extension_max: int = 5,
        word_length_threshold: int = 6,
        base_p: float = 0.45,
        seed: int | None = None,
    ) -> None:
        self._master_seed: int | None = seed

        def _corruption_wrapper(text: str, **kwargs: Any) -> str:
            result = extend_vowels(text, **kwargs)
            return result if isinstance(result, str) else result[0]

        super().__init__(
            name="Hokey",
            corruption_function=_corruption_wrapper,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.FIRST,
            seed=seed,
            rate=rate,
            extension_min=extension_min,
            extension_max=extension_max,
            word_length_threshold=word_length_threshold,
            base_p=base_p,
        )

    def pipeline_operation(self) -> dict[str, Any] | None:
        return {
            "type": "hokey",
            "rate": self.kwargs.get("rate", 0.3),
            "extension_min": self.kwargs.get("extension_min", 2),
            "extension_max": self.kwargs.get("extension_max", 5),
            "word_length_threshold": self.kwargs.get("word_length_threshold", 6),
            "base_p": self.kwargs.get("base_p", 0.45),
        }

    def reset_rng(self, seed: int | None = None) -> None:
        if seed is not None:
            self._master_seed = seed
            super().reset_rng(seed)
            if self.seed is None:
                return
            derived = Gaggle.derive_seed(int(seed), self.name, 0)
            self.seed = int(derived)
            self.rng = random.Random(self.seed)
            self.kwargs["seed"] = self.seed
        else:
            super().reset_rng(None)


hokey = Hokey()


__all__ = ["Hokey", "hokey", "extend_vowels"]
