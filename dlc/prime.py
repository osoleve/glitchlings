from enum import Enum
import functools as ft

import verifiers as vf
from datasets import Dataset

from zoo import Glitchling, Gaggle, mim1c, typogre, summon


class CR(Enum):
    """Challenge Rating levels for tutorial environments."""

    Zero = 0.1
    Half = 0.5
    One = 1
    Two = 1.5
    Three = 4
    Four = 9


def tutorial_level(
    env: vf.Environment | str, seed=151, CR: CR = CR.One
) -> vf.Environment:
    """Create a low-corruption environment."""

    mim1c.set_param("replacement_rate", 0.01 * CR.value)
    typogre.set_param("max_change_rate", 0.025 * CR.value)

    glitchlings: Gaggle = summon([mim1c, typogre], seed=seed)

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
    env: str | vf.Environment, seed=151, CR: CR = CR.One, loader=tutorial_level
) -> vf.Environment:
    """Load an environment by name."""
    return loader(env, seed=seed, CR=CR)
