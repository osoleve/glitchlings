"""Compatibility wrapper for attack configuration helpers.

Prefer ``glitchlings.conf.attack_config`` for imports.
"""

from __future__ import annotations

from .conf.attack_config import (
    ATTACK_CONFIG_SCHEMA,
    DEFAULT_ATTACK_SEED,
    AttackConfig,
    build_gaggle,
    load_attack_config,
    parse_attack_config,
)

__all__ = [
    "ATTACK_CONFIG_SCHEMA",
    "AttackConfig",
    "DEFAULT_ATTACK_SEED",
    "build_gaggle",
    "load_attack_config",
    "parse_attack_config",
]
