"""Hokey glitchling that performs expressive lengthening."""

from __future__ import annotations

import random
from typing import Any, Callable, cast

from ..util.hokey_generator import HokeyConfig, HokeyGenerator, StretchEvent
from ..util.stretchability import StretchabilityAnalyzer
from ._rust_extensions import get_rust_operation, resolve_seed
from .core import AttackOrder, AttackWave, Gaggle, PipelineOperationPayload
from .core import Glitchling as GlitchlingBase

StretchResult = str | tuple[str, list[StretchEvent]]
HokeyRustCallable = Callable[[str, float, int, int, int, float, int | None], StretchResult]

_hokey_rust = cast(HokeyRustCallable, get_rust_operation("hokey"))
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

    base_probability = base_p if base_p is not None else 0.45

    config = HokeyConfig(
        rate=rate,
        extension_min=extension_min,
        extension_max=extension_max,
        base_p=base_probability,
        word_length_threshold=word_length_threshold,
    )

    seed_value = resolve_seed(seed, rng)

    trace_events: list[StretchEvent] | None = None
    if return_trace:
        trace_rng = random.Random(seed_value)
        _, trace_events = _GENERATOR.generate(
            text,
            rng=trace_rng,
            config=config,
        )

    result: StretchResult = _hokey_rust(
        text,
        rate,
        extension_min,
        extension_max,
        word_length_threshold,
        base_probability,
        seed_value,
    )

    if isinstance(result, tuple):
        output, events = result
        if return_trace:
            return output, events
        return output

    output = result

    if return_trace:
        assert trace_events is not None
        return output, trace_events

    return output


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
