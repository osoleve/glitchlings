"""Shared utilities for DLC integrations."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ..zoo.core import Gaggle, _is_transcript


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


def infer_batch_targets(batch: Any) -> list[str | int] | None:
    """Infer which fields should be glitched from a representative batch.
    
    Args:
        batch: A batch from a DataLoader (mapping, sequence, or textual value).
    
    Returns:
        A list of column keys (strings) or indices (ints), or None if the batch
        itself is textual content.
    
    Raises:
        ValueError: If unable to infer textual columns/indices.
        TypeError: If the batch type is unsupported.
    """
    if isinstance(batch, Mapping):
        inferred = [key for key, value in batch.items() if is_textual_candidate(value)]
        if inferred:
            return inferred
        raise ValueError("Unable to infer which mapping columns contain text")

    if isinstance(batch, Sequence) and not isinstance(batch, (bytes, bytearray, str)):
        inferred_indices: list[str | int] = [
            idx for idx, value in enumerate(batch) if is_textual_candidate(value)
        ]
        if inferred_indices:
            return inferred_indices
        raise ValueError("Unable to infer which sequence indices contain text")

    if is_textual_candidate(batch):
        return None

    raise TypeError("Unsupported DataLoader batch type for glitching")


def corrupt_batch(batch: Any, targets: list[str | int] | None, gaggle: Gaggle) -> Any:
    """Return batch with glitchlings applied to the specified targets.
    
    Args:
        batch: The batch to corrupt (mapping, sequence, or textual value).
        targets: List of column keys (strings) or indices (ints), or None to
                 corrupt the entire batch as textual content.
        gaggle: The gaggle of glitchlings to apply.
    
    Returns:
        The corrupted batch, preserving the original type.
    
    Raises:
        TypeError: If batch type is unsupported or targets are incompatible.
        ValueError: If a specified target is not found in the batch.
    """
    if targets is None:
        return corrupt_text_value(batch, gaggle)

    if isinstance(batch, Mapping):
        # Use copy() if available, otherwise dict()
        if hasattr(batch, "copy"):
            mutated = batch.copy()
        else:
            mutated = dict(batch)
        
        for key in targets:
            if not isinstance(key, str):
                raise TypeError("Mapping batches require string column names")
            if key not in mutated:
                raise ValueError(f"Column '{key}' not found in DataLoader batch")
            mutated[key] = corrupt_text_value(mutated[key], gaggle)
        return mutated

    if isinstance(batch, Sequence) and not isinstance(batch, (bytes, bytearray, str)):
        mutated_sequence = list(batch)
        for index in targets:
            if not isinstance(index, int):
                raise TypeError("Sequence batches require integer column indices")
            try:
                mutated_sequence[index] = corrupt_text_value(mutated_sequence[index], gaggle)
            except IndexError as exc:  # pragma: no cover - defensive
                raise IndexError("Column index out of range for DataLoader batch") from exc
        if isinstance(batch, tuple):
            return tuple(mutated_sequence)
        return mutated_sequence

    raise TypeError("Unsupported DataLoader batch type for glitching")


class BaseGlitchedDataLoader:
    """Proxy dataloader that glitches batches produced by the wrapped loader.
    
    This class wraps a dataloader and applies glitchlings to specified columns
    in each batch as it's yielded. It supports both mapping-based batches (dict-like)
    and sequence-based batches (list/tuple-like).
    """

    def __init__(self, dataloader: Any, columns: list[str | int], gaggle: Gaggle) -> None:
        """Initialize the glitched dataloader.
        
        Args:
            dataloader: The underlying dataloader to wrap.
            columns: List of column names (strings) or indices (ints) to corrupt.
            gaggle: The gaggle of glitchlings to apply.
        """
        self._dataloader = dataloader
        self._columns = columns
        self._gaggle = gaggle

    def __iter__(self) -> Any:
        """Yield corrupted batches from the underlying dataloader."""
        for batch in self._dataloader:
            yield corrupt_batch(batch, self._columns, self._gaggle)

    def __len__(self) -> int:
        """Return the number of batches in the dataloader."""
        return len(self._dataloader)

    def __getattr__(self, attribute: str) -> Any:
        """Proxy attribute access to the underlying dataloader."""
        return getattr(self._dataloader, attribute)


def wrap_dataloader(
    dataloader: Any, columns: list[str | int], gaggle: Gaggle
) -> Any:
    """Wrap a dataloader (or nested structure) to apply glitchlings lazily.
    
    This function recursively wraps dataloaders in nested structures (mappings,
    lists, tuples, etc.) so that all dataloaders in the structure will yield
    corrupted batches.
    
    Args:
        dataloader: The dataloader or nested structure to wrap.
        columns: List of column names (strings) or indices (ints) to corrupt.
        gaggle: The gaggle of glitchlings to apply.
    
    Returns:
        The wrapped dataloader or structure, with the same type as the input.
    """
    if dataloader is None:
        return None

    if isinstance(dataloader, Mapping):
        mapping_type = type(dataloader)
        return mapping_type(
            {key: wrap_dataloader(value, columns, gaggle) for key, value in dataloader.items()}
        )

    if isinstance(dataloader, list):
        return [wrap_dataloader(value, columns, gaggle) for value in dataloader]

    if isinstance(dataloader, tuple):
        return tuple(wrap_dataloader(value, columns, gaggle) for value in dataloader)

    if isinstance(dataloader, Sequence) and not isinstance(dataloader, (str, bytes, bytearray)):
        sequence_type = type(dataloader)
        return sequence_type(wrap_dataloader(value, columns, gaggle) for value in dataloader)

    return BaseGlitchedDataLoader(dataloader, columns, gaggle)


__all__ = [
    "BaseGlitchedDataLoader",
    "corrupt_batch",
    "corrupt_text_value",
    "infer_batch_targets",
    "is_textual_candidate",
    "normalize_column_spec",
    "resolve_columns",
    "wrap_dataloader",
]
