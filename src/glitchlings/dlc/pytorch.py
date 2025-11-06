"""Integration helpers for PyTorch data loaders."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, cast

from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling
from ._shared import corrupt_batch, infer_batch_targets, normalize_column_spec


class _GlitchedDataLoader(Iterable[Any]):
    """Wrapper that applies glitchlings lazily to each batch from a data loader."""

    def __init__(
        self,
        dataloader: Any,
        gaggle: Gaggle,
        *,
        columns: list[str | int] | None,
    ) -> None:
        self._dataloader = dataloader
        self._gaggle = gaggle
        self._explicit_columns = columns
        self._inferred_columns: list[str | int] | None | _Sentinel = _UNINITIALISED

    def __iter__(self) -> Iterator[Any]:
        # Reset all glitchling RNGs before each fresh pass for determinism.
        self._gaggle.sort_glitchlings()
        for batch in self._dataloader:
            targets = self._resolve_columns(batch)
            yield corrupt_batch(batch, targets, self._gaggle)

    def __len__(self) -> int:
        return len(self._dataloader)

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._dataloader, attribute)

    def _resolve_columns(self, batch: Any) -> list[str | int] | None:
        if self._explicit_columns is not None:
            return self._explicit_columns

        if self._inferred_columns is _UNINITIALISED:
            self._inferred_columns = infer_batch_targets(batch)

        return cast(list[str | int] | None, self._inferred_columns)


class _Sentinel:
    """Sentinel type for deferred column inference."""


_UNINITIALISED = _Sentinel()


def GlitchedDataLoader(
    dataloader: Any,
    glitchlings: Iterable[str | Glitchling] | Glitchling | str | Gaggle,
    *,
    columns: str | int | Sequence[str | int] | None = None,
    seed: int = 151,
) -> _GlitchedDataLoader:
    """Return a lazily glitched view of a PyTorch DataLoader's batches.
    
    This function wraps a PyTorch DataLoader to apply glitchlings to specified
    columns (or auto-inferred text columns) in each batch as it's yielded.
    
    Args:
        dataloader: The PyTorch DataLoader to wrap.
        glitchlings: A glitchling, gaggle, or specification of glitchlings to apply.
        columns: Column name(s) or index/indices to corrupt. Can be:
                 - A single string column name (for dict-like batches)
                 - A single integer index (for sequence-like batches)
                 - A sequence of column names or indices
                 - None to auto-infer text columns (default)
        seed: RNG seed for deterministic corruption (default: 151).
    
    Returns:
        A wrapped dataloader that yields corrupted batches.
    
    Example:
        >>> from torch.utils.data import DataLoader
        >>> from glitchlings.dlc.pytorch import GlitchedDataLoader
        >>> dataset = [{"text": "hello", "label": 0}]
        >>> loader = DataLoader(dataset)
        >>> glitched = GlitchedDataLoader(loader, "typogre", columns="text")
        >>> for batch in glitched:
        ...     print(batch)
        {'text': 'helo', 'label': 0}
    """
    gaggle = coerce_gaggle(glitchlings, seed=seed)
    normalized = normalize_column_spec(columns)
    return _GlitchedDataLoader(dataloader, gaggle, columns=normalized)


__all__ = ["GlitchedDataLoader"]
