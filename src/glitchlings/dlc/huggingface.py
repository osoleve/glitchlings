"""Integration helpers for the Hugging Face datasets library."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling


def _normalize_columns(column: str | Sequence[str]) -> list[str]:
    """Normalize a column specification to a list."""
    if isinstance(column, str):
        return [column]

    normalized = list(column)
    if not normalized:
        raise ValueError("At least one column must be specified")
    return normalized


def _glitch_dataset(
    dataset: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    column: str | Sequence[str],
    *,
    seed: int = 151,
) -> Any:
    """Apply glitchlings to the provided dataset columns."""
    columns = _normalize_columns(column)
    gaggle = coerce_gaggle(glitchlings, seed=seed)
    return gaggle.corrupt_dataset(dataset, columns)


def GlitchedDataset(
    dataset: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    *,
    column: str | Sequence[str],
    seed: int = 151,
) -> Any:
    """Return a lazily corrupted copy of a Hugging Face dataset.
    
    This function applies glitchlings to the specified columns of a dataset,
    returning a new dataset that lazily corrupts data as it's accessed.
    
    Args:
        dataset: The Hugging Face Dataset to corrupt.
        glitchlings: A glitchling, gaggle, or specification of glitchlings to apply.
        column: The column name (string) or names (sequence of strings) to corrupt.
        seed: RNG seed for deterministic corruption (default: 151).
    
    Returns:
        A new dataset with the specified columns corrupted by the glitchlings.
    
    Example:
        >>> from datasets import Dataset
        >>> from glitchlings.dlc.huggingface import GlitchedDataset
        >>> dataset = Dataset.from_dict({"text": ["hello", "world"]})
        >>> corrupted = GlitchedDataset(dataset, "typogre", column="text")
        >>> list(corrupted)
        [{'text': 'helo'}, {'text': 'wrold'}]
    """
    return _glitch_dataset(dataset, glitchlings, column, seed=seed)


__all__ = ["GlitchedDataset"]
