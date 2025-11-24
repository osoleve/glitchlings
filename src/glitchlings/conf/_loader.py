"""Shared helpers for loading configuration mappings."""

from __future__ import annotations

from io import TextIOBase
from pathlib import Path
from typing import IO, Any, Callable, Mapping


def normalize_mapping(
    data: Any,
    *,
    source: str,
    description: str,
    allow_empty: bool = False,
    mapping_error: str = "must contain a top-level mapping.",
) -> dict[str, Any]:
    """Ensure ``data`` is a mapping, normalising error messages."""
    if data is None:
        if allow_empty:
            return {}
        raise ValueError(f"{description} '{source}' is empty.")
    if not isinstance(data, Mapping):
        raise ValueError(f"{description} '{source}' {mapping_error}")
    return dict(data)


def load_text_config(
    source: str | Path | TextIOBase,
    *,
    loader: Callable[..., Any],
    description: str,
    encoding: str = "utf-8",
    allow_empty: bool = False,
    mapping_error: str = "must contain a top-level mapping.",
    missing_error: Callable[[Path], Exception] | None = None,
    pass_label: bool = False,
) -> tuple[dict[str, Any], str]:
    """Load text configuration data and validate the top-level mapping."""
    text, label = _read_text_source(
        source,
        description=description,
        encoding=encoding,
        missing_error=missing_error,
    )
    if pass_label:
        data = loader(text, label)
    else:
        data = loader(text)
    mapping = normalize_mapping(
        data,
        source=label,
        description=description,
        allow_empty=allow_empty,
        mapping_error=mapping_error,
    )
    return mapping, label


def load_binary_config(
    path: Path,
    *,
    loader: Callable[[IO[bytes]], Any],
    description: str,
    allow_missing: bool = False,
    allow_empty: bool = False,
    mapping_error: str = "must contain a top-level mapping.",
) -> dict[str, Any]:
    """Load binary configuration data from disk and validate the mapping."""
    if not path.exists():
        if allow_missing:
            return {}
        raise FileNotFoundError(f"{description} '{path}' not found.")

    with path.open("rb") as handle:
        data = loader(handle)

    return normalize_mapping(
        data,
        source=str(path),
        description=description,
        allow_empty=allow_empty,
        mapping_error=mapping_error,
    )


def _read_text_source(
    source: str | Path | TextIOBase,
    *,
    description: str,
    encoding: str,
    missing_error: Callable[[Path], Exception] | None,
) -> tuple[str, str]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        try:
            text = path.read_text(encoding=encoding)
        except FileNotFoundError as exc:
            if missing_error is not None:
                raise missing_error(path) from exc
            raise
        return text, str(path)

    if isinstance(source, TextIOBase):
        return source.read(), getattr(source, "name", "<stream>")

    raise TypeError(f"{description} source must be a path or text stream.")
