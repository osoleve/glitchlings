"""Configuration helpers and schemas for glitchlings.

Architecture:
- conf/types.py - Pure dataclass definitions (no side effects)
- conf/schema.py - Pure validation functions (no IO)
- conf/loaders.py - Impure loading functions (file IO, global state)
- conf/__init__.py - Re-exports for backward compatibility
"""

# Re-export DEFAULT_ATTACK_SEED from constants for backward compatibility
from glitchlings.constants import DEFAULT_ATTACK_SEED, DEFAULT_CONFIG_PATH, DEFAULT_LEXICON_PRIORITY

from .loaders import (
    CONFIG_ENV_VAR,
    build_gaggle,
    get_config,
    load_attack_config,
    parse_attack_config,
    reload_config,
    reset_config,
)
from .types import (
    ATTACK_CONFIG_SCHEMA,
    AttackConfig,
    LexiconConfig,
    RuntimeConfig,
)

__all__ = [
    "ATTACK_CONFIG_SCHEMA",
    "AttackConfig",
    "CONFIG_ENV_VAR",
    "DEFAULT_ATTACK_SEED",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LEXICON_PRIORITY",
    "RuntimeConfig",
    "LexiconConfig",
    "build_gaggle",
    "get_config",
    "load_attack_config",
    "parse_attack_config",
    "reload_config",
    "reset_config",
]
