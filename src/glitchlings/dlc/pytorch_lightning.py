"""Integration helpers for PyTorch Lightning data modules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, cast

from ..compat import get_pytorch_lightning_datamodule, require_pytorch_lightning
from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling
from ._shared import corrupt_text_value, normalise_column_spec


def _glitch_batch(batch: Any, columns: list[str], gaggle: Gaggle) -> Any:
    """Apply glitchlings to the configured batch columns."""
    if not isinstance(batch, Mapping):
        return batch

    if hasattr(batch, "copy"):
        mutated = batch.copy()
    else:
        mutated = dict(batch)

    missing = [column for column in columns if column not in mutated]
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Columns not found in batch: {missing_str}")

    for column in columns:
        mutated[column] = corrupt_text_value(mutated[column], gaggle)

    return mutated


def _wrap_dataloader(dataloader: Any, columns: list[str], gaggle: Gaggle) -> Any:
    """Wrap a dataloader so yielded batches are corrupted lazily."""
    if dataloader is None:
        return None

    if isinstance(dataloader, Mapping):
        mapping_type = cast(type[Any], dataloader.__class__)
        return mapping_type(
            {
                key: _wrap_dataloader(value, columns, gaggle)
                for key, value in dataloader.items()
            }
        )

    if isinstance(dataloader, list):
        return [_wrap_dataloader(value, columns, gaggle) for value in dataloader]

    if isinstance(dataloader, tuple):
        return tuple(_wrap_dataloader(value, columns, gaggle) for value in dataloader)

    if isinstance(dataloader, Sequence) and not isinstance(dataloader, (str, bytes, bytearray)):
        sequence_type = cast(type[Any], dataloader.__class__)
        return sequence_type(
            _wrap_dataloader(value, columns, gaggle) for value in dataloader
        )

    return _GlitchedDataLoader(dataloader, columns, gaggle)


class _GlitchedDataLoader:
    """Proxy dataloader that glitches batches produced by the wrapped loader."""

    def __init__(self, dataloader: Any, columns: list[str], gaggle: Gaggle) -> None:
        self._dataloader = dataloader
        self._columns = columns
        self._gaggle = gaggle

    def __iter__(self) -> Any:
        for batch in self._dataloader:
            yield _glitch_batch(batch, self._columns, self._gaggle)

    def __len__(self) -> int:
        return len(self._dataloader)

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._dataloader, attribute)


def _glitch_datamodule(
    datamodule: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    column: str | Sequence[str],
    *,
    seed: int = 151,
) -> Any:
    """Return a proxy that applies glitchlings to batches from the datamodule."""

    columns = normalise_column_spec(column)
    if columns is None:  # pragma: no cover - defensive
        raise ValueError("At least one column must be specified")
    gaggle = coerce_gaggle(glitchlings, seed=seed)
    return _GlitchedLightningDataModule(datamodule, columns, gaggle)


class _GlitchedLightningDataModule:
    """Proxy wrapper around a LightningDataModule applying glitchlings to batches."""

    def __init__(self, base: Any, columns: list[str], gaggle: Gaggle) -> None:
        object.__setattr__(self, "_glitch_base", base)
        object.__setattr__(self, "_glitch_columns", columns)
        object.__setattr__(self, "_glitch_gaggle", gaggle)

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._glitch_base, attribute)

    def __setattr__(self, attribute: str, value: Any) -> None:
        if attribute.startswith("_glitch_"):
            object.__setattr__(self, attribute, value)
        else:
            setattr(self._glitch_base, attribute, value)

    def __delattr__(self, attribute: str) -> None:
        if attribute.startswith("_glitch_"):
            object.__delattr__(self, attribute)
        else:
            delattr(self._glitch_base, attribute)

    def __dir__(self) -> list[str]:
        return sorted(set(dir(self.__class__)) | set(dir(self._glitch_base)))

    # LightningDataModule API -------------------------------------------------
    def prepare_data(self, *args: Any, **kwargs: Any) -> Any:
        return self._glitch_base.prepare_data(*args, **kwargs)

    def setup(self, *args: Any, **kwargs: Any) -> Any:
        return self._glitch_base.setup(*args, **kwargs)

    def teardown(self, *args: Any, **kwargs: Any) -> Any:
        return self._glitch_base.teardown(*args, **kwargs)

    def state_dict(self) -> Mapping[str, Any]:
        state = self._glitch_base.state_dict()
        return cast(Mapping[str, Any], state)

    def load_state_dict(self, state_dict: Mapping[str, Any]) -> None:
        self._glitch_base.load_state_dict(state_dict)

    def transfer_batch_to_device(self, batch: Any, device: Any, dataloader_idx: int) -> Any:
        return self._glitch_base.transfer_batch_to_device(batch, device, dataloader_idx)

    def on_before_batch_transfer(self, batch: Any, dataloader_idx: int) -> Any:
        return self._glitch_base.on_before_batch_transfer(batch, dataloader_idx)

    def on_after_batch_transfer(self, batch: Any, dataloader_idx: int) -> Any:
        return self._glitch_base.on_after_batch_transfer(batch, dataloader_idx)

    def train_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.train_dataloader(*args, **kwargs)
        return _wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def val_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.val_dataloader(*args, **kwargs)
        return _wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def test_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.test_dataloader(*args, **kwargs)
        return _wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def predict_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.predict_dataloader(*args, **kwargs)
        return _wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)


def _ensure_datamodule_class() -> Any:
    """Return the Lightning ``LightningDataModule`` patched with ``.glitch``."""

    datamodule_cls = get_pytorch_lightning_datamodule()
    if datamodule_cls is None:  # pragma: no cover - dependency is optional
        module = require_pytorch_lightning("pytorch_lightning is not installed")
        datamodule_cls = getattr(module, "LightningDataModule", None)
        if datamodule_cls is None:
            raise ModuleNotFoundError("pytorch_lightning is not installed")

    if getattr(datamodule_cls, "glitch", None) is None:

        def glitch(
            self: Any,
            glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
            *,
            column: str | Sequence[str],
            seed: int = 151,
            **_: Any,
        ) -> Any:
            return _glitch_datamodule(self, glitchlings, column, seed=seed)

        setattr(datamodule_cls, "glitch", glitch)

    if not issubclass(_GlitchedLightningDataModule, datamodule_cls):
        _GlitchedLightningDataModule.__bases__ = (datamodule_cls,)

    return datamodule_cls


def install() -> None:
    """Monkeypatch ``LightningDataModule`` with ``.glitch``."""

    _ensure_datamodule_class()


LightningDataModule: type[Any] | None
_LightningDataModuleAlias = get_pytorch_lightning_datamodule()
if _LightningDataModuleAlias is not None:
    LightningDataModule = _ensure_datamodule_class()
else:  # pragma: no cover - optional dependency
    LightningDataModule = None


__all__ = ["LightningDataModule", "install"]

