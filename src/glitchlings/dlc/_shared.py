"""Shared utilities for DLC integrations."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


def resolve_environment(
    env: Any,
    *,
    loader: Callable[[str], Any],
    environment_type: type[Any],
) -> Any:
    """Return a fully-instantiated verifier environment."""
    if isinstance(env, str):
        env = loader(env)

    if not isinstance(env, environment_type):
        raise TypeError("Invalid environment type")

    return env


def resolve_columns(dataset: Any, columns: Sequence[str] | None) -> list[str]:
    """Identify which dataset columns should be corrupted."""
    available = set(getattr(dataset, "column_names", ()))

    if columns is not None:
        missing = sorted(set(columns) - available)
        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"Columns not found in dataset: {missing_str}")
        return list(columns)

    for candidate in ("prompt", "question"):
        if candidate in available:
            return [candidate]

    try:
        dataset_length = len(dataset)
    except TypeError:
        preview_rows: list[dict[str, Any]]
        take_fn = getattr(dataset, "take", None)
        if callable(take_fn):
            preview_rows = list(take_fn(1))
        else:
            iterator = iter(dataset)
            try:
                first_row = next(iterator)
            except StopIteration:
                preview_rows = []
            else:
                preview_rows = [first_row]
        sample = dict(preview_rows[0]) if preview_rows else {}
    else:
        sample = dataset[0] if dataset_length else {}
    inferred = [
        name for name in getattr(dataset, "column_names", ()) if isinstance(sample.get(name), str)
    ]

    if inferred:
        return inferred

    raise ValueError("Unable to determine which dataset columns to corrupt.")


__all__ = ["resolve_columns", "resolve_environment"]
