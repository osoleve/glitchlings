from enum import IntEnum, auto
from datasets import Dataset
import random
from typing import Any, Callable

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
        return corrupted

    def corrupt(self, text: str | list[dict]) -> str | list[dict]:
        if isinstance(text, list):
            text[-1]["content"] = self.__corrupt(text[-1]["content"], **self.kwargs)
        else:
            text = self.__corrupt(text, **self.kwargs)

        return text

    def corrupt_dataset(self, dataset: Dataset, columns: list[str]) -> Dataset:
        def __corrupt_row(row):
            for column in columns:
                row[column] = self.corrupt(row[column])
            return row

        dataset = dataset.map(__corrupt_row)

        return dataset

    def __call__(self, text: str, *args, **kwds) -> str | list[dict]:
        return self.corrupt(text, *args, **kwds)

    def reset_rng(self, seed=None):
        """Reset this glitchling's RNG to its initial seed (if one was provided)."""
        if seed is not None:
            self.seed = seed
        if self.seed is not None:
            self.rng = random.Random(self.seed)

    def clone(self, seed=None) -> "Glitchling":
        """Create a copy of this glitchling, optionally with a new seed."""
        # Avoid passing duplicate 'seed' through kwargs if it was set via set_param
        filtered_kwargs = {k: v for k, v in self.kwargs.items() if k != "seed"}
        new_glitchling = Glitchling(
            self.name,
            self.corruption_function,
            self.level,
            self.order,
            seed=seed if seed is not None else self.seed,
            **filtered_kwargs,
        )
        return new_glitchling


class Gaggle(Glitchling):
    def __init__(self, glitchlings: list[Glitchling], seed: int = 151):
        super().__init__("Gaggle", self.corrupt, AttackWave.DOCUMENT, seed=seed)
        self.glitchlings: dict[AttackWave, list[Glitchling]] = {
            level: [] for level in AttackWave
        }
        self.apply_order: list[Glitchling] = []
        # Derive deterministic per-glitchling seeds from master seed if provided
        for idx, g in enumerate(glitchlings):
            _g = g.clone()
            derived_seed = Gaggle.derive_seed(seed, _g.name, idx)
            _g.reset_rng(derived_seed)
            self.glitchlings[g.level].append(_g)
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
            corrupted = glitchling(corrupted)
        return corrupted
