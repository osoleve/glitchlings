"""Integration helpers for the Hugging Face datasets library."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..compat import datasets, get_datasets_dataset, require_datasets
from ..zoo import Gaggle, Glitchling, summon


_DATASETS_DATASET = optional_import(
    "datasets",
    "Dataset",
    friendly_name="datasets",
)


def _normalise_columns(column: str | Sequence[str]) -> list[str]:
    """Normalise a column specification to a list."""

    if isinstance(column, str):
        return [column]

    normalised = list(column)
    if not normalised:
        raise ValueError("At least one column must be specified")
    return normalised


def _as_gaggle(glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling], seed: int) -> Gaggle:
    """Coerce any supported glitchling specification into a :class:`Gaggle`."""

    if isinstance(glitchlings, Gaggle):
        return glitchlings

    if isinstance(glitchlings, (Glitchling, str)):
        resolved: Iterable[str | Glitchling] = [glitchlings]
    else:
        resolved = glitchlings

    return summon(list(resolved), seed=seed)


def _glitch_dataset(
    dataset: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    column: str | Sequence[str],
    *,
    seed: int = 151,
) -> Any:
    """Internal helper implementing :meth:`Dataset.glitch`."""

    columns = _normalise_columns(column)
    gaggle = _as_gaggle(glitchlings, seed=seed)
    return gaggle.corrupt_dataset(dataset, columns)


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

        def glitch(  # type: ignore[override]
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

    return dataset_cls


def install() -> None:
    """Monkeypatch the Hugging Face :class:`~datasets.Dataset` with ``.glitch``."""

    _ensure_dataset_class()


_DatasetAlias = get_datasets_dataset()
if _DatasetAlias is not None:
    Dataset = _ensure_dataset_class()
else:  # pragma: no cover - datasets is an install-time dependency
    Dataset = None  # type: ignore[assignment]


__all__ = ["Dataset", "install"]
