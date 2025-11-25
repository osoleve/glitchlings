"""Shared constants and helpers for Glitchlings benchmark utilities."""

from __future__ import annotations

import importlib
from functools import lru_cache
from types import ModuleType
from typing import Dict, List, Tuple

from glitchlings.zoo import get_glitchling_class

Descriptor = Dict[str, object]


@lru_cache(maxsize=None)
def _glitchling_module(name: str) -> ModuleType:
    """Return the module that defines the named glitchling."""
    module_path = get_glitchling_class(name).__module__
    return importlib.import_module(module_path)


def redactyl_full_block() -> str:
    """Expose the Redactyl full block character."""
    return getattr(_glitchling_module("Redactyl"), "FULL_BLOCK")


def zero_width_characters() -> List[str]:
    """Return the default zero-width characters used by Zeedub."""
    characters = getattr(_glitchling_module("Zeedub"), "_DEFAULT_ZERO_WIDTH_CHARACTERS")
    return list(characters)


def keyboard_layout(keyboard: str) -> Dict[str, List[str]]:
    """Return a mutable copy of a named keyboard layout for Typogre."""
    neighbors = getattr(_glitchling_module("Typogre"), "KEYNEIGHBORS")
    layout = getattr(neighbors, keyboard)
    return {key: list(value) for key, value in layout.items()}


OPERATION_MODULES: Dict[str, str] = {
    "reduplicate": "Rushmore",
    "delete": "Rushmore",
    "redact": "Redactyl",
    "ocr": "Scannequin",
    "zwj": "Zeedub",
    "swap_adjacent": "Rushmore",
    "typo": "Typogre",
    "hokey": "Hokey",
    "pedant": "Pedant",
    "ekkokin": "Ekkokin",
    "rushmore_combo": "Rushmore",
}


def module_for_operation(op_type: str) -> ModuleType:
    """Return the module that backs a named pipeline operation."""
    try:
        glitchling_name = OPERATION_MODULES[op_type]
    except KeyError as error:  # pragma: no cover - defensive fallback
        raise KeyError(f"Unknown operation type: {op_type}") from error
    return _glitchling_module(glitchling_name)


BASE_DESCRIPTORS: List[Descriptor] = [
    {
        "name": "Rushmore-Duplicate",
        "operation": {"type": "reduplicate", "rate": 0.01},
    },
    {"name": "Rushmore", "operation": {"type": "delete", "rate": 0.01}},
    {
        "name": "Redactyl",
        "operation": {
            "type": "redact",
            "replacement_char": redactyl_full_block(),
            "rate": 0.05,
            "merge_adjacent": True,
        },
    },
    {"name": "Scannequin", "operation": {"type": "ocr", "rate": 0.02}},
    {
        "name": "Zeedub",
        "operation": {
            "type": "zwj",
            "rate": 0.02,
            "characters": zero_width_characters(),
        },
    },
    {
        "name": "Typogre",
        "operation": {
            "type": "typo",
            "rate": 0.02,
            "keyboard": "CURATOR_QWERTY",
            "layout": keyboard_layout("CURATOR_QWERTY"),
        },
    },
]


SHORT_TEXT = (
    "One morning, when Gregor Samsa woke from troubled dreams, he found himself "
    "transformed in his bed into a horrible vermin."
)
MEDIUM_TEXT = " ".join([SHORT_TEXT] * 32)
LONG_TEXT = " ".join([SHORT_TEXT] * 256)

DEFAULT_TEXTS: Tuple[Tuple[str, str], ...] = (
    ("short", SHORT_TEXT),
    ("medium", MEDIUM_TEXT),
    ("long", LONG_TEXT),
)
DEFAULT_ITERATIONS = 25
MASTER_SEED = 151


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "baseline": "Default six-glitch pipeline mirroring the public benchmark configuration.",
    "shuffle_mix": ("Adds Rushmore's swap mode alongside deletion to stress mixed workloads."),
    "aggressive_cleanup": "Heavy redaction and deletion pass to emulate worst-case sanitisation.",
    "stealth_noise": "Lightweight typo and zero-width noise focused on subtle obfuscations.",
}


__all__ = [
    "Descriptor",
    "OPERATION_MODULES",
    "module_for_operation",
    "BASE_DESCRIPTORS",
    "DEFAULT_ITERATIONS",
    "DEFAULT_TEXTS",
    "MASTER_SEED",
    "SCENARIO_DESCRIPTIONS",
    "SHORT_TEXT",
    "MEDIUM_TEXT",
    "LONG_TEXT",
    "redactyl_full_block",
    "zero_width_characters",
    "keyboard_layout",
]
