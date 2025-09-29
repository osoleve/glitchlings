from enum import Enum
import functools as ft

import verifiers as vf
from datasets import Dataset

from ..zoo import Glitchling, Gaggle, Mim1c, Typogre, summon


class Difficulty(Enum):
    """Difficulty levels for tutorial environments."""

    Easy = 0.25
    Normal = 1.0
    Hard = 1.75
    Extreme = 3
    Impossible = 9


def tutorial_level(
    env: vf.Environment | str, seed=151, difficulty: Difficulty = Difficulty.Normal
) -> vf.Environment:
    """Create a low-corruption environment."""

    tuned_mim1c = Mim1c(replacement_rate=0.01 * difficulty.value)
    tuned_typogre = Typogre(max_change_rate=0.025 * difficulty.value)

    glitchlings: Gaggle = summon([tuned_mim1c, tuned_typogre], seed=seed)

    if isinstance(env, str):
        env = vf.load_environment(env)

    assert isinstance(env, vf.Environment), "Invalid environment type"

    if "prompt" in env.dataset.column_names:
        env.dataset = glitchlings.corrupt_dataset(env.dataset, ["prompt"])
    elif "question" in env.dataset.column_names:
        env.dataset = glitchlings.corrupt_dataset(env.dataset, ["question"])
    else:
        raise ValueError("Can't find prompt or question column")

    return env


def load_environment(
    env: str | vf.Environment,
    seed=151,
    difficulty: Difficulty = Difficulty.Normal,
    loader=tutorial_level,
) -> vf.Environment:
    """Load an environment by name."""
    return loader(env, seed=seed, difficulty=difficulty)
