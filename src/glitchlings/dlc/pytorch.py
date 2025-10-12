"""Integration helpers for PyTorch data loaders."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Iterator

from ..compat import optional_import
from ..zoo import Gaggle, Glitchling, _is_transcript, summon


_TORCH_DATALOADER = optional_import(
    "torch.utils.data",
    "DataLoader",
    friendly_name="torch",
)

def _normalise_columns(column: str | Sequence[str]) -> list[str]:
    """Normalise a column specification to a list."""

    if isinstance(column, str):
        return [column]

    normalised = list(column)
    if not normalised:
        raise ValueError("At least one column must be specified")
    return normalised


def _as_gaggle(
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
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


def _corrupt_sequence(sequence: Sequence[Any], gaggle: Gaggle) -> Sequence[Any]:
    """Return a corrupted copy of a sequence while preserving its type."""

    if isinstance(sequence, tuple):
        return tuple(_corrupt_value(item, gaggle) for item in sequence)

    if isinstance(sequence, list):
        return [_corrupt_value(item, gaggle) for item in sequence]

    try:
        return sequence.__class__(_corrupt_value(item, gaggle) for item in sequence)
    except TypeError:
        return [_corrupt_value(item, gaggle) for item in sequence]


def _corrupt_mapping(mapping: Mapping[str, Any], columns: list[str], gaggle: Gaggle) -> dict[str, Any]:
    """Return a corrupted copy of a mapping for the selected columns."""

    corrupted = dict(mapping)
    for column in columns:
        if column not in corrupted:
            missing = ", ".join(columns)
            message = f"Batch is missing required column(s): {missing}"
            raise KeyError(message)
        corrupted[column] = _corrupt_value(corrupted[column], gaggle)
    return corrupted


def _corrupt_value(value: Any, gaggle: Gaggle) -> Any:
    """Apply corruption to text-like structures contained in a batch value."""

    if isinstance(value, str):
        return gaggle.corrupt(value)

    if _is_transcript(value, allow_empty=False, require_all_content=True):
        return gaggle.corrupt(value)

    if isinstance(value, Mapping):
        return {key: _corrupt_value(inner, gaggle) for key, inner in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return _corrupt_sequence(value, gaggle)

    return value


class _GlitchedDataLoader:
    """Proxy object yielding corrupted batches from a PyTorch dataloader."""

    def __init__(self, dataloader: Any, gaggle: Gaggle, columns: list[str]):
        self._dataloader = dataloader
        self._gaggle = gaggle
        self._columns = columns

    def __iter__(self) -> Iterator[Any]:
        for batch in self._dataloader:
            if isinstance(batch, Mapping):
                yield _corrupt_mapping(batch, self._columns, self._gaggle)
            else:
                message = "Batches must be mappings to apply glitch corruption"
                raise TypeError(message)

    def __len__(self) -> int:  # pragma: no cover - delegating to dataloader
        return len(self._dataloader)

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - delegation only
        return getattr(self._dataloader, name)


def _glitch_dataloader(
    dataloader: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    column: str | Sequence[str],
    *,
    seed: int = 151,
) -> _GlitchedDataLoader:
    """Return a wrapper yielding corrupted batches from the dataloader."""

    columns = _normalise_columns(column)
    gaggle = _as_gaggle(glitchlings, seed=seed)
    return _GlitchedDataLoader(dataloader, gaggle, columns)


def _ensure_dataloader_class() -> Any:
    """Return the PyTorch :class:`~torch.utils.data.DataLoader` with ``.glitch``."""

    dataloader_cls = _TORCH_DATALOADER.require()

    if getattr(dataloader_cls, "glitch", None) is None:

        def glitch(  # type: ignore[override]
            self: Any,
            glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
            *,
            column: str | Sequence[str],
            seed: int = 151,
            **_: Any,
        ) -> _GlitchedDataLoader:
            """Return a wrapper over this dataloader yielding corrupted batches."""

            return _glitch_dataloader(self, glitchlings, column, seed=seed)

        setattr(dataloader_cls, "glitch", glitch)

    return dataloader_cls


def install() -> None:
    """Monkeypatch PyTorch's :class:`~torch.utils.data.DataLoader` with ``.glitch``."""

    _ensure_dataloader_class()


if _TORCH_DATALOADER.is_available():
    DataLoader = _ensure_dataloader_class()
else:  # pragma: no cover - torch is an install-time dependency
    DataLoader = None  # type: ignore[assignment]


__all__ = ["DataLoader", "install"]
