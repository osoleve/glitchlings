from collections.abc import Collection
import random
from typing import Literal

from confusable_homoglyphs import confusables

from .core import AttackOrder, AttackWave, Glitchling
from ._rate import resolve_rate


def swap_homoglyphs(
    text: str,
    rate: float | None = None,
    classes: list[str] | Literal["all"] | None = None,
    banned_characters: Collection[str] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
    *,
    replacement_rate: float | None = None,
) -> str:
    """Replace characters with visually confusable homoglyphs.

    Parameters
    - text: Input text.
    - rate: Max proportion of eligible characters to replace (default 0.02).
    - classes: Restrict replacements to these Unicode script classes (default ["LATIN","GREEK","CYRILLIC"]). Use "all" to allow any.
    - banned_characters: Characters that must never appear as replacements.
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.

    Notes
    - Only replaces characters present in confusables.confusables_data with single-codepoint alternatives.
    - Maintains determinism by shuffling candidates and sampling via the provided RNG.
    """
    effective_rate = resolve_rate(
        rate=rate,
        legacy_value=replacement_rate,
        default=0.02,
        legacy_name="replacement_rate",
    )

    if rng is None:
        rng = random.Random(seed)

    if classes is None:
        classes = ["LATIN", "GREEK", "CYRILLIC"]

    target_chars = [char for char in text if char.isalnum()]
    confusable_chars = [
        char for char in target_chars if char in confusables.confusables_data
    ]
    clamped_rate = max(0.0, effective_rate)
    num_replacements = int(len(confusable_chars) * clamped_rate)
    done = 0
    rng.shuffle(confusable_chars)
    banned_set = set(banned_characters or ())
    for char in confusable_chars:
        if done >= num_replacements:
            break
        options = [
            o["c"] for o in confusables.confusables_data[char] if len(o["c"]) == 1
        ]
        if classes != "all":
            options = [opt for opt in options if confusables.alias(opt) in classes]
        if banned_set:
            options = [opt for opt in options if opt not in banned_set]
        if not options:
            continue
        text = text.replace(char, rng.choice(options), 1)
        done += 1
    return text


class Mim1c(Glitchling):
    """Glitchling that swaps characters for visually similar homoglyphs."""

    def __init__(
        self,
        *,
        rate: float | None = None,
        replacement_rate: float | None = None,
        classes: list[str] | Literal["all"] | None = None,
        banned_characters: Collection[str] | None = None,
        seed: int | None = None,
    ) -> None:
        self._param_aliases = {"replacement_rate": "rate"}
        effective_rate = resolve_rate(
            rate=rate,
            legacy_value=replacement_rate,
            default=0.02,
            legacy_name="replacement_rate",
        )
        super().__init__(
            name="Mim1c",
            corruption_function=swap_homoglyphs,
            scope=AttackWave.CHARACTER,
            order=AttackOrder.LAST,
            seed=seed,
            rate=effective_rate,
            classes=classes,
            banned_characters=banned_characters,
        )


mim1c = Mim1c()


__all__ = ["Mim1c", "mim1c"]
