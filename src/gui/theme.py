from __future__ import annotations

from tkinter import ttk
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

# Application info
APP_VERSION = "1.3.0"
APP_TITLE = "GLITCHLINGS TERMINAL"

# Color palette - refined neo-terminal colors with balanced contrast
COLORS = {
    # Primary mint/green - refined for better readability
    "green": "#4ade80",
    "green_dim": "#22543d",
    "green_glow": "#86efac",
    "green_bright": "#bbf7d0",
    "green_dark": "#14532d",
    "green_muted": "#166534",
    # Background - layered depth with subtle warmth
    "black": "#0c1117",
    "dark": "#161b22",
    "darker": "#090c10",
    "panel": "#1c2128",
    "surface": "#21262d",
    # Accent colors - harmonized palette
    "cyan": "#7dd3fc",
    "cyan_dim": "#155e75",
    "cyan_bright": "#a5f3fc",
    "amber": "#fbbf24",
    "amber_dim": "#92400e",
    "amber_bright": "#fcd34d",
    "red": "#f87171",
    "red_dim": "#7f1d1d",
    "magenta": "#f472b6",
    "purple": "#a78bfa",
    "yellow": "#fde047",
    # UI chrome - refined borders and highlights
    "border": "#30363d",
    "border_bright": "#4ade80",
    "border_subtle": "#21262d",
    "highlight": "#1f2937",
    "hover": "#2d333b",
    "disabled": "#484f58",
    "text_muted": "#8b949e",
}

# Font configuration - using monospace fonts for authentic terminal feel
# Cascading font fallbacks for cross-platform compatibility
_MONO_FONTS = ("Cascadia Code", "JetBrains Mono", "Consolas", "Monaco", "monospace")

FONTS: Dict[str, Any] = {
    "header": (_MONO_FONTS, 15, "bold"),
    "title": (_MONO_FONTS, 11, "bold"),
    "section": (_MONO_FONTS, 10, "bold"),
    "body": (_MONO_FONTS, 10),
    "mono": (_MONO_FONTS, 10),
    "small": (_MONO_FONTS, 9),
    "tiny": (_MONO_FONTS, 8),
    "status": (_MONO_FONTS, 9),
    "metric": (_MONO_FONTS, 9),
    "glitch_name": (_MONO_FONTS, 11, "bold"),
    "button": (_MONO_FONTS, 9, "bold"),
}

MENU_STYLES = {
    "bg": COLORS["dark"],
    "fg": COLORS["green"],
    "activebackground": COLORS["highlight"],
    "activeforeground": COLORS["green_bright"],
    "font": FONTS["body"],
}

STYLE_CONFIGS: Dict[str, Dict[str, Any]] = {
    ".": {"background": COLORS["black"], "foreground": COLORS["green"]},
    "TFrame": {"background": COLORS["black"], "bordercolor": COLORS["border"]},
    "Panel.TFrame": {"background": COLORS["dark"], "bordercolor": COLORS["border"]},
    "Surface.TFrame": {"background": COLORS["surface"], "bordercolor": COLORS["border"]},
    "TLabel": {
        "background": COLORS["black"],
        "foreground": COLORS["green"],
        "font": FONTS["body"],
    },
    "Muted.TLabel": {
        "background": COLORS["black"],
        "foreground": COLORS["text_muted"],
        "font": FONTS["small"],
    },
    "Header.TLabel": {
        "background": COLORS["black"],
        "foreground": COLORS["green_bright"],
        "font": FONTS["title"],
    },
    "TLabelframe": {
        "background": COLORS["black"],
        "foreground": COLORS["green"],
        "bordercolor": COLORS["border"],
        "relief": "solid",
        "borderwidth": 1,
    },
    "TLabelframe.Label": {
        "background": COLORS["black"],
        "foreground": COLORS["cyan"],
        "font": FONTS["title"],
        "padding": (4, 2),
    },
    "TButton": {
        "background": COLORS["surface"],
        "foreground": COLORS["green"],
        "bordercolor": COLORS["border"],
        "font": FONTS["button"],
        "padding": (12, 6),
        "focuscolor": COLORS["green_dim"],
    },
    "Primary.TButton": {
        "background": COLORS["green_dark"],
        "foreground": COLORS["green_bright"],
        "bordercolor": COLORS["green_muted"],
        "font": FONTS["button"],
        "padding": (14, 7),
    },
    "Danger.TButton": {
        "background": COLORS["red_dim"],
        "foreground": COLORS["red"],
        "bordercolor": COLORS["red_dim"],
        "font": FONTS["button"],
        "padding": (12, 6),
    },
    "TCheckbutton": {
        "background": COLORS["black"],
        "foreground": COLORS["green"],
        "font": FONTS["body"],
    },
    "TRadiobutton": {
        "background": COLORS["black"],
        "foreground": COLORS["green"],
        "font": FONTS["body"],
    },
    "TEntry": {
        "fieldbackground": COLORS["darker"],
        "foreground": COLORS["amber"],
        "insertcolor": COLORS["green_bright"],
        "bordercolor": COLORS["border"],
        "font": FONTS["mono"],
        "padding": (4, 2),
    },
    "TSpinbox": {
        "fieldbackground": COLORS["darker"],
        "foreground": COLORS["amber"],
        "arrowcolor": COLORS["green"],
        "bordercolor": COLORS["border"],
        "font": FONTS["mono"],
        "padding": (4, 2),
    },
    "TCombobox": {
        "fieldbackground": COLORS["darker"],
        "foreground": COLORS["amber"],
        "arrowcolor": COLORS["green"],
        "bordercolor": COLORS["border"],
        "font": FONTS["mono"],
        "padding": (4, 2),
    },
    "TScrollbar": {
        "background": COLORS["dark"],
        "troughcolor": COLORS["darker"],
        "bordercolor": COLORS["border"],
        "arrowcolor": COLORS["green"],
        "gripcount": 0,
    },
    "TPanedwindow": {"background": COLORS["green_dim"]},
    "Treeview": {
        "background": COLORS["darker"],
        "foreground": COLORS["green"],
        "fieldbackground": COLORS["darker"],
        "bordercolor": COLORS["border"],
        "font": FONTS["metric"],
        "rowheight": 24,
    },
    "Treeview.Heading": {
        "background": COLORS["dark"],
        "foreground": COLORS["cyan"],
        "font": FONTS["body"],
        "bordercolor": COLORS["border"],
        "padding": (4, 3),
    },
    "TNotebook": {
        "background": COLORS["black"],
        "bordercolor": COLORS["border"],
        "tabmargins": (4, 6, 4, 2),
    },
    "TNotebook.Tab": {
        "background": COLORS["surface"],
        "foreground": COLORS["text_muted"],
        "padding": (14, 6),
        "focuscolor": COLORS["green_dim"],
    },
    "TSeparator": {"background": COLORS["border"]},
    "TProgressbar": {
        "background": COLORS["green"],
        "troughcolor": COLORS["darker"],
        "bordercolor": COLORS["border"],
    },
}

