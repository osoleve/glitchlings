from typing import Any, Dict

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

# Shared GUI defaults
DEFAULT_TOKENIZERS = ("cl100k_base", "gpt2", "bert-base-uncased")
SCAN_PRESET_OPTIONS = ("10", "100", "1000", "10000")

# Tooltips/help text for glitchlings
GLITCHLING_DESCRIPTIONS = {
    "Ekkokin": "Homophones",
    "Hokey": "Emphatic lengthening",
    "Jargoyle": "Thesaurus abuse",
    "Mim1c": "Confusables",
    "Pedant": "",
    "Redactyl": "Redaction",
    "Rushmore": "Hasty editing errors",
    "Scannequin": "OCR errors",
    "Typogre": "Keyboard-aware typos",
    "Zeedub": "Invisible characters",
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
