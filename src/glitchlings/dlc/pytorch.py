"""Integration helpers for PyTorch data loaders."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, cast

from ..compat import get_torch_dataloader, require_torch
from ..compat import torch as _torch_dependency
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


def _ensure_dataloader_class() -> type[Any]:
    """Return :class:`torch.utils.data.DataLoader` patched with ``.glitch``."""
    dataloader_cls = get_torch_dataloader()
    if dataloader_cls is None:
        require_torch("torch is not installed; install glitchlings[torch]")
        dataloader_cls = get_torch_dataloader()
        if dataloader_cls is None:  # pragma: no cover - defensive
            message = "torch.utils.data.DataLoader is not available"
            error = _torch_dependency.error
            if error is not None:
                raise ModuleNotFoundError(message) from error
            raise ModuleNotFoundError(message)

    if getattr(dataloader_cls, "glitch", None) is None:

        def glitch(
            self: Any,
            glitchlings: Iterable[str | Glitchling] | Glitchling | str | Gaggle,
            *,
            columns: str | int | Sequence[str | int] | None = None,
            seed: int = 151,
        ) -> _GlitchedDataLoader:
            """Return a lazily glitched view of the loader's batches."""
            gaggle = coerce_gaggle(glitchlings, seed=seed)
            normalized = normalize_column_spec(columns)
            return _GlitchedDataLoader(self, gaggle, columns=normalized)

        setattr(dataloader_cls, "glitch", glitch)

    return cast(type[Any], dataloader_cls)


def _optional_dataloader_class() -> type[Any] | None:
    """Return the PyTorch :class:`~torch.utils.data.DataLoader` when importable."""
    dataloader_cls = get_torch_dataloader()
    if dataloader_cls is None:
        return None
    return cast(type[Any], dataloader_cls)


def install() -> None:
    """Monkeypatch PyTorch's :class:`~torch.utils.data.DataLoader` with ``.glitch``."""
    _ensure_dataloader_class()


DataLoader: type[Any] | None
_DataLoaderAlias = _optional_dataloader_class()
if _DataLoaderAlias is not None:
    DataLoader = _ensure_dataloader_class()
else:  # pragma: no cover - torch is an optional dependency
    DataLoader = None


__all__ = ["DataLoader", "install"]
