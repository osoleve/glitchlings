"""Hokey glitchling that performs expressive lengthening."""

from __future__ import annotations

import random
from functools import cache
from typing import Any, Callable, cast

from ._rust_extensions import get_rust_operation, resolve_seed
from .core import AttackOrder, AttackWave, Gaggle, PipelineOperationPayload
from .core import Glitchling as GlitchlingBase

HokeyRustCallable = Callable[[str, float, int, int, int, float, int | None], str]


@cache
def _hokey_rust() -> HokeyRustCallable:
    """Return the compiled Hokey operation, importing it lazily."""

    return cast(
        HokeyRustCallable,
        get_rust_operation("hokey"),
    )


def extend_vowels(
    text: str,
    rate: float = 0.3,
    extension_min: int = 2,
    extension_max: int = 5,
    word_length_threshold: int = 6,
    seed: int | None = None,
    rng: random.Random | None = None,
    base_p: float | None = None,
) -> str:
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
    base_p : float, optional
        Base probability for the negative-binomial sampler (heavier tails for smaller
        values). Defaults to ``0.45``.
    """
    if not text:
        return text

    base_probability = base_p if base_p is not None else 0.45

    seed_value = resolve_seed(seed, rng)
    operation = _hokey_rust()
    return operation(
        text,
        rate,
        extension_min,
        extension_max,
        word_length_threshold,
        base_probability,
        seed_value,
    )


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
            return extend_vowels(text, **kwargs)

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

    def pipeline_operation(self) -> PipelineOperationPayload:
        kwargs = self.kwargs
        rate = kwargs.get("rate")
        extension_min = kwargs.get("extension_min")
        extension_max = kwargs.get("extension_max")
        word_length_threshold = kwargs.get("word_length_threshold")
        base_p = kwargs.get("base_p")
        return cast(
            PipelineOperationPayload,
            {
                "type": "hokey",
                "rate": 0.3 if rate is None else float(rate),
                "extension_min": 2 if extension_min is None else int(extension_min),
                "extension_max": 5 if extension_max is None else int(extension_max),
                "word_length_threshold": 6
                if word_length_threshold is None
                else int(word_length_threshold),
                "base_p": 0.45 if base_p is None else float(base_p),
            },
        )

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