STYLE_MAPS: Dict[str, Dict[str, Any]] = {
    "TButton": {
        "background": [("active", COLORS["highlight"]), ("pressed", COLORS["green_dark"])],
        "foreground": [("active", COLORS["green_bright"]), ("pressed", COLORS["green_glow"])],
        "bordercolor": [("active", COLORS["border_bright"])],
    },
    "Primary.TButton": {
        "background": [("active", COLORS["green_dim"]), ("pressed", COLORS["green"])],
        "foreground": [("active", COLORS["green_glow"]), ("pressed", COLORS["black"])],
    },
    "TCheckbutton": {
        "background": [("active", COLORS["black"])],
        "foreground": [("active", COLORS["green_bright"])],
    },
    "TRadiobutton": {
        "background": [("active", COLORS["black"])],
        "foreground": [("active", COLORS["green_bright"])],
    },
    "TEntry": {"bordercolor": [("focus", COLORS["border_bright"])]},
    "TSpinbox": {
        "bordercolor": [("focus", COLORS["border_bright"])],
        "arrowcolor": [("active", COLORS["green_bright"])],
    },
    "TCombobox": {
        "fieldbackground": [("readonly", COLORS["darker"]), ("focus", COLORS["dark"])],
        "foreground": [("readonly", COLORS["amber"])],
        "selectbackground": [("readonly", COLORS["green_dim"])],
        "selectforeground": [("readonly", COLORS["black"])],
        "bordercolor": [("focus", COLORS["border_bright"])],
        "arrowcolor": [("active", COLORS["green_bright"])],
    },
    "TScrollbar": {
        "background": [("active", COLORS["green_dim"]), ("pressed", COLORS["green_dark"])],
        "arrowcolor": [("active", COLORS["green_bright"])],
    },
    "Treeview": {
        "background": [("selected", COLORS["highlight"])],
        "foreground": [("selected", COLORS["green_bright"])],
    },
    "Treeview.Heading": {
        "background": [("active", COLORS["green_dim"])],
        "foreground": [("active", COLORS["green_bright"])],
    },
    "TNotebook.Tab": {
        "background": [("selected", COLORS["dark"]), ("active", COLORS["hover"])],
        "foreground": [("selected", COLORS["green_bright"]), ("active", COLORS["green"])],
    },
}


def apply_theme_styles(style: ttk.Style | None = None) -> ttk.Style:
    """Configure and return the shared ttk style for the GUI."""
    style = style or ttk.Style()
    style.theme_use("clam")

    for style_name, options in STYLE_CONFIGS.items():
        style.configure(style_name, **options)

    for style_name, options in STYLE_MAPS.items():
        style.map(style_name, **options)

    return style


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
