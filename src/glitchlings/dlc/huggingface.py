"""Integration helpers for the Hugging Face datasets library."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from ..compat import datasets, get_datasets_dataset, require_datasets
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


def _ensure_dataset_class() -> Any:
    """Return the Hugging Face :class:`~datasets.Dataset` patched with ``.glitch``."""
    dataset_cls = get_datasets_dataset()
    if dataset_cls is None:  # pragma: no cover - datasets is an install-time dependency
        require_datasets("datasets is not installed")
        dataset_cls = get_datasets_dataset()
        if dataset_cls is None:
            message = "datasets is not installed"
            error = datasets.error
            if error is not None:
                raise ModuleNotFoundError(message) from error
            raise ModuleNotFoundError(message)

    if getattr(dataset_cls, "glitch", None) is None:

        def glitch(
            self: Any,
            glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
            *,
            column: str | Sequence[str],
            seed: int = 151,
            **_: Any,
        ) -> Any:
            """Return a lazily corrupted copy of the dataset."""
            return _glitch_dataset(self, glitchlings, column, seed=seed)

        setattr(dataset_cls, "glitch", glitch)

    return cast(type[Any], dataset_cls)


def install() -> None:
    """Monkeypatch the Hugging Face :class:`~datasets.Dataset` with ``.glitch``."""
    _ensure_dataset_class()


Dataset: type[Any] | None
_DatasetAlias = get_datasets_dataset()
if _DatasetAlias is not None:
    Dataset = _ensure_dataset_class()
else:  # pragma: no cover - datasets is an install-time dependency
    Dataset = None


__all__ = ["Dataset", "GlitchedDataset", "install"]
