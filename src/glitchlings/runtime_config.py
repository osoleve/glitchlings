"""Compatibility wrapper for runtime configuration helpers.

Prefer ``glitchlings.conf.runtime_config`` for imports.
"""

from __future__ import annotations

from .conf.runtime_config import (
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_PATH,
    DEFAULT_LEXICON_PRIORITY,
    LexiconConfig,
    RuntimeConfig,
    get_config,
    reload_config,
    reset_config,
)

__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LEXICON_PRIORITY",
    "RuntimeConfig",
    "LexiconConfig",
    "get_config",
    "reload_config",
    "reset_config",
]
