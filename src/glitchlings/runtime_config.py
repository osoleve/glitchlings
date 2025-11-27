"""Compatibility wrapper for runtime configuration helpers.

Prefer ``glitchlings.conf`` for imports.
"""

from __future__ import annotations

from .conf import (
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_PATH,
    RuntimeConfig,
    get_config,
    reload_config,
    reset_config,
)

__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_CONFIG_PATH",
    "RuntimeConfig",
    "get_config",
    "reload_config",
    "reset_config",
]
