"""Integration helpers for the optional verifiers prime DLC."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import Enum
from typing import Any, Callable

import verifiers as vf

from jellyfish import damerau_levenshtein_distance

try:
    from .huggingface import Dataset
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Dataset = object  # type: ignore[assignment]
else:
    if Dataset is None:  # pragma: no cover - optional dependency
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

    tuned_mim1c = Mim1c(rate=0.01 * difficulty.value)
    tuned_typogre = Typogre(rate=0.025 * difficulty.value)

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


def _as_gaggle(
    glitchlings: Iterable[str | Glitchling] | Glitchling | str | Gaggle,
    *,
    seed: int,
) -> Gaggle:
    """Coerce any supported glitchling specification into a :class:`Gaggle`."""

    if isinstance(glitchlings, Gaggle):
        return glitchlings

    if isinstance(glitchlings, (Glitchling, str)):
        resolved: Iterable[str | Glitchling] = [glitchlings]
    else:
        resolved = glitchlings

    return summon(list(resolved), seed=seed)


def _extract_completion_text(completion: Any) -> str:
    """Normalise a completion payload into a plain string."""

    if isinstance(completion, str):
        return completion

    if isinstance(completion, list) and completion:
        first = completion[0]
        if isinstance(first, dict) and "content" in first:
            return str(first["content"])
        return str(first)

    return str(completion)


def symmetric_damerau_levenshtein_similarity(
    _: Any,
    completion: Any,
    answer: str,
) -> float:
    """Return ``1 - (distance / max_len)`` using Damerau-Levenshtein distance."""

    completion_text = _extract_completion_text(completion)
    target = answer or ""
    denominator = max(len(completion_text), len(target), 1)
    distance = damerau_levenshtein_distance(completion_text, target)
    score = 1.0 - (distance / denominator)
    return max(0.0, min(1.0, score))


DEFAULT_CLEANUP_INSTRUCTIONS = (
    "You are a meticulous copy editor. Restore the provided text to its original form."
)


def echo_chamber(
    dataset_id: str,
    column: str,
    glitchlings: Iterable[str | Glitchling] | Glitchling | str | Gaggle,
    *,
    seed: int = 151,
    instructions: str = DEFAULT_CLEANUP_INSTRUCTIONS,
    reward_function: Callable[..., float] | None = None,
    split: str | None = None,
    **load_dataset_kwargs: Any,
) -> vf.Environment:
    """Create an Echo Chamber Prime environment from a Hugging Face dataset column.

    Args:
        dataset_id: Identifier of the Hugging Face dataset to load.
        column: Name of the column whose text should be glitched.
        glitchlings: Glitchling specifiers that will corrupt the prompts.
        seed: RNG seed forwarded to :func:`summon`.
        instructions: System instructions supplied to the environment prompts.
        reward_function: Optional callable used to score completions. Defaults to
            :func:`symmetric_damerau_levenshtein_similarity` when omitted.
        split: Optional dataset split to load.
        **load_dataset_kwargs: Extra keyword arguments forwarded to
            :func:`datasets.load_dataset`.
    """

    try:
        from datasets import Dataset as HFDataset, DatasetDict, load_dataset
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        message = "datasets is required to build an echo chamber"
        raise ModuleNotFoundError(message) from exc

    hf_dataset: HFDataset | DatasetDict
    if split is None:
        hf_dataset = load_dataset(dataset_id, **load_dataset_kwargs)
        if isinstance(hf_dataset, DatasetDict):
            try:
                hf_dataset = next(iter(hf_dataset.values()))
            except StopIteration as exc:  # pragma: no cover - defensive
                raise ValueError("The specified dataset does not contain any splits") from exc
    else:
        hf_dataset = load_dataset(dataset_id, split=split, **load_dataset_kwargs)

    if isinstance(hf_dataset, DatasetDict):
        raise ValueError(
            "Specify which split to use when the dataset loads as a DatasetDict."
        )

    prompts: list[list[dict[str, str]]] = []
    answers: list[str] = []

    for row in hf_dataset:
        value = row.get(column)
        if value is None:
            continue

        text = str(value)
        prompts.append(
            [
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Corrupted text:\n{text}"},
            ]
        )
        answers.append(text)

    if not prompts:
        raise ValueError(
            f"Column '{column}' did not yield any textual entries in dataset '{dataset_id}'."
        )

    dataset = HFDataset.from_dict({"prompt": prompts, "answer": answers})

    gaggle = _as_gaggle(glitchlings, seed=seed)
    glitched_dataset = gaggle.corrupt_dataset(dataset, ["prompt"])

    rubric_func = reward_function or symmetric_damerau_levenshtein_similarity
    rubric = vf.Rubric(funcs=[rubric_func], weights=[1.0])
    return vf.SingleTurnEnv(dataset=glitched_dataset, rubric=rubric)
