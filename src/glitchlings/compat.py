"""Utilities for interacting with optional third-party dependencies."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Generic, TypeVar, cast

__all__ = ["OptionalImport", "optional_import"]

_T = TypeVar("_T")
_MISSING = object()


class OptionalImport(Generic[_T]):
    """Lazily import an optional dependency and expose informative helpers."""

    __slots__ = ("_import_path", "_attribute", "_friendly_name", "_cached", "_error")

    def __init__(
        self,
        import_path: str,
        attribute: str | None = None,
        *,
        friendly_name: str | None = None,
    ) -> None:
        self._import_path = import_path
        self._attribute = attribute
        self._friendly_name = friendly_name or attribute or import_path
        self._cached: object = _MISSING
        self._error: ModuleNotFoundError | None = None

    def require(self) -> _T:
        """Return the resolved object or raise :class:`ModuleNotFoundError`."""

        resolved = self._load()
        if resolved is None:
            message = f"{self._friendly_name} is not installed"
            raise ModuleNotFoundError(message) from self._error
        return resolved

    def optional(self) -> _T | None:
        """Return the resolved object when available, otherwise ``None``."""

        return self._load()

    def is_available(self) -> bool:
        """Return ``True`` when the optional dependency is importable."""

        return self._load() is not None

    def error(self) -> ModuleNotFoundError | None:
        """Return the captured import error for debugging purposes."""

        self._load()
        return self._error

    def _load(self) -> _T | None:
        """Attempt to import the configured module and attribute once."""

        if self._cached is _MISSING:
            try:
                module = import_module(self._import_path)
            except ModuleNotFoundError as exc:
                self._cached = None
                self._error = exc
            else:
                if self._attribute is None:
                    self._cached = module
                else:
                    try:
                        value = getattr(module, self._attribute)
                    except AttributeError as exc:  # pragma: no cover - defensive guard
                        message = (
                            f"{self._import_path} does not expose {self._attribute}"
                        )
                        raise ImportError(message) from exc
                    self._cached = value
        if self._cached is None:
            return None
        return cast(_T, self._cached)


def optional_import(
    import_path: str,
    attribute: str | None = None,
    *,
    friendly_name: str | None = None,
) -> OptionalImport[Any]:
    """Create an :class:`OptionalImport` for the requested module attribute."""

    return OptionalImport(import_path, attribute, friendly_name=friendly_name)
