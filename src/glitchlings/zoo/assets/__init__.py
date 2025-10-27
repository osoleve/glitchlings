from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable
from typing import BinaryIO, TextIO


def _asset(name: str) -> Traversable:
    asset = resources.files(__name__).joinpath(name)
    if not asset.is_file():  # pragma: no cover - defensive guard for packaging issues
        raise FileNotFoundError(f"Asset '{name}' not found in glitchlings.zoo.assets")
    return asset


def read_text(name: str, *, encoding: str = "utf-8") -> str:
    """Return the decoded contents of a bundled text asset."""

    return _asset(name).read_text(encoding=encoding)


def open_text(name: str, *, encoding: str = "utf-8") -> TextIO:
    """Open a bundled text asset for reading."""

    return _asset(name).open("r", encoding=encoding)


def open_binary(name: str) -> BinaryIO:
    """Open a bundled binary asset for reading."""

    return _asset(name).open("rb")


__all__ = ["read_text", "open_text", "open_binary"]
