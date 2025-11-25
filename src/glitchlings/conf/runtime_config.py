"""Runtime configuration handling for lexicon settings and defaults."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, Mapping, Protocol, Sequence, cast

from glitchlings.constants import DEFAULT_CONFIG_PATH, DEFAULT_LEXICON_PRIORITY

from ._loader import load_binary_config, normalize_mapping

try:  # Python 3.11+
    import tomllib as _tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    _tomllib = importlib.import_module("tomli")


class _TomllibModule(Protocol):
    def load(self, fp: IO[bytes]) -> Any: ...


tomllib = cast(_TomllibModule, _tomllib)

CONFIG_ENV_VAR = "GLITCHLINGS_CONFIG"


@dataclass(slots=True)
class LexiconConfig:
    """Lexicon-specific configuration section."""

    priority: list[str] = field(default_factory=lambda: list(DEFAULT_LEXICON_PRIORITY))
    vector_cache: Path | None = None


@dataclass(slots=True)
class RuntimeConfig:
    """Top-level runtime configuration loaded from ``config.toml``."""

    lexicon: LexiconConfig
    path: Path


_CONFIG: RuntimeConfig | None = None


def reset_config() -> None:
    """Forget any cached runtime configuration."""
    global _CONFIG
    _CONFIG = None


def reload_config() -> RuntimeConfig:
    """Reload the runtime configuration from disk."""
    reset_config()
    return get_config()


def get_config() -> RuntimeConfig:
    """Return the cached runtime configuration, loading it if necessary."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_runtime_config()
    return _CONFIG


def _load_runtime_config() -> RuntimeConfig:
    path = _resolve_config_path()
    data = load_binary_config(
        path,
        loader=tomllib.load,
        description="Configuration file",
        allow_missing=path == DEFAULT_CONFIG_PATH,
        allow_empty=True,
    )
    mapping = _validate_runtime_config_data(data, source=path)

    lexicon_section = mapping.get("lexicon", {})

    priority = lexicon_section.get("priority", DEFAULT_LEXICON_PRIORITY)
    if not isinstance(priority, Sequence) or isinstance(priority, (str, bytes)):
        raise ValueError("lexicon.priority must be a sequence of strings.")
    normalized_priority = []
    for item in priority:
        string_value = str(item)
        if not string_value:
            raise ValueError("lexicon.priority entries must be non-empty strings.")
        normalized_priority.append(string_value)

    vector_cache = _resolve_optional_path(
        lexicon_section.get("vector_cache"),
        base=path.parent,
    )
    lexicon_config = LexiconConfig(
        priority=normalized_priority,
        vector_cache=vector_cache,
    )

    return RuntimeConfig(lexicon=lexicon_config, path=path)


def _resolve_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override)
    return DEFAULT_CONFIG_PATH


def _validate_runtime_config_data(data: Any, *, source: Path) -> Mapping[str, Any]:
    mapping = normalize_mapping(
        data,
        source=str(source),
        description="Configuration file",
        allow_empty=True,
    )

    allowed_sections = {"lexicon"}
    unexpected_sections = [str(key) for key in mapping if key not in allowed_sections]
    if unexpected_sections:
        extras = ", ".join(sorted(unexpected_sections))
        raise ValueError(f"Configuration file '{source}' has unsupported sections: {extras}.")

    lexicon_section = mapping.get("lexicon", {})
    if not isinstance(lexicon_section, Mapping):
        raise ValueError("Configuration 'lexicon' section must be a table.")

    allowed_lexicon_keys = {"priority", "vector_cache"}
    unexpected_keys = [str(key) for key in lexicon_section if key not in allowed_lexicon_keys]
    if unexpected_keys:
        extras = ", ".join(sorted(unexpected_keys))
        raise ValueError(f"Unknown lexicon settings: {extras}.")

    for key in ("vector_cache",):
        value = lexicon_section.get(key)
        if value is not None and not isinstance(value, (str, os.PathLike)):
            raise ValueError(f"lexicon.{key} must be a path or string when provided.")

    return mapping


def _resolve_optional_path(value: Any, *, base: Path) -> Path | None:
    if value in (None, ""):
        return None

    candidate = Path(str(value))
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    return candidate


__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LEXICON_PRIORITY",
    "LexiconConfig",
    "RuntimeConfig",
    "get_config",
    "reload_config",
    "reset_config",
]
