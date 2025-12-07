"""Centralized defaults and shared configuration constants."""

from __future__ import annotations

from pathlib import Path

# Global configuration defaults
DEFAULT_ATTACK_SEED = 151
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")

# Character-level glitchling default rates
DEFAULT_TYPOGRE_RATE = 0.02
DEFAULT_TYPOGRE_KEYBOARD = "CURATOR_QWERTY"
DEFAULT_MIM1C_RATE = 0.02
DEFAULT_SCANNEQUIN_RATE = 0.02
DEFAULT_ZEEDUB_RATE = 0.02

# Word-level glitchling default rates
DEFAULT_WHEREWOLF_RATE = 0.02
DEFAULT_WHEREWOLF_WEIGHTING = "flat"
DEFAULT_JARGOYLE_RATE = 0.01
DEFAULT_REDACTYL_RATE = 0.025
DEFAULT_REDACTYL_CHAR = "\u2588"  # █ FULL BLOCK

# Rushmore default rates per mode
RUSHMORE_DEFAULT_RATES = {
    "delete": 0.01,
    "duplicate": 0.01,
    "swap": 0.5,
}

# Mim1c Unicode script class defaults
MIM1C_DEFAULT_CLASSES: tuple[str, ...] = ("LATIN", "GREEK", "CYRILLIC", "COMMON")

# Zeedub zero-width character palette
ZEEDUB_DEFAULT_ZERO_WIDTHS: tuple[str, ...] = (
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\ufeff",  # BYTE ORDER MARK (zero-width no-break space)
)

__all__ = [
    "DEFAULT_ATTACK_SEED",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_WHEREWOLF_RATE",
    "DEFAULT_WHEREWOLF_WEIGHTING",
    "DEFAULT_JARGOYLE_RATE",
    "DEFAULT_MIM1C_RATE",
    "DEFAULT_REDACTYL_CHAR",
    "DEFAULT_REDACTYL_RATE",
    "DEFAULT_SCANNEQUIN_RATE",
    "DEFAULT_TYPOGRE_KEYBOARD",
    "DEFAULT_TYPOGRE_RATE",
    "DEFAULT_ZEEDUB_RATE",
    "MIM1C_DEFAULT_CLASSES",
    "RUSHMORE_DEFAULT_RATES",
    "ZEEDUB_DEFAULT_ZERO_WIDTHS",
]
