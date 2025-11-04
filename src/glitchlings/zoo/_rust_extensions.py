"""Helpers for loading the mandatory Rust acceleration hooks."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import Any, Callable, Mapping, MutableMapping, cast


class _MissingRustOperation:
    """Callable placeholder that raises when the Rust extension is unavailable."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - runtime failure
        message = (
            "Rust operation '{name}' is unavailable because glitchlings._zoo_rust "
            "failed to import. Rebuild the project with `pip install .` or "
            "`maturin develop`."
        ).format(name=self.name)
        raise RuntimeError(message)


class _MissingRustModule:
    """Sentinel module that provides informative error callables."""

    __slots__ = ()

    def __getattr__(self, name: str) -> _MissingRustOperation:
        return _MissingRustOperation(name)

    def __dir__(self) -> list[str]:  # pragma: no cover - debug helper
        return []


def _import_rust_module() -> Any:
    try:
        module = import_module("_zoo_rust")
    except ModuleNotFoundError:
        try:
            module = import_module("glitchlings._zoo_rust")
        except ModuleNotFoundError:
            module = _MissingRustModule()
    else:
        sys.modules.setdefault("glitchlings._zoo_rust", module)
    return module


_RUST_MODULE = _import_rust_module()
HAS_RUST_EXTENSION = not isinstance(_RUST_MODULE, _MissingRustModule)
_OPERATION_CACHE: MutableMapping[str, Callable[..., Any]] = {}


def _build_missing_operation_error(name: str) -> RuntimeError:
    message = (
        "Rust operation '{name}' is not exported by glitchlings._zoo_rust. "
        "Rebuild the project to refresh the compiled extension."
    ).format(name=name)
    return RuntimeError(message)


def get_rust_operation(operation_name: str) -> Callable[..., Any]:
    """Return a callable exported by :mod:`glitchlings._zoo_rust`.

    Parameters
    ----------
    operation_name : str
        Name of the function to retrieve from the compiled extension.

    Raises
    ------
    RuntimeError
        If the operation cannot be located or is not callable.
    """

    operation = _OPERATION_CACHE.get(operation_name)
    if operation is not None:
        return operation

    try:
        candidate = getattr(_RUST_MODULE, operation_name)
    except AttributeError as exc:
        raise _build_missing_operation_error(operation_name) from exc

    if not callable(candidate):
        raise _build_missing_operation_error(operation_name)

    operation = cast(Callable[..., Any], candidate)
    _OPERATION_CACHE[operation_name] = operation
    return operation


def preload_operations(*operation_names: str) -> Mapping[str, Callable[..., Any]]:
    """Eagerly load multiple Rust operations at once."""

    return {name: get_rust_operation(name) for name in operation_names}


__all__ = ["get_rust_operation", "preload_operations", "HAS_RUST_EXTENSION"]
