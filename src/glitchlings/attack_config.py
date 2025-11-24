"""Attack roster configuration handling and helpers."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Protocol, Sequence, cast

from glitchlings.compat import jsonschema

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .zoo import Gaggle, Glitchling


class _YamlModule(Protocol):
    YAMLError: type[Exception]

    def safe_load(self, stream: str) -> Any: ...


yaml = cast(_YamlModule, importlib.import_module("yaml"))

DEFAULT_ATTACK_SEED = 151

ATTACK_CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["glitchlings"],
    "properties": {
        "glitchlings": {
            "type": "array",
            "minItems": 1,
            "items": {
                "anyOf": [
                    {"type": "string", "minLength": 1},
                    {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "parameters": {"type": "object"},
                        },
                        "additionalProperties": True,
                    },
                ]
            },
        },
        "seed": {"type": "integer"},
    },
    "additionalProperties": False,
}


@dataclass(slots=True)
class AttackConfig:
    """Structured representation of a glitchling roster loaded from YAML."""

    glitchlings: list["Glitchling"]
    seed: int | None = None


def load_attack_config(
    source: str | Path | TextIOBase,
    *,
    encoding: str = "utf-8",
) -> AttackConfig:
    """Load and parse an attack configuration from YAML."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        label = str(path)
        try:
            text = path.read_text(encoding=encoding)
        except FileNotFoundError as exc:
            raise ValueError(f"Attack configuration '{label}' was not found.") from exc
    elif isinstance(source, TextIOBase):
        label = getattr(source, "name", "<stream>")
        text = source.read()
    else:
        raise TypeError("Attack configuration source must be a path or text stream.")

    data = _load_yaml(text, label)
    return parse_attack_config(data, source=label)


def _validate_attack_config_schema(data: Any, *, source: str) -> Mapping[str, Any]:
    if data is None:
        raise ValueError(f"Attack configuration '{source}' is empty.")
    if not isinstance(data, Mapping):
        raise ValueError(f"Attack configuration '{source}' must be a mapping.")

    unexpected = [key for key in data if key not in {"glitchlings", "seed"}]
    if unexpected:
        extras = ", ".join(sorted(unexpected))
        raise ValueError(f"Attack configuration '{source}' has unsupported fields: {extras}.")

    if "glitchlings" not in data:
        raise ValueError(f"Attack configuration '{source}' must define 'glitchlings'.")

    raw_glitchlings = data["glitchlings"]
    if not isinstance(raw_glitchlings, Sequence) or isinstance(raw_glitchlings, (str, bytes)):
        raise ValueError(f"'glitchlings' in '{source}' must be a sequence.")

    seed = data.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise ValueError(f"Seed in '{source}' must be an integer if provided.")

    for index, entry in enumerate(raw_glitchlings, start=1):
        if isinstance(entry, Mapping):
            if "type" in entry:
                raise ValueError(
                    f"{source}: glitchling #{index} uses unsupported 'type'; use 'name'."
                )

            name_candidate = entry.get("name")
            if not isinstance(name_candidate, str) or not name_candidate.strip():
                raise ValueError(f"{source}: glitchling #{index} is missing a 'name'.")
            parameters = entry.get("parameters")
            if parameters is not None and not isinstance(parameters, Mapping):
                raise ValueError(
                    f"{source}: glitchling '{name_candidate}' parameters must be a mapping."
                )

    schema_module = jsonschema.get()
    if schema_module is not None:
        try:
            schema_module.validate(instance=data, schema=ATTACK_CONFIG_SCHEMA)
        except schema_module.exceptions.ValidationError as exc:  # pragma: no cover - optional dep
            message = exc.message
            raise ValueError(f"Attack configuration '{source}' is invalid: {message}") from exc

    return data


def parse_attack_config(data: Any, *, source: str = "<config>") -> AttackConfig:
    """Convert arbitrary YAML data into a validated ``AttackConfig``."""
    mapping = _validate_attack_config_schema(data, source=source)

    raw_glitchlings = mapping["glitchlings"]

    glitchlings: list["Glitchling"] = []
    for index, entry in enumerate(raw_glitchlings, start=1):
        glitchlings.append(_build_glitchling(entry, source, index))

    seed = mapping.get("seed")

    return AttackConfig(glitchlings=glitchlings, seed=seed)


def build_gaggle(config: AttackConfig, *, seed_override: int | None = None) -> "Gaggle":
    """Instantiate a ``Gaggle`` according to ``config``."""
    from .zoo import Gaggle  # Imported lazily to avoid circular dependencies

    seed = seed_override if seed_override is not None else config.seed
    if seed is None:
        seed = DEFAULT_ATTACK_SEED

    return Gaggle(config.glitchlings, seed=seed)


def _load_yaml(text: str, label: str) -> Any:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse attack configuration '{label}': {exc}") from exc


def _build_glitchling(entry: Any, source: str, index: int) -> "Glitchling":
    from .zoo import get_glitchling_class, parse_glitchling_spec

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
    "ATTACK_CONFIG_SCHEMA",
    "AttackConfig",
    "DEFAULT_ATTACK_SEED",
    "build_gaggle",
    "load_attack_config",
    "parse_attack_config",
]
