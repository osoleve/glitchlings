"""Centralized defaults and shared configuration constants."""

from __future__ import annotations

from pathlib import Path

# Global configuration defaults
DEFAULT_ATTACK_SEED = 151
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")

# Character-level glitchling default rates
DEFAULT_TYPOGRE_RATE = 0.02
DEFAULT_TYPOGRE_KEYBOARD = "CURATOR_QWERTY"
DEFAULT_TYPOGRE_MOTOR_WEIGHTING = "uniform"
DEFAULT_MIM1C_RATE = 0.02
DEFAULT_ZEEDUB_RATE = 0.02

# Scannequin OCR simulation defaults
# Base rate for character-level OCR confusions
DEFAULT_SCANNEQUIN_RATE = 0.02
# Burst model parameters (Kanungo et al., 1994)
DEFAULT_SCANNEQUIN_BURST_ENTER = 0.0  # Disabled by default for backward compat
DEFAULT_SCANNEQUIN_BURST_EXIT = 0.3
DEFAULT_SCANNEQUIN_BURST_MULTIPLIER = 3.0
# Document-level bias parameters (UNLV-ISRI, 1995)
DEFAULT_SCANNEQUIN_BIAS_K = 0  # Disabled by default for backward compat
DEFAULT_SCANNEQUIN_BIAS_BETA = 2.0
# Whitespace error parameters (Smith, 2007)
DEFAULT_SCANNEQUIN_SPACE_DROP_RATE = 0.0  # Disabled by default
DEFAULT_SCANNEQUIN_SPACE_INSERT_RATE = 0.0  # Disabled by default

# Scannequin quality presets based on UNLV-ISRI test regimes (Rice et al., 1995)
# Each preset maps to (rate, burst_enter, burst_exit, burst_multiplier, bias_k, bias_beta,
#                      space_drop_rate, space_insert_rate)
SCANNEQUIN_PRESETS: dict[str, tuple[float, float, float, float, int, float, float, float]] = {
    # Clean 300dpi scan - minimal errors, good quality baseline
    "clean_300dpi": (0.01, 0.0, 0.3, 3.0, 0, 2.0, 0.0, 0.0),
    # Newspaper scan - moderate errors, some burst, stroke-loss bias
    "newspaper": (0.03, 0.05, 0.3, 2.5, 3, 2.0, 0.005, 0.002),
    # Fax quality - high errors, strong burst, heavy l/1/I confusion bias
    "fax": (0.06, 0.1, 0.2, 3.5, 5, 3.0, 0.02, 0.01),
    # Third-generation photocopy - very degraded, long burst runs
    "photocopy_3rd_gen": (0.08, 0.15, 0.15, 4.0, 5, 3.5, 0.03, 0.015),
}

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
    # Scannequin defaults
    "DEFAULT_SCANNEQUIN_RATE",
    "DEFAULT_SCANNEQUIN_BURST_ENTER",
    "DEFAULT_SCANNEQUIN_BURST_EXIT",
    "DEFAULT_SCANNEQUIN_BURST_MULTIPLIER",
    "DEFAULT_SCANNEQUIN_BIAS_K",
    "DEFAULT_SCANNEQUIN_BIAS_BETA",
    "DEFAULT_SCANNEQUIN_SPACE_DROP_RATE",
    "DEFAULT_SCANNEQUIN_SPACE_INSERT_RATE",
    "SCANNEQUIN_PRESETS",
    # Typogre defaults
    "DEFAULT_TYPOGRE_KEYBOARD",
    "DEFAULT_TYPOGRE_MOTOR_WEIGHTING",
    "DEFAULT_TYPOGRE_RATE",
    "DEFAULT_ZEEDUB_RATE",
    "MIM1C_DEFAULT_CLASSES",
    "RUSHMORE_DEFAULT_RATES",
    "ZEEDUB_DEFAULT_ZERO_WIDTHS",
]
