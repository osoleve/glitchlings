"""Integration helpers for PyTorch Lightning data modules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, cast

from ..compat import get_pytorch_lightning_datamodule
from ..util.adapters import coerce_gaggle
from ..zoo import Gaggle, Glitchling
from ._shared import normalize_column_spec, wrap_dataloader


def _glitch_datamodule(
    datamodule: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    column: str | Sequence[str],
    *,
    seed: int = 151,
) -> Any:
    """Return a proxy that applies glitchlings to batches from the datamodule."""

    columns = normalize_column_spec(column)
    if columns is None:  # pragma: no cover - defensive
        raise ValueError("At least one column must be specified")
    # Lightning datamodules only support string column names (mapping keys)
    columns_str = cast(list[str], columns)
    gaggle = coerce_gaggle(glitchlings, seed=seed)
    
    # Ensure _GlitchedLightningDataModule inherits from LightningDataModule
    _ensure_inheritance()
    
    return _GlitchedLightningDataModule(datamodule, columns_str, gaggle)


def GlitchedLightningDataModule(
    datamodule: Any,
    glitchlings: Glitchling | Gaggle | str | Iterable[str | Glitchling],
    *,
    column: str | Sequence[str],
    seed: int = 151,
) -> Any:
    """Return a glitched wrapper around a PyTorch Lightning LightningDataModule.
    
    This function wraps a LightningDataModule to apply glitchlings to specified
    columns in batches yielded by the module's dataloaders.
    
    Args:
        datamodule: The LightningDataModule to wrap.
        glitchlings: A glitchling, gaggle, or specification of glitchlings to apply.
        column: The column name (string) or names (sequence of strings) to corrupt.
        seed: RNG seed for deterministic corruption (default: 151).
    
    Returns:
        A wrapped datamodule that yields corrupted batches from its dataloaders.
    
    Example:
        >>> from pytorch_lightning import LightningDataModule
        >>> from glitchlings.dlc.pytorch_lightning import GlitchedLightningDataModule
        >>> class MyDataModule(LightningDataModule):
        ...     def train_dataloader(self):
        ...         return [{"text": "hello", "label": 0}]
        >>> dm = MyDataModule()
        >>> glitched = GlitchedLightningDataModule(dm, "typogre", column="text")
        >>> batches = list(glitched.train_dataloader())
    """
    return _glitch_datamodule(datamodule, glitchlings, column, seed=seed)


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
        return wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def val_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.val_dataloader(*args, **kwargs)
        return wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def test_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.test_dataloader(*args, **kwargs)
        return wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)

    def predict_dataloader(self, *args: Any, **kwargs: Any) -> Any:
        loader = self._glitch_base.predict_dataloader(*args, **kwargs)
        return wrap_dataloader(loader, self._glitch_columns, self._glitch_gaggle)


def _ensure_inheritance() -> None:
    """Ensure _GlitchedLightningDataModule inherits from LightningDataModule.
    
    This function dynamically sets the base class of _GlitchedLightningDataModule
    to inherit from pytorch_lightning.LightningDataModule when available. This
    ensures that isinstance(glitched, LightningDataModule) checks work correctly
    and that the wrapper interoperates with Lightning APIs that require that type.
    """
    datamodule_cls = get_pytorch_lightning_datamodule()
    if datamodule_cls is None:
        # If LightningDataModule is not available, keep as plain object
        return
    
    # Check if we've already set up inheritance
    if issubclass(_GlitchedLightningDataModule, datamodule_cls):
        return
    
    # Try to dynamically set __bases__ to inherit from LightningDataModule
    try:
        _GlitchedLightningDataModule.__bases__ = (datamodule_cls,)
    except TypeError:
        # If we can't modify __bases__ (e.g., due to __slots__), create a new class
        namespace = {
            name: value
            for name, value in vars(_GlitchedLightningDataModule).items()
            if name not in {"__dict__", "__weakref__"}
        }
        replacement = cast(
            type[Any],
            type("_GlitchedLightningDataModule", (datamodule_cls,), namespace),
        )
        # Update the module's global namespace
        globals()["_GlitchedLightningDataModule"] = replacement


__all__ = ["GlitchedLightningDataModule"]
