"""Rust-backed Mim1c glitchling that swaps characters for homoglyphs."""

from __future__ import annotations

import random
from collections.abc import Collection, Iterable
from typing import Callable, Literal, cast

from glitchlings.constants import DEFAULT_MIM1C_RATE, MIM1C_DEFAULT_CLASSES
from glitchlings.internal.rust import get_rust_operation, resolve_seed

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload

_MIM1C_RUST = cast(Callable[..., str], get_rust_operation("mim1c"))


def _normalise_classes(
    value: object,
) -> tuple[str, ...] | Literal["all"] | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value.lower() == "all":
            return "all"
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    raise TypeError("classes must be an iterable of strings or 'all'")


def _normalise_banned(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return tuple(value)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    raise TypeError("banned_characters must be an iterable of strings")


def _serialise_classes(
    value: tuple[str, ...] | Literal["all"] | None,
) -> list[str] | Literal["all"] | None:
    if value is None:
        return None
    if value == "all":
        return "all"
    return list(value)


def _serialise_banned(value: tuple[str, ...] | None) -> list[str] | None:
    if value is None:
        return None
    return list(value)


def swap_homoglyphs(
    text: str,
    rate: float | None = None,
    classes: list[str] | Literal["all"] | None = None,
    banned_characters: Collection[str] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace characters with visually confusable homoglyphs via the Rust engine."""

    effective_rate = DEFAULT_MIM1C_RATE if rate is None else rate

    normalised_classes = _normalise_classes(classes)
    normalised_banned = _normalise_banned(banned_characters)

    if normalised_classes is None:
        payload_classes: list[str] | Literal["all"] | None = list(MIM1C_DEFAULT_CLASSES)
    else:
        payload_classes = _serialise_classes(normalised_classes)
    payload_banned = _serialise_banned(normalised_banned)

    return _MIM1C_RUST(
        text,
        effective_rate,
        payload_classes,
        payload_banned,
        resolve_seed(seed, rng),
    )


class Mim1c(Glitchling):
    """Glitchling that swaps characters for visually similar homoglyphs."""

    flavor = (
        "Breaks your parser by replacing some characters in strings with "
        "doppelgangers. Don't worry, this text is clean. ;)"
    )

    def __init__(
        self,
        *,
        rate: float | None = None,
        classes: list[str] | Literal["all"] | None = None,
        banned_characters: Collection[str] | None = None,
        seed: int | None = None,
    ) -> None:
        effective_rate = DEFAULT_MIM1C_RATE if rate is None else rate
        normalised_classes = _normalise_classes(classes)
        normalised_banned = _normalise_banned(banned_characters)
        super().__init__(
            name="Mim1c",
            corruption_function=swap_homoglyphs,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LAST,
            seed=seed,
            rate=effective_rate,
            classes=normalised_classes,
            banned_characters=normalised_banned,
        )

    def pipeline_operation(self) -> PipelineOperationPayload:
        rate_value = self.kwargs.get("rate")
        rate = DEFAULT_MIM1C_RATE if rate_value is None else float(rate_value)

        descriptor: dict[str, object] = {"type": "mimic", "rate": rate}

        classes = self.kwargs.get("classes")
        serialised_classes = _serialise_classes(classes)
        if serialised_classes is not None:
            descriptor["classes"] = serialised_classes

        banned = self.kwargs.get("banned_characters")
        serialised_banned = _serialise_banned(banned)
        if serialised_banned:
            descriptor["banned_characters"] = serialised_banned

        return cast(PipelineOperationPayload, descriptor)

    def set_param(self, key: str, value: object) -> None:
        if key == "classes":
            super().set_param(key, _normalise_classes(value))
            return
        if key == "banned_characters":
            super().set_param(key, _normalise_banned(value))
            return
        super().set_param(key, value)


mim1c = Mim1c()


__all__ = ["Mim1c", "mim1c", "swap_homoglyphs"]
