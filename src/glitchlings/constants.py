"""Centralized defaults and shared configuration constants."""

from __future__ import annotations

from pathlib import Path

# Global configuration defaults
DEFAULT_ATTACK_SEED = 151
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")
DEFAULT_LEXICON_PRIORITY = ["vector", "wordnet"]

# Glitchling behavioural defaults
DEFAULT_EKKOKIN_RATE = 0.02
DEFAULT_EKKOKIN_WEIGHTING = "flat"
MIM1C_DEFAULT_CLASSES: tuple[str, ...] = ("LATIN", "GREEK", "CYRILLIC", "COMMON")
RUSHMORE_DEFAULT_RATES = {
    "delete": 0.01,
    "duplicate": 0.01,
    "swap": 0.05,
}
ZEEDUB_DEFAULT_ZERO_WIDTHS: tuple[str, ...] = (
    "\u200b",
    "\u200c",
    "\u200d",
    "\ufeff",
)

__all__ = [
    "DEFAULT_ATTACK_SEED",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_EKKOKIN_RATE",
    "DEFAULT_EKKOKIN_WEIGHTING",
    "DEFAULT_LEXICON_PRIORITY",
    "MIM1C_DEFAULT_CLASSES",
    "RUSHMORE_DEFAULT_RATES",
    "ZEEDUB_DEFAULT_ZERO_WIDTHS",
]
