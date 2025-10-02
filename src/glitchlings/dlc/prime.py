"""Integration helpers for the optional verifiers prime DLC."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import Enum

import verifiers as vf

try:
    from datasets import Dataset
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Dataset = object  # type: ignore[assignment]

from ..zoo import Gaggle, Glitchling, Mim1c, Typogre, summon


def _resolve_environment(env: str | vf.Environment) -> vf.Environment:
    """Return a fully-instantiated verifier environment."""

    if isinstance(env, str):
        env = vf.load_environment(env)

    if not isinstance(env, vf.Environment):
        raise TypeError("Invalid environment type")

    return env


def _resolve_columns(dataset: Dataset, columns: Sequence[str] | None) -> list[str]:
    """Identify which dataset columns should be corrupted."""

    available = set(dataset.column_names)

    if columns is not None:
        missing = sorted(set(columns) - available)
        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"Columns not found in dataset: {missing_str}")
        return list(columns)

    for candidate in ("prompt", "question"):
        if candidate in available:
            return [candidate]

    sample = dataset[0] if len(dataset) else {}
    inferred = [
        name
        for name in dataset.column_names
        if isinstance(sample.get(name), str)
    ]

    if inferred:
        return inferred

    raise ValueError("Unable to determine which dataset columns to corrupt.")


class Difficulty(Enum):
    """Difficulty levels for tutorial environments."""

    Easy = 0.25
    Normal = 1.0
    Hard = 1.75
    Extreme = 3
    Impossible = 9


def tutorial_level(
    env: vf.Environment | str,
    seed: int = 151,
    difficulty: Difficulty = Difficulty.Normal,
) -> vf.Environment:
    """Create a low-corruption environment using tuned defaults."""

    tuned_mim1c = Mim1c(replacement_rate=0.01 * difficulty.value)
    tuned_typogre = Typogre(max_change_rate=0.025 * difficulty.value)

    return load_environment(
        env,
        glitchlings=[tuned_mim1c, tuned_typogre],
        seed=seed,
    )


def load_environment(
    env: str | vf.Environment,
    glitchlings: Iterable[str | Glitchling] | Glitchling | str | Gaggle | None = None,
    *,
    seed: int = 151,
    columns: Sequence[str] | None = None,
) -> vf.Environment:
    """Load an environment and optionally corrupt it with glitchlings."""

    environment = _resolve_environment(env)

    if glitchlings is None:
        return environment

    if isinstance(glitchlings, Gaggle):
        gaggle = glitchlings
    else:
        if isinstance(glitchlings, (Glitchling, str)):
            resolved = [glitchlings]
        else:
            resolved = list(glitchlings)

        gaggle = summon(resolved, seed=seed)

    dataset = environment.dataset
    corrupt_columns = _resolve_columns(dataset, columns)
    environment.dataset = gaggle.corrupt_dataset(dataset, corrupt_columns)
    return environment
