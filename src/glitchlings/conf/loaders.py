"""Impure configuration loading functions.

This module is IMPURE - it performs file IO, environment variable access,
and maintains global state. Use the schema module for pure validation.

Impure operations:
- File reading (TOML, YAML)
- Environment variable access
- Global configuration cache
- Optional dependency imports (jsonschema, yaml)
"""

from __future__ import annotations

import importlib
import os
from io import TextIOBase
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Callable, Mapping, Protocol, cast

from glitchlings.constants import DEFAULT_ATTACK_SEED, DEFAULT_CONFIG_PATH, DEFAULT_LEXICON_PRIORITY

from ..compat import jsonschema
from .schema import (
    normalize_mapping,
    normalize_priority_list,
    resolve_relative_path,
    validate_attack_config_schema,
    validate_runtime_config_data,
)
from .types import ATTACK_CONFIG_SCHEMA, AttackConfig, LexiconConfig, RuntimeConfig

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..zoo import Gaggle, Glitchling


# ---------------------------------------------------------------------------
# TOML/YAML module loading (impure - module imports)
# ---------------------------------------------------------------------------

try:  # Python 3.11+
    import tomllib as _tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    _tomllib = importlib.import_module("tomli")


class _TomllibModule(Protocol):
    def load(self, fp: IO[bytes]) -> Any: ...


class _YamlModule(Protocol):
    YAMLError: type[Exception]

    def safe_load(self, stream: str) -> Any: ...


tomllib = cast(_TomllibModule, _tomllib)
yaml = cast(_YamlModule, importlib.import_module("yaml"))


# ---------------------------------------------------------------------------
# Environment and path resolution (impure - environment access)
# ---------------------------------------------------------------------------

CONFIG_ENV_VAR = "GLITCHLINGS_CONFIG"


def _resolve_config_path() -> Path:
    """Resolve the configuration file path from environment or default."""
    override = os.environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override)
    return DEFAULT_CONFIG_PATH


# ---------------------------------------------------------------------------
# Global configuration state (impure - mutable global)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# File IO helpers (impure - file system access)
# ---------------------------------------------------------------------------


def _read_text_source(
    source: str | Path | TextIOBase,
    *,
    description: str,
    encoding: str,
    missing_error: Callable[[Path], Exception] | None,
) -> tuple[str, str]:
    """Read text content from a file path or stream."""
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


# ---------------------------------------------------------------------------
# Runtime configuration loading (impure - file IO + validation)
# ---------------------------------------------------------------------------


def _load_runtime_config() -> RuntimeConfig:
    """Load runtime configuration from disk."""
    path = _resolve_config_path()
    data = load_binary_config(
        path,
        loader=tomllib.load,
        description="Configuration file",
        allow_missing=path == DEFAULT_CONFIG_PATH,
        allow_empty=True,
    )
    mapping = validate_runtime_config_data(data, source=str(path))

    lexicon_section = mapping.get("lexicon", {})

    priority = normalize_priority_list(
        lexicon_section.get("priority"),
        default=DEFAULT_LEXICON_PRIORITY,
    )

    vector_cache = resolve_relative_path(
        lexicon_section.get("vector_cache"),
        base=path.parent,
    )
    lexicon_config = LexiconConfig(
        priority=priority,
        vector_cache=vector_cache,
    )

    return RuntimeConfig(lexicon=lexicon_config, path=path)


# ---------------------------------------------------------------------------
# Attack configuration loading (impure - file IO + validation)
# ---------------------------------------------------------------------------


def _load_yaml(text: str, label: str) -> Any:
    """Parse YAML text, wrapping errors with source context."""
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse attack configuration '{label}': {exc}") from exc


def load_attack_config(
    source: str | Path | TextIOBase,
    *,
    encoding: str = "utf-8",
) -> AttackConfig:
    """Load and parse an attack configuration from YAML."""
    mapping, label = load_text_config(
        source,
        loader=_load_yaml,
        description="Attack configuration",
        encoding=encoding,
        mapping_error="must be a mapping.",
        missing_error=lambda path: ValueError(f"Attack configuration '{path}' was not found."),
        pass_label=True,
    )
    return parse_attack_config(mapping, source=label)


def parse_attack_config(data: Any, *, source: str = "<config>") -> AttackConfig:
    """Convert arbitrary YAML data into a validated ``AttackConfig``."""
    mapping = validate_attack_config_schema(data, source=source)

    # Optional jsonschema validation (impure - optional dependency)
    schema_module = jsonschema.get()
    if schema_module is not None:
        try:
            schema_module.validate(instance=mapping, schema=ATTACK_CONFIG_SCHEMA)
        except schema_module.exceptions.ValidationError as exc:  # pragma: no cover - optional dep
            message = exc.message
            raise ValueError(f"Attack configuration '{source}' is invalid: {message}") from exc

    raw_glitchlings = mapping["glitchlings"]

    glitchlings: list["Glitchling"] = []
    for index, entry in enumerate(raw_glitchlings, start=1):
        glitchlings.append(_build_glitchling(entry, source, index))

    seed = mapping.get("seed")

    return AttackConfig(glitchlings=glitchlings, seed=seed)


def build_gaggle(config: AttackConfig, *, seed_override: int | None = None) -> "Gaggle":
    """Instantiate a ``Gaggle`` according to ``config``."""
    from ..zoo import Gaggle  # Imported lazily to avoid circular dependencies

    seed = seed_override if seed_override is not None else config.seed
    if seed is None:
        seed = DEFAULT_ATTACK_SEED

    return Gaggle(config.glitchlings, seed=seed)


def _build_glitchling(entry: Any, source: str, index: int) -> "Glitchling":
    """Build a glitchling instance from a configuration entry."""
    from ..zoo import get_glitchling_class, parse_glitchling_spec

    if isinstance(entry, str):
        try:
            return parse_glitchling_spec(entry)
        except ValueError as exc:
            raise ValueError(f"{source}: glitchling #{index}: {exc}") from exc

    if isinstance(entry, Mapping):
        if "type" in entry:
            raise ValueError(f"{source}: glitchling #{index} uses unsupported 'type'; use 'name'.")

        name_value = entry.get("name")

        if not isinstance(name_value, str) or not name_value.strip():
            raise ValueError(f"{source}: glitchling #{index} is missing a 'name'.")

        parameters = entry.get("parameters")
        if parameters is not None:
            if not isinstance(parameters, Mapping):
                raise ValueError(
                    f"{source}: glitchling '{name_value}' parameters must be a mapping."
                )
            kwargs = dict(parameters)
        else:
            kwargs = {
                key: value for key, value in entry.items() if key not in {"name", "parameters"}
            }

        try:
            glitchling_type = get_glitchling_class(name_value)
        except ValueError as exc:
            raise ValueError(f"{source}: glitchling #{index}: {exc}") from exc

        try:
            return glitchling_type(**kwargs)
        except TypeError as exc:
            raise ValueError(
                f"{source}: glitchling #{index}: failed to instantiate '{name_value}': {exc}"
            ) from exc

    raise ValueError(f"{source}: glitchling #{index} must be a string or mapping.")


__all__ = [
    "CONFIG_ENV_VAR",
    "build_gaggle",
    "get_config",
    "load_attack_config",
    "load_binary_config",
    "load_text_config",
    "parse_attack_config",
    "reload_config",
    "reset_config",
]
