"""Pure validation functions for configuration data.

This module contains only pure validation functions that operate on already-
loaded data structures. Functions here do not perform IO - they validate
in-memory data and return normalized results.

Pure guarantees:
- No file IO
- No environment variable access
- No mutable global state
- Same inputs always produce same outputs
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def normalize_mapping(
    data: Any,
    *,
    source: str,
    description: str,
    allow_empty: bool = False,
    mapping_error: str = "must contain a top-level mapping.",
) -> dict[str, Any]:
    """Ensure ``data`` is a mapping, normalising error messages.

    This is a pure validation function - it checks that ``data`` is a valid
    mapping and returns a normalized dict copy.

    Args:
        data: The data to validate.
        source: A label identifying where the data came from (for error messages).
        description: A human-readable description of the data type.
        allow_empty: If True, None values are converted to empty dicts.
        mapping_error: Custom error message suffix when data is not a mapping.

    Returns:
        A dict copy of the mapping.

    Raises:
        ValueError: If the data is not a valid mapping.
    """
    if data is None:
        if allow_empty:
            return {}
        raise ValueError(f"{description} '{source}' is empty.")
    if not isinstance(data, Mapping):
        raise ValueError(f"{description} '{source}' {mapping_error}")
    return dict(data)


def validate_runtime_config_data(data: Any, *, source: str) -> Mapping[str, Any]:
    """Validate runtime configuration data structure.

    This is a pure validation function that checks the structure of
    already-loaded configuration data without performing any IO.

    Args:
        data: The configuration data (typically from TOML parsing).
        source: A label identifying the data source (for error messages).

    Returns:
        The validated mapping.

    Raises:
        ValueError: If the configuration structure is invalid.
    """
    mapping = normalize_mapping(
        data,
        source=source,
        description="Configuration file",
        allow_empty=True,
    )

    # Configuration file is currently empty (lexicon system removed)
    # but we still accept empty configs for forwards compatibility
    return mapping


def validate_attack_config_schema(data: Any, *, source: str) -> Mapping[str, Any]:
    """Validate attack configuration data structure.

    This is a pure validation function that checks the structure of
    already-loaded configuration data. It does NOT perform jsonschema
    validation (that requires the optional dependency).

    Args:
        data: The configuration data (typically from YAML parsing).
        source: A label identifying the data source (for error messages).

    Returns:
        The validated mapping.

    Raises:
        ValueError: If the configuration structure is invalid.
    """
    mapping = normalize_mapping(
        data,
        source=source,
        description="Attack configuration",
        mapping_error="must be a mapping.",
    )

    unexpected = [key for key in mapping if key not in {"glitchlings", "seed"}]
    if unexpected:
        extras = ", ".join(sorted(unexpected))
        raise ValueError(f"Attack configuration '{source}' has unsupported fields: {extras}.")

    if "glitchlings" not in mapping:
        raise ValueError(f"Attack configuration '{source}' must define 'glitchlings'.")

    raw_glitchlings = mapping["glitchlings"]
    if not isinstance(raw_glitchlings, Sequence) or isinstance(raw_glitchlings, (str, bytes)):
        raise ValueError(f"'glitchlings' in '{source}' must be a sequence.")

    seed = mapping.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise ValueError(f"Seed in '{source}' must be an integer if provided.")

    for index, entry in enumerate(raw_glitchlings, start=1):
        _validate_glitchling_entry(entry, source=source, index=index)

    return mapping


def _validate_glitchling_entry(entry: Any, *, source: str, index: int) -> None:
    """Validate a single glitchling entry in an attack configuration."""
    if isinstance(entry, str):
        if not entry.strip():
            raise ValueError(f"{source}: glitchling #{index} name cannot be empty.")
        return

    if isinstance(entry, Mapping):
        if "type" in entry:
            raise ValueError(f"{source}: glitchling #{index} uses unsupported 'type'; use 'name'.")

        name_candidate = entry.get("name")
        if not isinstance(name_candidate, str) or not name_candidate.strip():
            raise ValueError(f"{source}: glitchling #{index} is missing a 'name'.")

        parameters = entry.get("parameters")
        if parameters is not None and not isinstance(parameters, Mapping):
            raise ValueError(
                f"{source}: glitchling '{name_candidate}' parameters must be a mapping."
            )
        return

    raise ValueError(f"{source}: glitchling #{index} must be a string or mapping.")


__all__ = [
    "normalize_mapping",
    "validate_attack_config_schema",
    "validate_runtime_config_data",
]
