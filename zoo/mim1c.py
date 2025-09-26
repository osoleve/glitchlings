from typing import Literal
from .core import Glitchling, AttackWave, AttackOrder
import random
from confusable_homoglyphs import confusables


def swap_homoglyphs(
    text: str,
    replacement_rate: float = 0.02,
    classes: list[str] | Literal["all"] | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    """Replace characters with visually confusable homoglyphs.

    Parameters
    - text: Input text.
    - replacement_rate: Max proportion of eligible characters to replace (default 0.02).
    - classes: Restrict replacements to these Unicode script classes (default ["LATIN","GREEK","CYRILLIC"]). Use "all" to allow any.
    - seed: Optional seed if `rng` not provided.
    - rng: Optional RNG; overrides seed.

    Notes
    - Only replaces characters present in confusables.confusables_data with single-codepoint alternatives.
    - Maintains determinism by shuffling candidates and sampling via the provided RNG.
    """
    if rng is None:
        rng = random.Random(seed)

    if classes is None:
        classes = ["LATIN", "GREEK", "CYRILLIC"]

    target_chars = [char for char in text if char.isalnum()]
    confusable_chars = [
        char for char in target_chars if char in confusables.confusables_data
    ]
    num_replacements = int(len(confusable_chars) * replacement_rate)
    done = 0
    rng.shuffle(confusable_chars)
    for char in confusable_chars:
        if done >= num_replacements:
            break
        options = [
            o["c"] for o in confusables.confusables_data[char] if len(o["c"]) == 1
        ]
        if classes != "all":
            options = [opt for opt in options if confusables.alias(opt) in classes]
        if not options:
            continue
        text = text.replace(char, rng.choice(options), 1)
        done += 1
    return text


mim1c = Glitchling(
    name="Mim1c",
    corruption_function=swap_homoglyphs,
    scope=AttackWave.CHARACTER,
    order=AttackOrder.LATE,
    replacement_rate=0.02,
    classes=["LATIN", "GREEK", "CYRILLIC"],
)
