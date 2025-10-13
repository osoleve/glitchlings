"""Integration helpers for PyTorch data loaders."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableMapping, Sequence
from typing import Any, cast

from ..compat import get_torch_dataloader, require_torch
from ..compat import torch as _torch_dependency
from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling
from ..zoo.core import _is_transcript


def _normalise_columns(columns: str | int | Sequence[str | int] | None) -> list[str | int] | None:
    """Normalise a column specification into a list of keys or indices."""
    if columns is None:
        return None

    if isinstance(columns, (str, int)):
        return [columns]

    normalised = list(columns)
    if not normalised:
        raise ValueError("At least one column must be specified")
    return normalised


def _is_textual_candidate(value: Any) -> bool:
    """Return ``True`` when ``value`` looks like text that glitchlings can corrupt."""
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


def _corrupt_text(value: Any, gaggle: Gaggle) -> Any:
    """Return ``value`` with glitchlings applied when possible."""
    if isinstance(value, str):
        return gaggle.corrupt(value)

    if _is_transcript(value, allow_empty=True):
        return gaggle.corrupt(value)

    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return [gaggle.corrupt(item) for item in value]

    if isinstance(value, tuple) and value and all(isinstance(item, str) for item in value):
        return tuple(gaggle.corrupt(item) for item in value)

    return value


def _apply_to_batch(batch: Any, targets: list[str | int] | None, gaggle: Gaggle) -> Any:
    """Return ``batch`` with glitchlings applied to the specified ``targets``."""
    if targets is None:
        return _corrupt_text(batch, gaggle)

    if isinstance(batch, Mapping):
        mutated = cast(MutableMapping[str, Any], dict(batch))
        for key in targets:
            if not isinstance(key, str):
                raise TypeError("Mapping batches require string column names")
            if key not in mutated:
                raise ValueError(f"Column '{key}' not found in DataLoader batch")
            mutated[key] = _corrupt_text(mutated[key], gaggle)
        return mutated

    if isinstance(batch, Sequence) and not isinstance(batch, (bytes, bytearray, str)):
        mutated_sequence = list(batch)
        for index in targets:
            if not isinstance(index, int):
                raise TypeError("Sequence batches require integer column indices")
            try:
                mutated_sequence[index] = _corrupt_text(mutated_sequence[index], gaggle)
            except IndexError as exc:  # pragma: no cover - defensive
                raise IndexError("Column index out of range for DataLoader batch") from exc
        if isinstance(batch, tuple):
            return tuple(mutated_sequence)
        return mutated_sequence

    raise TypeError("Unsupported DataLoader batch type for glitching")


def _infer_targets(batch: Any) -> list[str | int] | None:
    """Infer which fields should be glitched from a representative ``batch``."""
    if isinstance(batch, Mapping):
        inferred = [key for key, value in batch.items() if _is_textual_candidate(value)]
        if inferred:
            return inferred
        raise ValueError("Unable to infer which mapping columns contain text")

    if isinstance(batch, Sequence) and not isinstance(batch, (bytes, bytearray, str)):
        inferred_indices: list[str | int] = [
            idx for idx, value in enumerate(batch) if _is_textual_candidate(value)
        ]
        if inferred_indices:
            return inferred_indices
        raise ValueError("Unable to infer which sequence indices contain text")

    if _is_textual_candidate(batch):
        return None

    raise TypeError("Unsupported DataLoader batch type for glitching")


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
            yield _apply_to_batch(batch, targets, self._gaggle)

    def __len__(self) -> int:
        return len(self._dataloader)

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._dataloader, attribute)

    def _resolve_columns(self, batch: Any) -> list[str | int] | None:
        if self._explicit_columns is not None:
            return self._explicit_columns

        if self._inferred_columns is _UNINITIALISED:
            self._inferred_columns = _infer_targets(batch)

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
            normalised = _normalise_columns(columns)
            return _GlitchedDataLoader(self, gaggle, columns=normalised)

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
