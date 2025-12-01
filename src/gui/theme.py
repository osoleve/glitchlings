from typing import Any, Dict
import tkinter as tk
from glitchlings.constants import (
    DEFAULT_EKKOKIN_RATE,
    DEFAULT_JARGOYLE_RATE,
    DEFAULT_MIM1C_RATE,
    DEFAULT_REDACTYL_CHAR,
    DEFAULT_REDACTYL_RATE,
    DEFAULT_SCANNEQUIN_RATE,
    DEFAULT_TYPOGRE_KEYBOARD,
    DEFAULT_TYPOGRE_RATE,
    DEFAULT_ZEEDUB_RATE,
    RUSHMORE_DEFAULT_RATES,
)
from glitchlings.util.keyboards import _KEYNEIGHBORS
from glitchlings.zoo import (
    Ekkokin,
    Hokey,
    Jargoyle,
    Mim1c,
    Pedant,
    Redactyl,
    Rushmore,
    Scannequin,
    Typogre,
    Zeedub,
)
from glitchlings.zoo.jargoyle import VALID_MODES as JARGOYLE_MODES
from glitchlings.zoo.jargoyle import list_lexeme_dictionaries
from glitchlings.zoo.pedant.stones import PedantStone
from glitchlings.zoo.rushmore import RushmoreMode

# Application info
APP_VERSION = "1.2.0"
APP_TITLE = "GLITCHLINGS TERMINAL"

# Color palette - refreshed neo-terminal colors with soft mint glow
COLORS = {
    # Primary mint glow
    "green": "#7ce7c5",
    "green_dim": "#2f6b57",
    "green_glow": "#a8ffd8",
    "green_bright": "#d8ffe9",
    "green_dark": "#0f2f2a",
    "green_muted": "#3f7a66",
    # Background - deep midnight blues to keep the terminal feel
    "black": "#050a12",
    "dark": "#0c1424",
    "darker": "#08101d",
    "panel": "#111b2e",
    # Accent colors - cool cyan with warm amber and magenta pops
    "cyan": "#65d9ff",
    "cyan_dim": "#1d5f7a",
    "cyan_bright": "#b4f0ff",
    "amber": "#f6b97b",
    "amber_dim": "#8f4f1f",
    "amber_bright": "#ffd7a1",
    "red": "#ff6b81",
    "red_dim": "#7f1d30",
    "magenta": "#ff5ec8",
    "yellow": "#f4f28b",
    # UI chrome
    "border": "#1a2f42",
    "border_bright": "#35d2a3",
    "highlight": "#14243a",
    "disabled": "#2b3b50",
}

# Font configuration - using monospace fonts for authentic terminal feel
FONTS = {
    "header": ("Consolas", 14, "bold"),
    "title": ("Consolas", 11, "bold"),
    "section": ("Consolas", 10, "bold"),
    "body": ("Consolas", 10),
    "mono": ("Consolas", 10),
    "small": ("Consolas", 9),
    "tiny": ("Consolas", 8),
    "status": ("Consolas", 9),
    "metric": ("Consolas", 9),
    "glitch_name": ("Consolas", 11, "bold"),
}

# Tooltips/help text for glitchlings
GLITCHLING_DESCRIPTIONS = {
    "Ekkokin": "Duplicates random characters for a stuttering effect",
    "Hokey": "Inserts folksy phonetic spellings and exclamations",
    "Jargoyle": "Replaces words with lexeme-based synonyms",
    "Mim1c": "Substitutes characters with visually similar homoglyphs",
    "Pedant": "Enforces strict grammatical transformations",
    "Redactyl": "Redacts words with replacement characters",
    "Rushmore": "Deletes, duplicates, or swaps adjacent tokens",
    "Scannequin": "Introduces OCR-style confusion errors",
    "Typogre": "Simulates keyboard typos with adjacent key substitutions",
    "Zeedub": "Inserts zero-width Unicode characters",
}

# Available keyboard layouts from the repo
KEYBOARD_LAYOUTS = list(_KEYNEIGHBORS.keys())

AVAILABLE_GLITCHLINGS = [
    Ekkokin,
    Hokey,
    Jargoyle,
    Mim1c,
    Pedant,
    Redactyl,
    Rushmore,
    Scannequin,
    Typogre,
    Zeedub,
]

# Parameter metadata for each glitchling (using defaults from constants.py)
GLITCHLING_PARAMS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Ekkokin": {
        "rate": {"type": "float", "default": DEFAULT_EKKOKIN_RATE, "min": 0.0, "max": 1.0},
    },
    "Hokey": {
        "rate": {"type": "float", "default": 0.3, "min": 0.0, "max": 1.0},
        "extension_min": {"type": "int", "default": 2, "min": 1, "max": 10},
        "extension_max": {"type": "int", "default": 5, "min": 1, "max": 20},
        "word_length_threshold": {"type": "int", "default": 6, "min": 1, "max": 20},
        "base_p": {"type": "float", "default": 0.45, "min": 0.0, "max": 1.0},
    },
    "Jargoyle": {
        "lexemes": {
            "type": "choice",
            "default": "synonyms",
            "choices": list_lexeme_dictionaries(),
        },
        "mode": {"type": "choice", "default": "drift", "choices": list(JARGOYLE_MODES)},
        "rate": {"type": "float", "default": DEFAULT_JARGOYLE_RATE, "min": 0.0, "max": 1.0},
    },
    "Mim1c": {
        "rate": {"type": "float", "default": DEFAULT_MIM1C_RATE, "min": 0.0, "max": 1.0},
        "classes": {"type": "text", "default": ""},
    },
    "Pedant": {
        "stone": {
            "type": "choice",
            "default": "Coeurite",
            "choices": [s.label for s in PedantStone],
        },
    },
    "Redactyl": {
        "rate": {"type": "float", "default": DEFAULT_REDACTYL_RATE, "min": 0.0, "max": 1.0},
        "replacement_char": {"type": "text", "default": DEFAULT_REDACTYL_CHAR},
        "merge_adjacent": {"type": "bool", "default": False},
        "unweighted": {"type": "bool", "default": False},
    },
    "Rushmore": {
        "modes": {
            "type": "choice",
            "default": "delete",
            "choices": [m.value for m in RushmoreMode],
        },
        "rate": {
            "type": "float",
            "default": RUSHMORE_DEFAULT_RATES["delete"],
            "min": 0.0,
            "max": 1.0,
        },
        "unweighted": {"type": "bool", "default": False},
    },
    "Scannequin": {
        "rate": {"type": "float", "default": DEFAULT_SCANNEQUIN_RATE, "min": 0.0, "max": 1.0},
    },
    "Typogre": {
        "rate": {"type": "float", "default": DEFAULT_TYPOGRE_RATE, "min": 0.0, "max": 1.0},
        "keyboard": {
            "type": "choice",
            "default": DEFAULT_TYPOGRE_KEYBOARD,
            "choices": KEYBOARD_LAYOUTS,
        },
        "shift_slip_rate": {"type": "float", "default": 0.0, "min": 0.0, "max": 1.0},
    },
    "Zeedub": {
        "rate": {"type": "float", "default": DEFAULT_ZEEDUB_RATE, "min": 0.0, "max": 1.0},
    },
}
