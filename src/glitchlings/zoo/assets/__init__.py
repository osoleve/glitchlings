from __future__ import annotations

import json
from functools import cache
from hashlib import blake2b
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Any, BinaryIO, TextIO, cast

_DEFAULT_DIGEST_SIZE = 32


def _asset(name: str) -> Traversable:
    asset = resources.files(__name__).joinpath(name)
    if not asset.is_file():  # pragma: no cover - defensive guard for packaging issues
        raise FileNotFoundError(f"Asset '{name}' not found at {asset}")
    return asset


def read_text(name: str, *, encoding: str = "utf-8") -> str:
    """Return the decoded contents of a bundled text asset."""

    return cast(str, _asset(name).read_text(encoding=encoding))


def open_text(name: str, *, encoding: str = "utf-8") -> TextIO:
    """Open a bundled text asset for reading."""

    return cast(TextIO, _asset(name).open("r", encoding=encoding))


def open_binary(name: str) -> BinaryIO:
    """Open a bundled binary asset for reading."""

    return cast(BinaryIO, _asset(name).open("rb"))


def load_json(name: str, *, encoding: str = "utf-8") -> Any:
    """Deserialize a JSON asset using the shared loader helpers."""

    with open_text(name, encoding=encoding) as handle:
        return json.load(handle)


def hash_asset(name: str) -> str:
    """Return a BLAKE2b digest for the bundled asset ``name``."""

    digest = blake2b(digest_size=_DEFAULT_DIGEST_SIZE)
    with open_binary(name) as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


@cache
def load_homophone_groups(name: str = "ekkokin_homophones.json") -> tuple[tuple[str, ...], ...]:
    """Return the curated homophone sets bundled for the Ekkokin glitchling."""

    data: list[list[str]] = load_json(name)
    return tuple(tuple(group) for group in data)


__all__ = [
    "read_text",
    "open_text",
    "open_binary",
    "load_json",
    "hash_asset",
    "load_homophone_groups",
]
