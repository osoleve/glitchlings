"""Shared utilities for DLC integrations."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ..zoo.core import Gaggle, _is_transcript


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


def normalize_column_spec(
    columns: str | int | Sequence[str | int] | None,
) -> list[str | int] | None:
    """Normalize a column specification into a list of keys or indices.

    Args:
        columns: Column specification as a single value, sequence of values, or None.

    Returns:
        A list of column identifiers, or None if input was None.

    Raises:
        ValueError: If an empty sequence is provided.
    """
    if columns is None:
        return None

    if isinstance(columns, (str, int)):
        return [columns]

    normalized = list(columns)
    if not normalized:
        raise ValueError("At least one column must be specified")
    return normalized


def is_textual_candidate(value: Any) -> bool:
    """Return ``True`` when ``value`` looks like text that glitchlings can corrupt.

    Args:
        value: The value to check for textual content.

    Returns:
        True if the value appears to be textual content.
    """
    if isinstance(value, str):
        return True

    if _is_transcript(value, allow_empty=False, require_all_content=True):
        return True

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        if not value:
            return False
        if all(isinstance(item, str) for item in value):
            return True
        if _is_transcript(list(value), allow_empty=False, require_all_content=True):
            return True

    return False


def corrupt_text_value(value: Any, gaggle: Gaggle) -> Any:
    """Return ``value`` with glitchlings applied when possible.

    Args:
        value: The value to corrupt (string, transcript, or sequence of strings).
        gaggle: The gaggle of glitchlings to apply.

    Returns:
        The corrupted value, preserving the original type where possible.
    """
    if isinstance(value, str):
        return gaggle.corrupt(value)

    if _is_transcript(value, allow_empty=True):
        return gaggle.corrupt(value)

    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return [gaggle.corrupt(item) for item in value]

    if isinstance(value, tuple) and value and all(isinstance(item, str) for item in value):
        return tuple(gaggle.corrupt(item) for item in value)

    return value


__all__ = [
    "corrupt_text_value",
    "is_textual_candidate",
    "normalize_column_spec",
    "resolve_columns",
    "resolve_environment",
]
