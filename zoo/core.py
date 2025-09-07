from enum import IntEnum, auto
import random
from typing import Any, Callable
from util import string_diffs, SAMPLE_TEXT

import functools as ft


# Text levels for glitchlings, to enforce a sort order
# Work from highest level down, because e.g.
# duplicating a word then adding a typo is potentially different than
# adding a typo then duplicating a word
class AttackWave(IntEnum):
    DOCUMENT = auto()
    PARAGRAPH = auto()
    SENTENCE = auto()
    WORD = auto()
    CHARACTER = auto()


# Modifier for within the same attack wave
class AttackOrder(IntEnum):
    FIRST = auto()
    EARLY = auto()
    NORMAL = auto()
    LATE = auto()
    LAST = auto()


class Glitchling:
    def __init__(
        self,
        name: str,
        corruption_function: Callable,
        scope: AttackWave,
        order: AttackOrder = AttackOrder.NORMAL,
        seed: int | None = None,
        **kwargs,
    ):
        # Each Glitchling maintains its own RNG for deterministic yet isolated behavior.
        # If no seed is supplied, we fall back to Python's default entropy.
        self.seed = seed
        self.rng: random.Random = random.Random(seed)
        self.name: str = name
        self.corruption_function: Callable[..., str] = corruption_function
        self.img: str = ""
        self.translations: dict[str, str] = {}
        self.level: AttackWave = scope
        self.order: AttackOrder = order
        self.kwargs: dict[str, Any] = {}
        for kw, val in kwargs.items():
            self.set_param(kw, val)

    def set_param(self, key: str, value: Any):
        setattr(self, key, value)
        self.kwargs[key] = value

    def __corrupt(self, text, *args, **kwargs):
        # Pass rng to underlying corruption function if it expects it.
        if "rng" in self.corruption_function.__code__.co_varnames:
            corrupted = self.corruption_function(text, *args, rng=self.rng, **kwargs)
        else:
            corrupted = self.corruption_function(text, *args, **kwargs)
        self.translations[text] = corrupted
        return corrupted

    def corrupt(self, text: str) -> str:
        return self.__corrupt(text, **self.kwargs)

    def pretty_diff(self, text_in):
        text_out = self.translations[text_in]
        diff = string_diffs(text_in, text_out)
        return diff

    def __call__(self, text: str, *args, **kwds) -> str:
        return self.corrupt(text, *args, **kwds)

    def __repr__(self) -> str:
        return f"""{self.name} says {self.corrupt(SAMPLE_TEXT)}"""

    def get_translations(self) -> dict:
        return self.translations

    def reset_rng(self, seed=None):
        """Reset this glitchling's RNG to its initial seed (if one was provided)."""
        if seed is not None:
            self.seed = seed
        if self.seed is not None:
            self.rng = random.Random(self.seed)
            # do not clear translations to allow diffing history


class Gaggle(Glitchling):
    def __init__(self, glitchlings: list[Glitchling], seed: int | None = None):
        super().__init__("Gaggle", self.corrupt, AttackWave.DOCUMENT, seed=seed)
        # Derive deterministic per-glitchling seeds from master seed if provided
        if seed is not None:
            for idx, g in enumerate(glitchlings):
                # Only override if the glitchling did not already specify a seed explicitly
                if getattr(g, "seed", None) is None:
                    derived_seed = Gaggle.derive_seed(seed, g.name, idx)
                    g.seed = derived_seed
                    g.rng = random.Random(derived_seed)
                g.reset_rng()
        self.glitchlings = {level: [] for level in AttackWave}
        for g in glitchlings:
            self.glitchlings[g.level].append(g)
        self.sort_glitchlings()

    @staticmethod
    def derive_seed(master_seed: int, glitchling_name: str, index: int) -> int:
        """Derive a deterministic seed for a glitchling based on the master seed."""
        return hash((master_seed, glitchling_name, index)) & 0xFFFFFFFF

    def sort_glitchlings(self):
        self.apply_order = [
            g
            for _, glitchlings in sorted(self.glitchlings.items())
            for g in sorted(glitchlings, key=lambda x: (x.order, x.name))
        ]

    def corrupt(self, text: str) -> str:
        corrupted = text
        for glitchling in self.apply_order:
            # Ensure deterministic behavior per call when seeds are defined
            glitchling.reset_rng()
            corrupted = glitchling(corrupted)
            self.translations[text] = corrupted
        return corrupted

    def pretty_diff(self, text_in):
        result = []
        for glitchling in self.apply_order:
            diff = glitchling.pretty_diff(text_in)
            result.append(f"{glitchling.name}:\n{diff}\n")
            text_in = glitchling.get_translations().get(text_in, text_in)

        return "\n".join(result)
