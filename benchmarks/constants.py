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
    "homoglyph": "Mim1c",
    "synonym": "Jargoyle",
    "homophone": "Ekkokin",
}


PEDANT_STONES: Dict[str, str] = {
    "whomst": "Whom Stone",
    "fewerling": "Fewerite",
    "aetheria": "Coeurite",
    "apostrofae": "Curlite",
    "subjunic": "Subjunctite",
    "commama": "Oxfordium",
    "kiloa": "Metricite",
    "correctopus": "Orthogonite",
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
VERY_LONG_TEXT = " ".join([SHORT_TEXT] * 2048)

DEFAULT_TEXTS: Tuple[Tuple[str, str], ...] = (
    ("short", SHORT_TEXT),
    ("medium", MEDIUM_TEXT),
    ("long", LONG_TEXT),
    ("very_long", VERY_LONG_TEXT),
)
DEFAULT_ITERATIONS = 25
MASTER_SEED = 151


SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "baseline": "Default six-glitch pipeline mirroring the public benchmark configuration.",
    "shuffle_mix": "Adds Rushmore's swap mode alongside deletion to stress mixed workloads.",
    "aggressive_cleanup": "Heavy redaction and deletion pass to emulate worst-case sanitisation.",
    "stealth_noise": "Lightweight typo and zero-width noise focused on subtle obfuscations.",
    # Individual glitchling scenarios
    "typogre_only": "Typogre-only benchmark for keyboard neighbor typo injection.",
    "rushmore_delete": "Rushmore delete-only benchmark for word deletion.",
    "rushmore_duplicate": "Rushmore duplicate-only benchmark for word reduplication.",
    "rushmore_swap": "Rushmore swap-only benchmark for adjacent word swapping.",
    "redactyl_only": "Redactyl-only benchmark for character redaction.",
    "scannequin_only": "Scannequin-only benchmark for OCR confusion injection.",
    "zeedub_only": "Zeedub-only benchmark for zero-width character injection.",
    "mim1c_only": "Mim1c-only benchmark for homoglyph substitution.",
    "ekkokin_only": "Ekkokin-only benchmark for homophone substitution.",
    "hokey_only": "Hokey-only benchmark for expressive lengthening.",
    "jargoyle_only": "Jargoyle-only benchmark for dictionary-based synonym substitution.",
    # Pedant evolution scenarios
    "pedant_whomst": "Pedant Whomst benchmark for who→whom correction.",
    "pedant_fewerling": "Pedant Fewerling benchmark for less→fewer correction.",
    "pedant_aetheria": "Pedant Aetheria benchmark for ligature and diaeresis restoration.",
    "pedant_apostrofae": "Pedant Apostrofae benchmark for curly quote normalization.",
    "pedant_subjunic": "Pedant Subjunic benchmark for subjunctive correction.",
    "pedant_commama": "Pedant Commama benchmark for Oxford comma insertion.",
    "pedant_kiloa": "Pedant Kiloa benchmark for imperial→metric conversion.",
    "pedant_correctopus": "Pedant Correctopus benchmark for uppercase transformation.",
}


__all__ = [
    "Descriptor",
    "OPERATION_MODULES",
    "PEDANT_STONES",
    "module_for_operation",
    "BASE_DESCRIPTORS",
    "DEFAULT_ITERATIONS",
    "DEFAULT_TEXTS",
    "MASTER_SEED",
    "SCENARIO_DESCRIPTIONS",
    "SHORT_TEXT",
    "MEDIUM_TEXT",
    "LONG_TEXT",
    "VERY_LONG_TEXT",
    "redactyl_full_block",
    "zero_width_characters",
    "keyboard_layout",
]
