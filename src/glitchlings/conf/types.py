"""Pure type definitions for configuration structures.

This module contains only dataclass definitions and type constants with no
side effects. It can be safely imported anywhere without triggering IO or
module loading.

Pure guarantees:
- No import side effects
- No file IO
- No environment variable access
- No mutable global state
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..zoo import Glitchling


@dataclass(slots=True)
class RuntimeConfig:
    """Top-level runtime configuration loaded from ``config.toml``."""

    path: Path


@dataclass(slots=True)
class AttackConfig:
    """Structured representation of a glitchling roster loaded from YAML."""

    glitchlings: list["Glitchling"]
    seed: int | None = None


# JSON Schema for attack configuration validation
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


__all__ = [
    "ATTACK_CONFIG_SCHEMA",
    "AttackConfig",
    "RuntimeConfig",
]
