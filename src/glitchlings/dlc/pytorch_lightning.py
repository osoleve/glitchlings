"""Integration helpers for PyTorch Lightning data modules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from ..compat import optional_import
from ..zoo import Gaggle, Glitchling
from . import pytorch as torch_dlc


_GLITCHABLE_LOADERS = ("train", "val", "test", "predict")


_LIGHTNING_DATAMODULE = optional_import(
    "pytorch_lightning",
    "LightningDataModule",
    friendly_name="pytorch_lightning",
)


def _normalise_columns(column: str | Sequence[str]) -> list[str]:
    """Normalise a column specification to a list."""

    if isinstance(column, str):
        return [column]

    normalised = list(column)
    if not normalised:
        raise ValueError("At least one column must be specified")
    return normalised


def _normalise_loaders(loaders: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalise dataloader selection to the supported hook names."""

    if loaders is None:
        return _GLITCHABLE_LOADERS

    if isinstance(loaders, str):
        candidates = (loaders,)
    else:
        candidates = tuple(loaders)

    if not candidates:
        raise ValueError("At least one dataloader must be specified")

    unsupported = [name for name in candidates if name not in _GLITCHABLE_LOADERS]
    if unsupported:
        joined = ", ".join(sorted(unsupported))
        message = f"Unsupported dataloader hook(s): {joined}"
        raise ValueError(message)

    return candidates


def _glitch_output(
    output: Any,
    glitchlings: Gaggle | Glitchling | Iterable[str | Glitchling] | str,
    columns: Sequence[str],
    *,
    seed: int,
) -> Any:
    """Apply :meth:`DataLoader.glitch` to supported structures."""

    glitch_method = getattr(output, "glitch", None)
    if callable(glitch_method):
        return glitch_method(glitchlings, column=columns, seed=seed)

    if isinstance(output, Mapping):
        return {
            key: _glitch_output(inner, glitchlings, columns, seed=seed)
            for key, inner in output.items()
        }

    if isinstance(output, Sequence) and not isinstance(output, (str, bytes, bytearray)):
        try:
            return output.__class__(
                _glitch_output(item, glitchlings, columns, seed=seed) for item in output
            )
        except TypeError:
            return [
                _glitch_output(item, glitchlings, columns, seed=seed) for item in output
            ]

    return output


class _GlitchedLightningDataModule:
    """Proxy that returns glitched dataloaders for selected hooks."""

    def __init__(
        self,
        datamodule: Any,
        glitchlings: Gaggle | Glitchling | Iterable[str | Glitchling] | str,
        columns: Sequence[str],
        *,
        seed: int,
        loaders: tuple[str, ...],
    ) -> None:
        self._datamodule = datamodule
        self._glitchlings = glitchlings
        self._columns = tuple(columns)
        self._seed = seed
        self._loaders = set(loaders)

    def train_dataloader(self) -> Any:
        original = self._datamodule.train_dataloader()
        return self._maybe_glitch("train", original)

    def val_dataloader(self) -> Any:  # pragma: no cover - passthrough logic
        original = self._datamodule.val_dataloader()
        return self._maybe_glitch("val", original)

    def test_dataloader(self) -> Any:  # pragma: no cover - passthrough logic
        original = self._datamodule.test_dataloader()
        return self._maybe_glitch("test", original)

    def predict_dataloader(self) -> Any:  # pragma: no cover - passthrough logic
        original = self._datamodule.predict_dataloader()
        return self._maybe_glitch("predict", original)

    def _maybe_glitch(self, hook: str, output: Any) -> Any:
        if hook not in self._loaders:
            return output

        return _glitch_output(output, self._glitchlings, self._columns, seed=self._seed)

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - delegation only
        return getattr(self._datamodule, name)


def _glitch_datamodule(
    datamodule: Any,
    glitchlings: Gaggle | Glitchling | Iterable[str | Glitchling] | str,
    column: str | Sequence[str],
    *,
    seed: int = 151,
    loaders: str | Sequence[str] | None = None,
) -> _GlitchedLightningDataModule:
    """Return a proxy that yields glitched dataloaders for the requested hooks."""

    columns = _normalise_columns(column)
    selected_loaders = _normalise_loaders(loaders)
    torch_dlc.install()
    return _GlitchedLightningDataModule(
        datamodule,
        glitchlings,
        columns,
        seed=seed,
        loaders=selected_loaders,
    )


def _ensure_datamodule_class() -> Any:
    """Return the Lightning :class:`~pytorch_lightning.LightningDataModule` with ``.glitch``."""

    datamodule_cls = _LIGHTNING_DATAMODULE.require()

    if getattr(datamodule_cls, "glitch", None) is None:

        def glitch(  # type: ignore[override]
            self: Any,
            glitchlings: Gaggle | Glitchling | Iterable[str | Glitchling] | str,
            *,
            column: str | Sequence[str],
            seed: int = 151,
            loaders: str | Sequence[str] | None = None,
            **_: Any,
        ) -> _GlitchedLightningDataModule:
            """Return a proxy yielding glitched dataloaders for this module."""

            return _glitch_datamodule(
                self,
                glitchlings,
                column,
                seed=seed,
                loaders=loaders,
            )

        setattr(datamodule_cls, "glitch", glitch)

    return datamodule_cls


def install() -> None:
    """Monkeypatch PyTorch Lightning's :class:`LightningDataModule` with ``.glitch``."""

    _ensure_datamodule_class()


if _LIGHTNING_DATAMODULE.is_available():
    LightningDataModule = _ensure_datamodule_class()
else:  # pragma: no cover - dependency required at runtime
    LightningDataModule = None  # type: ignore[assignment]


__all__ = ["LightningDataModule", "install"]
