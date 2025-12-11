"""Rust-backed Mim1c glitchling that swaps characters for homoglyphs.

The Mim1c glitchling replaces characters with visually similar confusable
characters (homoglyphs) based on Unicode Technical Standard #39.

## Modes

- **single_script** (safest): Only substitute within the same script
  (Latin→Latin variants). Minimal visual disruption.
- **mixed_script** (default): Allow visually similar cross-script substitutions
  (Latin↔Cyrillic↔Greek). Maximum visual similarity with some mixed scripts.
- **compatibility**: Include Unicode compatibility variants
  (fullwidth, math alphanumerics). Wider range of substitutions.
- **aggressive**: All of the above combined. Most aggressive substitution.

## Locality Control

`max_consecutive` limits how many adjacent characters can be substituted,
preventing the "ransom note" effect where every character is from a different
script. Default is 3.

## Data Source

Confusable mappings derived from Unicode Technical Standard #39 (confusables.txt).

## References

- **Unicode Technical Standard #39**: Unicode Security Mechanisms
  - https://www.unicode.org/reports/tr39/
- **confusables.txt**: Official confusable character mappings
  - https://www.unicode.org/Public/security/latest/confusables.txt
"""

from __future__ import annotations

import random
from collections.abc import Collection, Iterable
from typing import Any, Literal, cast

from glitchlings.constants import (
    DEFAULT_MIM1C_MAX_CONSECUTIVE,
    DEFAULT_MIM1C_MODE,
    DEFAULT_MIM1C_RATE,
    MIM1C_DEFAULT_CLASSES,
)
from glitchlings.internal.rust_ffi import resolve_seed, swap_homoglyphs_rust

from .core import AttackOrder, AttackWave, Glitchling, PipelineOperationPayload
from .validation import normalize_mim1c_max_consecutive, normalize_mim1c_mode


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


HomoglyphMode = Literal["single_script", "mixed_script", "compatibility", "aggressive"]


def swap_homoglyphs(
    text: str,
    rate: float | None = None,
    classes: list[str] | Literal["all"] | None = None,
    banned_characters: Collection[str] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    mode: HomoglyphMode | None = None,
    max_consecutive: int | None = None,
) -> str:
    """Replace characters with visually confusable homoglyphs via the Rust engine.

    Args:
        text: The input text to transform.
        rate: Probability of substituting each eligible character. Default 0.02.
        classes: Unicode script classes to include.
            Default ["LATIN", "GREEK", "CYRILLIC", "COMMON"].
        banned_characters: Characters to never use as substitutes.
        seed: Random seed for deterministic behavior.
        rng: Optional random.Random instance (alternative to seed).
        mode: Substitution mode controlling confusable types:
            - "single_script": Only same-script substitutions (safest).
            - "mixed_script": Allow cross-script like Latin↔Cyrillic↔Greek (default).
            - "compatibility": Include fullwidth, math alphanumerics.
            - "aggressive": All confusable types.
        max_consecutive: Maximum consecutive characters to substitute. Default 3.
            Set to 0 for unlimited.

    Returns:
        Text with some characters replaced by visually similar confusables.
    """
    effective_rate = DEFAULT_MIM1C_RATE if rate is None else rate
    effective_mode = normalize_mim1c_mode(mode, DEFAULT_MIM1C_MODE)
    effective_max_consecutive = normalize_mim1c_max_consecutive(
        max_consecutive, DEFAULT_MIM1C_MAX_CONSECUTIVE
    )

    normalised_classes = _normalise_classes(classes)
    normalised_banned = _normalise_banned(banned_characters)

    if normalised_classes is None:
        payload_classes: list[str] | Literal["all"] | None = list(MIM1C_DEFAULT_CLASSES)
    else:
        payload_classes = _serialise_classes(normalised_classes)
    payload_banned = _serialise_banned(normalised_banned)

    return swap_homoglyphs_rust(
        text,
        effective_rate,
        payload_classes,
        payload_banned,
        resolve_seed(seed, rng),
        effective_mode,
        effective_max_consecutive,
    )


class Mim1c(Glitchling):
    """Glitchling that swaps characters for visually similar homoglyphs.

    Mim1c replaces characters with visually similar confusable characters
    (homoglyphs) based on Unicode Technical Standard #39.

    ## Modes

    - **single_script** (safest): Only substitute within the same script
      (Latin→Latin variants). Minimal visual disruption.
    - **mixed_script** (default): Allow visually similar cross-script substitutions
      (Latin↔Cyrillic↔Greek). Maximum visual similarity with some mixed scripts.
    - **compatibility**: Include Unicode compatibility variants
      (fullwidth, math alphanumerics). Wider range of substitutions.
    - **aggressive**: All of the above combined. Most aggressive substitution.

    ## Locality Control

    `max_consecutive` limits how many adjacent characters can be substituted,
    preventing the "ransom note" effect where every character is from a different
    script. Default is 3. Set to 0 for unlimited.

    Args:
        rate: Probability of substituting each eligible character. Default 0.02.
        classes: Unicode script classes to include.
            Default ["LATIN", "GREEK", "CYRILLIC", "COMMON"].
        banned_characters: Characters to never use as substitutes.
        mode: Substitution mode. One of "single_script", "mixed_script",
            "compatibility", "aggressive".
        max_consecutive: Maximum consecutive characters to substitute. Default 3.
        seed: Random seed for deterministic behavior.
    """

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
        mode: HomoglyphMode | None = None,
        max_consecutive: int | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> None:
        effective_rate = DEFAULT_MIM1C_RATE if rate is None else rate
        effective_mode = normalize_mim1c_mode(mode, DEFAULT_MIM1C_MODE)
        effective_max_consecutive = normalize_mim1c_max_consecutive(
            max_consecutive, DEFAULT_MIM1C_MAX_CONSECUTIVE
        )
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
            mode=effective_mode,
            max_consecutive=effective_max_consecutive,
            **kwargs,
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

        # Add mode and max_consecutive parameters
        mode = self.kwargs.get("mode")
        if mode is not None:
            descriptor["mode"] = str(mode)

        max_consecutive = self.kwargs.get("max_consecutive")
        if max_consecutive is not None:
            descriptor["max_consecutive"] = int(max_consecutive)

        return cast(PipelineOperationPayload, descriptor)

    def set_param(self, key: str, value: object) -> None:
        if key == "classes":
            super().set_param(key, _normalise_classes(value))
            return
        if key == "banned_characters":
            super().set_param(key, _normalise_banned(value))
            return
        if key == "mode":
            super().set_param(key, normalize_mim1c_mode(str(value) if value else None))
            return
        if key == "max_consecutive":
            int_value: int | None = int(cast(Any, value)) if value is not None else None
            super().set_param(key, normalize_mim1c_max_consecutive(int_value))
            return
        super().set_param(key, value)


mim1c = Mim1c()


__all__ = ["Mim1c", "mim1c", "swap_homoglyphs", "HomoglyphMode"]
