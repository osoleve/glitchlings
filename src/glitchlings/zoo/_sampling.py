from __future__ import annotations

import random
from typing import Sequence


def weighted_sample_without_replacement(
    population: Sequence[int],
    weights: Sequence[float],
    *,
    k: int,
    rng: random.Random,
) -> list[int]:
    """Sample ``k`` unique indices from ``population`` using ``weights``.

    Mirrors the behaviour used by several glitchlings while centralising error
    handling and RNG interactions so the Python and Rust implementations remain
    aligned.
    """
    if k < 0:
        raise ValueError("Sample size cannot be negative")

    if len(population) != len(weights):
        raise ValueError("Population and weight sequences must be the same length")

    items = list(zip(population, weights))
    count = len(items)
    if k == 0 or count == 0:
        return []

    if k > count:
        raise ValueError("Sample larger than population or is negative")

    selections: list[int] = []
    for _ in range(k):
        total_weight = sum(weight for _, weight in items)
        if total_weight <= 0.0:
            chosen_index = rng.randrange(len(items))
        else:
            threshold = rng.random() * total_weight
            cumulative = 0.0
            chosen_index = len(items) - 1
            for idx, (_, weight) in enumerate(items):
                cumulative += weight
                if cumulative >= threshold:
                    chosen_index = idx
                    break
        value, _ = items.pop(chosen_index)
        selections.append(value)

    return selections


__all__ = ["weighted_sample_without_replacement"]
