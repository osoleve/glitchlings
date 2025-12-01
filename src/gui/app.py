"""Glitchlings GUI application.

A vector terminal-styled interface for corrupting text with glitchlings.
Features a retro CRT aesthetic with phosphor green displays and scanline effects.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from typing import Any

from glitchlings.attack import (
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from glitchlings.attack.tokenization import resolve_tokenizer
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
    Gaggle,
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

# =============================================================
# Vector Terminal Theme - Old School CRT Aesthetic
# =============================================================

# Color palette - Classic vector phosphor colors
COLORS = {
    # Primary vector green (P1 phosphor)
    "green": "#33ff33",
    "green_dim": "#1a4a1a",
    "green_glow": "#44ff44",
    "green_bright": "#66ff66",
    "green_dark": "#0d2f0d",
    # Background - deep CRT black with subtle blue tint
    "black": "#080a08",
    "dark": "#101410",
    "darker": "#040604",
    # Accent colors - CRT phosphor palette
    "cyan": "#00e8e8",
    "cyan_dim": "#006666",
    "amber": "#ffbb33",
    "amber_dim": "#664400",
    "red": "#ff4444",
    "red_dim": "#661111",
    "magenta": "#ff44ff",
    # UI chrome
    "border": "#224422",
    "border_bright": "#33aa33",
    "highlight": "#115511",
}

# Font configuration - using monospace fonts for authentic terminal feel
FONTS = {
    "header": ("Consolas", 13, "bold"),
    "title": ("Consolas", 11, "bold"),
    "body": ("Consolas", 10),
    "mono": ("Consolas", 10),
    "small": ("Consolas", 9),
    "tiny": ("Consolas", 8),
    "status": ("Consolas", 9, "italic"),
}

# Application info
APP_VERSION = "1.0.0"
APP_TITLE = "GLITCHLINGS TERMINAL"

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
GLITCHLING_PARAMS: dict[str, dict[str, dict[str, Any]]] = {
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


class App(tk.Tk):
    """Main application window with vector terminal theme."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"༼ つ ◕_◕ ༽つ {APP_TITLE} v{APP_VERSION}")
        self.geometry("1280x860")
        self.minsize(1000, 700)

        # Apply vector terminal theme
        self._apply_theme()

        self.main_frame: MainFrame

        # Create menu bar
        self._create_menu_bar()

        # Create main frame
        self.main_frame = MainFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def _apply_theme(self) -> None:
        """Apply the vector terminal CRT aesthetic."""
        # Configure root window
        self.configure(bg=COLORS["black"])

        # Create custom ttk style
        style = ttk.Style()
        style.theme_use("clam")

        # Configure main backgrounds
        style.configure(".", background=COLORS["black"], foreground=COLORS["green"])

        # Frame styling
        style.configure(
            "TFrame",
            background=COLORS["black"],
            bordercolor=COLORS["border"],
        )

        style.configure(
            "Panel.TFrame",
            background=COLORS["dark"],
            bordercolor=COLORS["border"],
        )

        # Label styling
        style.configure(
            "TLabel",
            background=COLORS["black"],
            foreground=COLORS["green"],
            font=FONTS["body"],
        )

        style.configure(
            "Header.TLabel",
            background=COLORS["black"],
            foreground=COLORS["green_bright"],
            font=FONTS["title"],
        )

        # LabelFrame styling - vector terminal panel
        style.configure(
            "TLabelframe",
            background=COLORS["black"],
            foreground=COLORS["green"],
            bordercolor=COLORS["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TLabelframe.Label",
            background=COLORS["black"],
            foreground=COLORS["cyan"],
            font=FONTS["title"],
            padding=(4, 2),
        )

        # Button styling - vector green glow effect
        style.configure(
            "TButton",
            background=COLORS["dark"],
            foreground=COLORS["green"],
            bordercolor=COLORS["border"],
            font=FONTS["body"],
            padding=(10, 5),
            focuscolor=COLORS["green_dim"],
        )
        style.map(
            "TButton",
            background=[
                ("active", COLORS["highlight"]),
                ("pressed", COLORS["green_dark"]),
            ],
            foreground=[
                ("active", COLORS["green_bright"]),
                ("pressed", COLORS["green_glow"]),
            ],
            bordercolor=[
                ("active", COLORS["border_bright"]),
            ],
        )

        # Primary action button style
        style.configure(
            "Primary.TButton",
            background=COLORS["green_dark"],
            foreground=COLORS["green_bright"],
            bordercolor=COLORS["green_dim"],
            font=FONTS["body"],
            padding=(12, 6),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", COLORS["green_dim"]),
                ("pressed", COLORS["green"]),
            ],
            foreground=[
                ("active", COLORS["green_glow"]),
                ("pressed", COLORS["black"]),
            ],
        )

        # Checkbutton styling
        style.configure(
            "TCheckbutton",
            background=COLORS["black"],
            foreground=COLORS["green"],
            font=FONTS["body"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", COLORS["black"])],
            foreground=[("active", COLORS["green_bright"])],
        )

        # Radiobutton styling
        style.configure(
            "TRadiobutton",
            background=COLORS["black"],
            foreground=COLORS["green"],
            font=FONTS["body"],
        )
        style.map(
            "TRadiobutton",
            background=[("active", COLORS["black"])],
            foreground=[("active", COLORS["green_bright"])],
        )

        # Entry styling
        style.configure(
            "TEntry",
            fieldbackground=COLORS["darker"],
            foreground=COLORS["amber"],
            insertcolor=COLORS["green_bright"],
            bordercolor=COLORS["border"],
            font=FONTS["mono"],
            padding=(4, 2),
        )
        style.map(
            "TEntry",
            bordercolor=[
                ("focus", COLORS["border_bright"]),
            ],
        )

        # Spinbox styling
        style.configure(
            "TSpinbox",
            fieldbackground=COLORS["darker"],
            foreground=COLORS["amber"],
            arrowcolor=COLORS["green"],
            bordercolor=COLORS["border"],
            font=FONTS["mono"],
            padding=(4, 2),
        )
        style.map(
            "TSpinbox",
            bordercolor=[
                ("focus", COLORS["border_bright"]),
            ],
            arrowcolor=[
                ("active", COLORS["green_bright"]),
            ],
        )

        # Combobox styling
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["darker"],
            foreground=COLORS["amber"],
            arrowcolor=COLORS["green"],
            bordercolor=COLORS["border"],
            font=FONTS["mono"],
            padding=(4, 2),
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", COLORS["darker"]),
                ("focus", COLORS["dark"]),
            ],
            foreground=[
                ("readonly", COLORS["amber"]),
            ],
            selectbackground=[
                ("readonly", COLORS["green_dim"]),
            ],
            selectforeground=[
                ("readonly", COLORS["black"]),
            ],
            bordercolor=[
                ("focus", COLORS["border_bright"]),
            ],
            arrowcolor=[
                ("active", COLORS["green_bright"]),
            ],
        )

        # Scrollbar styling
        style.configure(
            "TScrollbar",
            background=COLORS["dark"],
            troughcolor=COLORS["darker"],
            bordercolor=COLORS["border"],
            arrowcolor=COLORS["green"],
            gripcount=0,
        )
        style.map(
            "TScrollbar",
            background=[
                ("active", COLORS["green_dim"]),
                ("pressed", COLORS["green_dark"]),
            ],
            arrowcolor=[
                ("active", COLORS["green_bright"]),
            ],
        )

        # PanedWindow styling
        style.configure(
            "TPanedwindow",
            background=COLORS["green_dim"],
        )

        # Treeview styling - vector data grid
        style.configure(
            "Treeview",
            background=COLORS["darker"],
            foreground=COLORS["green"],
            fieldbackground=COLORS["darker"],
            bordercolor=COLORS["border"],
            font=FONTS["mono"],
            rowheight=22,
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["dark"],
            foreground=COLORS["cyan"],
            font=FONTS["body"],
            bordercolor=COLORS["border"],
            padding=(4, 3),
        )
        style.map(
            "Treeview",
            background=[
                ("selected", COLORS["highlight"]),
            ],
            foreground=[
                ("selected", COLORS["green_bright"]),
            ],
        )
        style.map(
            "Treeview.Heading",
            background=[
                ("active", COLORS["green_dim"]),
            ],
            foreground=[
                ("active", COLORS["green_bright"]),
            ],
        )

        # Notebook styling (if used)
        style.configure(
            "TNotebook",
            background=COLORS["black"],
            bordercolor=COLORS["border"],
            tabmargins=(2, 4, 2, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=COLORS["dark"],
            foreground=COLORS["green"],
            padding=(12, 5),
            focuscolor=COLORS["green_dim"],
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", COLORS["black"]),
                ("active", COLORS["green_dark"]),
            ],
            foreground=[
                ("selected", COLORS["green_bright"]),
                ("active", COLORS["green_glow"]),
            ],
        )

        # Separator styling
        style.configure(
            "TSeparator",
            background=COLORS["border"],
        )

        # Progressbar styling (for future use)
        style.configure(
            "TProgressbar",
            background=COLORS["green"],
            troughcolor=COLORS["darker"],
            bordercolor=COLORS["border"],
        )

    def _create_menu_bar(self) -> None:
        menubar = tk.Menu(
            self,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["body"],
            borderwidth=0,
            relief=tk.FLAT,
        )
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["body"],
            borderwidth=1,
            relief=tk.SOLID,
        )
        menubar.add_cascade(label="▒ FILE", menu=file_menu)
        file_menu.add_command(label="New Session", command=self._new_session, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save...", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Alt+F4")

        # Edit menu
        edit_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["body"],
            borderwidth=1,
            relief=tk.SOLID,
        )
        menubar.add_cascade(label="▒ EDIT", menu=edit_menu)
        edit_menu.add_command(
            label="Copy Input", command=self._copy_input, accelerator="Ctrl+Shift+C"
        )
        edit_menu.add_command(label="Copy Output", command=self._copy_output)
        edit_menu.add_command(
            label="Paste to Input", command=self._paste_input, accelerator="Ctrl+Shift+V"
        )

        # View menu
        view_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["body"],
            borderwidth=1,
            relief=tk.SOLID,
        )
        menubar.add_cascade(label="▒ VIEW", menu=view_menu)
        view_menu.add_command(label="Reset Layout", command=self._reset_layout)

        # Help menu
        help_menu = tk.Menu(
            menubar,
            tearoff=0,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["body"],
            borderwidth=1,
            relief=tk.SOLID,
        )
        menubar.add_cascade(label="▒ HELP", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Bind keyboard shortcuts
        self.bind("<Control-n>", lambda e: self._new_session())
        self.bind("<Control-o>", lambda e: self._open_file())
        self.bind("<Control-s>", lambda e: self._save_file())

    def _new_session(self) -> None:
        self.main_frame.clear_all()

    def _open_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            self.main_frame.set_input(content)

    def _save_file(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.main_frame.get_output())

    def _copy_input(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.main_frame.get_input())

    def _copy_output(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.main_frame.get_output())

    def _paste_input(self) -> None:
        try:
            content = self.clipboard_get()
            self.main_frame.set_input(content)
        except tk.TclError:
            pass

    def _reset_layout(self) -> None:
        pass  # Could be used to reset sash positions

    def _show_about(self) -> None:
        # Create custom about dialog with vector theme
        about = tk.Toplevel(self)
        about.title("ABOUT")
        about.geometry("420x340")
        about.configure(bg=COLORS["black"])
        about.resizable(False, False)

        # Center the dialog
        about.transient(self)
        about.grab_set()

        # Border frame - double border effect
        outer_border = tk.Frame(about, bg=COLORS["green_dim"], padx=2, pady=2)
        outer_border.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        border = tk.Frame(outer_border, bg=COLORS["border"], padx=1, pady=1)
        border.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(border, bg=COLORS["black"])
        inner.pack(fill=tk.BOTH, expand=True)

        # ASCII art header with scanline effect
        header_text = """
╔══════════════════════════════════════╗
║  ༼ つ ◕_◕ ༽つ  GLITCHLINGS       ║
║     ▒▒▒ TERMINAL v{ver:<9} ▒▒▒    ║
╚══════════════════════════════════════╝
""".format(ver=APP_VERSION)
        header = tk.Label(
            inner,
            text=header_text,
            font=("Consolas", 10),
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
            justify=tk.CENTER,
        )
        header.pack(pady=(8, 0))

        # Description
        desc = tk.Label(
            inner,
            text="A vector terminal interface for\ncorrupting text with glitchlings.\n\n"
            "Summon creatures from the digital void\nto transform your tokens into chaos.",
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            justify=tk.CENTER,
        )
        desc.pack(pady=12)

        # Decorative separator
        sep_frame = tk.Frame(inner, bg=COLORS["black"])
        sep_frame.pack(fill=tk.X, padx=30, pady=5)
        tk.Frame(sep_frame, bg=COLORS["green_dim"], height=1).pack(fill=tk.X)

        # Status line
        status = tk.Label(
            inner,
            text="▒ SYSTEM OPERATIONAL ▒",
            font=FONTS["status"],
            fg=COLORS["cyan"],
            bg=COLORS["black"],
        )
        status.pack(pady=8)

        # Close button
        close_btn = tk.Button(
            inner,
            text="[ CLOSE ]",
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=1,
            relief=tk.SOLID,
            padx=16,
            pady=4,
            command=about.destroy,
        )
        close_btn.pack(pady=15)

        # Bind escape to close
        about.bind("<Escape>", lambda e: about.destroy())


# UI Layout Reference (ASCII wireframe):
#   ┌──────────────────────────────────────────────────────────────────────────────┐
#   │                                                                            x │
#   │──────────────────────────────────────────────────────────────────────────────│
#   │ File  Edit  View  Help                                        Seed  [ 417 ]  │
#   │──────────────────┬─┬─────────────────────────────────────────────────────────│
#   │ Glitchlings      │▲│ Input                                                   │
#   │                  │=│ ┌─────────────────────────────────────────────────────┐ │
#   │ ► Ekkokin        │=│ │The quick brown fox...                               │ │
#   │                  │=│ │                                                     │ │
#   │ ► Hokey          │=│ │                                                     │ │
#   │                  │ │ │                                                     │ │
#   │ ▼ Jargoyle       │ │ └─────────────────────────────────────────────────────┘ │
#   │┌────────────────┐│ │                                                         │
#   ││Lexemes         ││ │  Output                                                 │
#   ││ [Corporate ▼]  ││ │ ┌─────────────────────────────────────────────────────┐ │
#   ││                ││ │ │ .....................                               │ │
#   ││Mode            ││ │ │                                                     │ │
#   ││ [Drift     ▼]  ││ │ │                                                     │ │
#   ││                ││ │ │                                                     │ │
#   ││Rate ▲ 1.0% ▼   ││ │ │                                                     │ │
#   │└────────────────┘│▼│ └─────────────────────────────────────────────────────┘ │
#   │──────────────────┼─┤                                                         │
#   │ Tokenizers       │▲│  Token Diff [  ID  > Label  ]  [ bert ▼ ]               │
#   │                  │ │ ┌─────────────────────────────────────────────────────┐ │
#   │                  │ │ │ ....................                                │ │
#   │  + tiktoken_100k │ │ │                                                     │ │
#   │                  │ │ │                                                     │ │
#   │  + gpt2          │ │ │                                                     │ │
#   │                  │ │ │                                                     │ │
#   │  + bert          │ │ └─────────────────────────────────────────────────────┘ │
#   │                  │ │  Metrics                                                │
#   │  + smollm3       │ │ ┌─────────────────────────────────────────────────────┐ │
#   │                  │ │ │           | tiktoken | gpt2 | bert | smollm3        │ │
#   │  Add New [ + ]   │ │ │  Metric11 |          |      |      |                │ │
#   │                  │ │ │  Metric 2 |          |      |      |                │ │
#   │                  │ │ │  Metric 3 |          |      |      |                │ │
#   │                  │ │ │  Metric 4 |          |      |      |                │ │
#   │                  │▼│ └─────────────────────────────────────────────────────┘ │
#   └──────────────────┴─┴─────────────────────────────────────────────────────────┘


class GlitchlingFrame(tk.Frame):
    """Custom frame that stores glitchling-specific attributes."""

    def __init__(self, parent: tk.Frame | tk.Canvas, name: str) -> None:
        super().__init__(parent, bg=COLORS["black"])
        self.glitchling_name = name
        self.expand_btn: tk.Button | None = None
        self.param_frame: tk.Frame | None = None


class GlitchlingPanel(ttk.Frame):
    """Panel showing expandable glitchling list with parameter controls."""

    def __init__(self, parent: ttk.PanedWindow, on_change_callback: Any) -> None:
        super().__init__(parent)
        self.on_change = on_change_callback
        self.expanded: dict[str, bool] = {}
        self.enabled: dict[str, tk.BooleanVar] = {}
        self.param_widgets: dict[str, dict[str, Any]] = {}
        self.frames: dict[str, GlitchlingFrame] = {}

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header with vector terminal styling
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        header_inner = tk.Frame(header_frame, bg=COLORS["dark"])
        header_inner.pack(fill=tk.X)

        header = tk.Label(
            header_inner,
            text="▒▒▒ GLITCHLINGS ▒▒▒",
            font=FONTS["title"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=10,
            pady=5,
        )
        header.pack(fill=tk.X)

        # Scrollable frame for glitchlings with border
        scroll_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.canvas = tk.Canvas(
            scroll_container,
            highlightthickness=0,
            bg=COLORS["black"],
        )
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["black"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Create glitchling entries
        for cls in AVAILABLE_GLITCHLINGS:
            self._create_glitchling_entry(cls)

    def _on_mousewheel(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _create_glitchling_entry(self, cls: type) -> None:
        name = cls.__name__
        self.expanded[name] = False
        self.enabled[name] = tk.BooleanVar(value=False)
        self.param_widgets[name] = {}

        # Main frame for this glitchling
        frame = GlitchlingFrame(self.scrollable_frame, name)
        frame.pack(fill=tk.X, padx=2, pady=1)
        self.frames[name] = frame

        # Header row with expand button and checkbox
        header_frame = tk.Frame(frame, bg=COLORS["black"])
        header_frame.pack(fill=tk.X)

        # Expand/collapse button - vector style
        expand_btn = tk.Button(
            header_frame,
            text="▸",
            width=2,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda n=name: self._toggle_expand(n),  # type: ignore[misc]
        )
        expand_btn.pack(side=tk.LEFT, padx=(2, 4))
        frame.expand_btn = expand_btn

        # Enable checkbox - vector style
        check = tk.Checkbutton(
            header_frame,
            text=name,
            variable=self.enabled[name],
            command=self.on_change,
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        check.pack(side=tk.LEFT, padx=2)

        # Parameter frame (initially hidden)
        param_frame = tk.Frame(frame, bg=COLORS["black"])
        frame.param_frame = param_frame

        # Create parameter widgets
        if name in GLITCHLING_PARAMS:
            for param_name, param_info in GLITCHLING_PARAMS[name].items():
                self._create_param_widget(param_frame, name, param_name, param_info)

    def _create_param_widget(
        self,
        parent: tk.Frame,
        glitchling_name: str,
        param_name: str,
        param_info: dict[str, Any],
    ) -> None:
        row = tk.Frame(parent, bg=COLORS["black"])
        row.pack(fill=tk.X, padx=20, pady=2)

        label = tk.Label(
            row,
            text=param_name,
            width=15,
            anchor="w",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        )
        label.pack(side=tk.LEFT)

        param_type = param_info["type"]

        if param_type == "float":
            var = tk.DoubleVar(value=param_info["default"])
            spinbox = ttk.Spinbox(
                row,
                from_=param_info.get("min", 0.0),
                to=param_info.get("max", 1.0),
                increment=0.01,
                textvariable=var,
                width=10,
                command=self.on_change,
            )
            spinbox.pack(side=tk.LEFT, padx=5)
            spinbox.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var

        elif param_type == "int":
            var_int = tk.IntVar(value=param_info["default"])
            spinbox = ttk.Spinbox(
                row,
                from_=param_info.get("min", 0),
                to=param_info.get("max", 100),
                increment=1,
                textvariable=var_int,
                width=10,
                command=self.on_change,
            )
            spinbox.pack(side=tk.LEFT, padx=5)
            spinbox.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_int

        elif param_type == "choice":
            var_str = tk.StringVar(value=param_info["default"])
            combo = ttk.Combobox(
                row,
                textvariable=var_str,
                values=param_info["choices"],
                width=12,
                state="readonly",
            )
            combo.pack(side=tk.LEFT, padx=5)
            combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_str

        elif param_type == "bool":
            var_bool = tk.BooleanVar(value=param_info["default"])
            check = ttk.Checkbutton(row, variable=var_bool, command=self.on_change)
            check.pack(side=tk.LEFT, padx=5)
            self.param_widgets[glitchling_name][param_name] = var_bool

        elif param_type == "text":
            var_text = tk.StringVar(value=param_info["default"])
            entry = ttk.Entry(row, textvariable=var_text, width=15)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_text

    def _toggle_expand(self, name: str) -> None:
        self.expanded[name] = not self.expanded[name]
        frame = self.frames[name]

        if frame.expand_btn is None or frame.param_frame is None:
            return

        if self.expanded[name]:
            frame.expand_btn.config(text="▾")
            frame.param_frame.pack(fill=tk.X, after=frame.winfo_children()[0])
        else:
            frame.expand_btn.config(text="▸")
            frame.param_frame.pack_forget()

    def get_enabled_glitchlings(self) -> list[tuple[type, dict[str, Any]]]:
        """Return list of (class, params) for enabled glitchlings."""
        result: list[tuple[type, dict[str, Any]]] = []
        for cls in AVAILABLE_GLITCHLINGS:
            name = cls.__name__
            if self.enabled[name].get():
                params: dict[str, Any] = {}
                for param_name, var in self.param_widgets[name].items():
                    params[param_name] = var.get()
                result.append((cls, params))
        return result


class TokenizerPanel(ttk.Frame):
    """Panel for managing tokenizers."""

    def __init__(self, parent: ttk.PanedWindow, on_change_callback: Any) -> None:
        super().__init__(parent)
        self.on_change = on_change_callback
        self.tokenizers: list[str] = []
        self.tokenizer_vars: dict[str, tk.BooleanVar] = {}

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header with vector terminal styling
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        header_inner = tk.Frame(header_frame, bg=COLORS["dark"])
        header_inner.pack(fill=tk.X)

        header = tk.Label(
            header_inner,
            text="▒▒▒ TOKENIZERS ▒▒▒",
            font=FONTS["title"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=10,
            pady=5,
        )
        header.pack(fill=tk.X)

        # Scrollable frame with border
        scroll_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.canvas = tk.Canvas(
            scroll_container,
            highlightthickness=0,
            bg=COLORS["black"],
        )
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["black"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Default tokenizers (tiktoken + HuggingFace)
        default_tokenizers = ["cl100k_base", "gpt2", "bert-base-uncased"]
        for tok in default_tokenizers:
            self._add_tokenizer(tok)

        # Add new tokenizer row
        add_frame = tk.Frame(self.scrollable_frame, bg=COLORS["black"])
        add_frame.pack(fill=tk.X, padx=5, pady=8)

        self.new_tok_entry = tk.Entry(
            add_frame,
            width=15,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        self.new_tok_entry.pack(side=tk.LEFT, padx=2)
        self.new_tok_entry.bind("<Return>", lambda e: self._add_new_tokenizer())

        add_btn = tk.Button(
            add_frame,
            text="+",
            width=3,
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=1,
            relief=tk.SOLID,
            cursor="hand2",
            command=self._add_new_tokenizer,
        )
        add_btn.pack(side=tk.LEFT, padx=2)

    def _add_tokenizer(self, name: str) -> None:
        if name in self.tokenizers:
            return

        self.tokenizers.append(name)
        var = tk.BooleanVar(value=True)
        self.tokenizer_vars[name] = var

        frame = tk.Frame(self.scrollable_frame, bg=COLORS["black"])
        frame.pack(fill=tk.X, padx=5, pady=2)

        check = tk.Checkbutton(
            frame,
            text=name,
            variable=var,
            command=self.on_change,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        check.pack(side=tk.LEFT)

        remove_btn = tk.Button(
            frame,
            text="×",
            width=2,
            font=FONTS["small"],
            fg=COLORS["red"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["red_dim"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda n=name, f=frame: self._remove_tokenizer(n, f),  # type: ignore[misc]
        )
        remove_btn.pack(side=tk.RIGHT)

    def _add_new_tokenizer(self) -> None:
        name = self.new_tok_entry.get().strip()
        if name:
            self._add_tokenizer(name)
            self.new_tok_entry.delete(0, tk.END)
            self.on_change()

    def _remove_tokenizer(self, name: str, frame: tk.Frame) -> None:
        if name in self.tokenizers:
            self.tokenizers.remove(name)
            del self.tokenizer_vars[name]
            frame.destroy()
            self.on_change()

    def get_enabled_tokenizers(self) -> list[str]:
        """Return list of enabled tokenizer names."""
        return [name for name in self.tokenizers if self.tokenizer_vars[name].get()]


class MainFrame(ttk.Frame):
    """Main content frame with all UI components."""

    def __init__(self, parent: App) -> None:
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        self.seed_var = tk.IntVar(value=151)
        self.auto_update_var = tk.BooleanVar(value=True)
        self.diff_mode_var = tk.StringVar(value="label")
        self.diff_tokenizer_var = tk.StringVar(value="cl100k_base")

        self.glitchling_panel: GlitchlingPanel
        self.tokenizer_panel: TokenizerPanel
        self.input_text: scrolledtext.ScrolledText
        self.output_text: scrolledtext.ScrolledText
        self.token_diff_text: scrolledtext.ScrolledText
        self.diff_tokenizer_combo: ttk.Combobox
        self.metrics_tree: ttk.Treeview
        self.status_var: tk.StringVar

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Top bar with seed
        self._create_top_bar()

        # Main content with paned windows
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        # Left panel (Glitchlings + Tokenizers)
        left_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(left_pane, weight=1)

        # Glitchlings panel
        self.glitchling_panel = GlitchlingPanel(left_pane, self._on_settings_change)
        left_pane.add(self.glitchling_panel, weight=2)

        # Tokenizers panel
        self.tokenizer_panel = TokenizerPanel(left_pane, self._on_settings_change)
        left_pane.add(self.tokenizer_panel, weight=1)

        # Right panel
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        # Right panel is split into upper (Input/Output) and lower (Token Diff/Metrics)
        right_pane = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        # Upper section: Input and Output
        upper_frame = ttk.Frame(right_pane)
        right_pane.add(upper_frame, weight=2)

        # Input section with vector styling
        input_frame = self._create_vector_labelframe(upper_frame, "INPUT")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        self.input_text = self._create_vector_text(input_frame, height=6)
        self.input_text.insert("1.0", "The quick brown fox jumps over the lazy dog.")
        self.input_text.bind("<KeyRelease>", lambda e: self._on_settings_change())

        # Output section with vector styling - amber for corrupted output
        output_frame = self._create_vector_labelframe(upper_frame, "OUTPUT")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        self.output_text = self._create_vector_text(
            output_frame, height=6, state=tk.DISABLED, color=COLORS["amber"]
        )

        # Lower section: Token Diff and Metrics
        lower_frame = ttk.Frame(right_pane)
        right_pane.add(lower_frame, weight=2)

        # Token Diff section
        token_frame = self._create_vector_labelframe(lower_frame, "TOKEN DIFF")
        token_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        # Token diff header with controls - put in content frame
        if hasattr(token_frame, "content"):
            token_content = token_frame.content  # type: ignore[attr-defined]
        else:
            token_content = token_frame

        token_header = tk.Frame(token_content, bg=COLORS["black"])
        token_header.pack(fill=tk.X, padx=6, pady=(4, 2))

        id_radio = tk.Radiobutton(
            token_header,
            text="ID",
            variable=self.diff_mode_var,
            value="id",
            command=self._update_token_diff,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        id_radio.pack(side=tk.LEFT)

        label_radio = tk.Radiobutton(
            token_header,
            text="Label",
            variable=self.diff_mode_var,
            value="label",
            command=self._update_token_diff,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        label_radio.pack(side=tk.LEFT, padx=8)

        # Spacer
        tk.Frame(token_header, bg=COLORS["black"], width=20).pack(side=tk.LEFT)

        tok_label = tk.Label(
            token_header,
            text="Tokenizer:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        )
        tok_label.pack(side=tk.LEFT, padx=(0, 4))

        self.diff_tokenizer_combo = ttk.Combobox(
            token_header,
            textvariable=self.diff_tokenizer_var,
            values=["cl100k_base", "gpt2", "bert-base-uncased"],
            width=18,
            state="readonly",
        )
        self.diff_tokenizer_combo.pack(side=tk.LEFT)
        self.diff_tokenizer_combo.bind("<<ComboboxSelected>>", lambda e: self._update_token_diff())

        self.token_diff_text = self._create_vector_text(token_content, height=5, state=tk.DISABLED)

        # Configure tags for diff highlighting - vector colors
        self.token_diff_text.tag_configure("added", foreground=COLORS["cyan"])
        self.token_diff_text.tag_configure("removed", foreground=COLORS["red"], overstrike=True)
        self.token_diff_text.tag_configure("unchanged", foreground=COLORS["green_dim"])

        # Metrics section
        metrics_frame = self._create_vector_labelframe(lower_frame, "METRICS")
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        # Get content frame for metrics
        if hasattr(metrics_frame, "content"):
            metrics_content = metrics_frame.content  # type: ignore[attr-defined]
        else:
            metrics_content = metrics_frame

        # Create a container with border for the treeview
        tree_container = tk.Frame(metrics_content, bg=COLORS["border"], padx=1, pady=1)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tree_inner = tk.Frame(tree_container, bg=COLORS["darker"])
        tree_inner.pack(fill=tk.BOTH, expand=True)

        # Create treeview for metrics table
        columns = ("metric", "cl100k_base", "gpt2", "bert-base-uncased")
        self.metrics_tree = ttk.Treeview(tree_inner, columns=columns, show="headings", height=6)

        for col in columns:
            display_name = col.replace("_", " ").replace("-", " ").title()
            self.metrics_tree.heading(col, text=display_name)
            self.metrics_tree.column(col, width=110, anchor="center")

        self.metrics_tree.column("metric", width=180, anchor="w")

        metrics_scroll = ttk.Scrollbar(
            tree_inner, orient=tk.VERTICAL, command=self.metrics_tree.yview
        )
        self.metrics_tree.configure(yscrollcommand=metrics_scroll.set)

        self.metrics_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        metrics_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Initial metrics rows
        self.metrics_tree.insert("", "end", values=("Token Count", "-", "-", "-"))
        self.metrics_tree.insert("", "end", values=("Token Delta", "-", "-", "-"))
        self.metrics_tree.insert("", "end", values=("Char Count", "-", "-", "-"))

        # Status bar at the bottom
        self._create_status_bar()

    def _create_status_bar(self) -> None:
        """Create a status bar at the bottom of the window."""
        status_frame = tk.Frame(self, bg=COLORS["dark"], height=24)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=(0, 2))
        status_frame.pack_propagate(False)

        # Left side - status message
        self.status_var = tk.StringVar(value="▒ Ready")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            anchor="w",
            padx=8,
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Right side - version
        version_label = tk.Label(
            status_frame,
            text=f"v{APP_VERSION}",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=8,
        )
        version_label.pack(side=tk.RIGHT)

    def _create_vector_labelframe(self, parent: ttk.Frame | tk.Frame, title: str) -> tk.Frame:
        """Create a vector-styled labelframe."""
        outer = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)

        inner = tk.Frame(outer, bg=COLORS["black"])
        inner.pack(fill=tk.BOTH, expand=True)

        # Title bar with gradient effect
        title_bar = tk.Frame(inner, bg=COLORS["dark"])
        title_bar.pack(fill=tk.X)

        # Left decoration
        tk.Label(
            title_bar,
            text="▒",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=(4, 0))

        title_label = tk.Label(
            title_bar,
            text=title,
            font=FONTS["title"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=6,
            pady=4,
        )
        title_label.pack(side=tk.LEFT)

        # Right decoration
        tk.Label(
            title_bar,
            text="▒",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT)

        # Content area
        content = tk.Frame(inner, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Return outer frame for packing, but configure it to behave like content
        outer.content = content  # type: ignore[attr-defined]
        return outer

    def _create_vector_text(
        self,
        parent: tk.Frame,
        height: int = 6,
        state: str = tk.NORMAL,
        color: str | None = None,
    ) -> scrolledtext.ScrolledText:
        """Create a vector-styled text widget."""
        # Get the content frame if this is a vector labelframe
        if hasattr(parent, "content"):
            parent = parent.content  # type: ignore[attr-defined]

        fg_color = color if color else COLORS["green"]

        # Create a border frame
        border_frame = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        text = scrolledtext.ScrolledText(
            border_frame,
            wrap=tk.WORD,
            height=height,
            font=FONTS["mono"],
            fg=fg_color,
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            selectbackground=COLORS["highlight"],
            selectforeground=COLORS["green_bright"],
            relief=tk.FLAT,
            padx=10,
            pady=8,
            state=state,
            cursor="xterm",
        )
        text.pack(fill=tk.BOTH, expand=True)
        return text

    def _create_top_bar(self) -> None:
        # Header bar with vector styling
        top_bar = tk.Frame(self, bg=COLORS["dark"])
        top_bar.pack(fill=tk.X, padx=2, pady=(2, 0))

        # Title on the left with decorative border
        title_frame = tk.Frame(top_bar, bg=COLORS["dark"])
        title_frame.pack(side=tk.LEFT, padx=8, pady=4)

        title = tk.Label(
            title_frame,
            text="░▒▓ ༼ つ ◕_◕ ༽つ GLITCHLINGS ▓▒░",
            font=FONTS["header"],
            fg=COLORS["green_bright"],
            bg=COLORS["dark"],
        )
        title.pack(side=tk.LEFT)

        # Seed control on the right
        seed_frame = tk.Frame(top_bar, bg=COLORS["dark"])
        seed_frame.pack(side=tk.RIGHT, padx=8, pady=4)

        seed_label = tk.Label(
            seed_frame,
            text="SEED:",
            font=FONTS["body"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
        )
        seed_label.pack(side=tk.LEFT, padx=(0, 4))

        seed_spinbox = tk.Spinbox(
            seed_frame,
            from_=0,
            to=999999,
            textvariable=self.seed_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            buttonbackground=COLORS["dark"],
            relief=tk.SOLID,
            bd=1,
            command=self._on_settings_change,
        )
        seed_spinbox.pack(side=tk.LEFT)
        seed_spinbox.bind("<Return>", lambda e: self._on_settings_change())

        # Transform button - primary action
        transform_btn = tk.Button(
            top_bar,
            text="▶ TRANSFORM",
            font=FONTS["body"],
            fg=COLORS["green_bright"],
            bg=COLORS["green_dark"],
            activeforeground=COLORS["green_glow"],
            activebackground=COLORS["green_dim"],
            bd=1,
            relief=tk.SOLID,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._transform_text,
        )
        transform_btn.pack(side=tk.RIGHT, padx=8)

        # Auto-update checkbox
        auto_check = tk.Checkbutton(
            top_bar,
            text="Auto-update",
            variable=self.auto_update_var,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["dark"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
        )
        auto_check.pack(side=tk.RIGHT, padx=8)

    def _on_settings_change(self) -> None:
        """Called when any setting changes."""
        if self.auto_update_var.get():
            self._transform_text()

    def _transform_text(self) -> None:
        """Apply selected glitchlings to the input text."""
        input_text = self.input_text.get("1.0", tk.END).strip()
        if not input_text:
            self._set_output("")
            self.status_var.set("▒ No input text")
            return

        enabled = self.glitchling_panel.get_enabled_glitchlings()
        if not enabled:
            self._set_output(input_text)
            self._update_token_diff()
            self._update_metrics()
            self.status_var.set("▒ No glitchlings enabled")
            return

        try:
            # Create glitchling instances
            glitchlings = []
            names = []
            for cls, params in enabled:
                instance = cls(seed=self.seed_var.get(), **params)
                glitchlings.append(instance)
                names.append(cls.__name__)

            # Create gaggle and corrupt
            gaggle = Gaggle(glitchlings, seed=self.seed_var.get())
            output = gaggle.corrupt(input_text)

            # Handle both string and Transcript return types
            if isinstance(output, str):
                self._set_output(output)
            else:
                # It's a Transcript, extract text content
                self._set_output(str(output))

            self._update_token_diff()
            self._update_metrics()

            # Update status with glitchling names
            gnames = ", ".join(names)
            self.status_var.set(f"▒ Transformed with: {gnames}")

        except Exception as e:
            self._set_output(f"Error: {e}")
            self.status_var.set(f"▒ Error: {e}")

    def _set_output(self, text: str) -> None:
        """Set the output text."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

    def get_output(self) -> str:
        """Get the current output text."""
        return self.output_text.get("1.0", tk.END).strip()

    def get_input(self) -> str:
        """Get the current input text."""
        return self.input_text.get("1.0", tk.END).strip()

    def set_input(self, text: str) -> None:
        """Set the input text."""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        self._on_settings_change()

    def clear_all(self) -> None:
        """Clear all text and reset seed."""
        self.input_text.delete("1.0", tk.END)
        self._set_output("")
        self.seed_var.set(151)

    def _update_token_diff(self) -> None:
        """Update the token diff display using resolve_tokenizer."""
        input_text = self.get_input()
        output_text = self.get_output()

        self.token_diff_text.config(state=tk.NORMAL)
        self.token_diff_text.delete("1.0", tk.END)

        if not input_text or not output_text:
            self.token_diff_text.insert("1.0", "No text to compare")
            self.token_diff_text.config(state=tk.DISABLED)
            return

        try:
            tokenizer_name = self.diff_tokenizer_var.get()
            tok = resolve_tokenizer(tokenizer_name)

            input_tokens, input_ids = tok.encode(input_text)
            output_tokens, output_ids = tok.encode(output_text)

            mode = self.diff_mode_var.get()

            if mode == "id":
                input_str = " ".join(str(t) for t in input_ids)
                output_str = " ".join(str(t) for t in output_ids)
            else:
                input_str = " ".join(f"[{t}]" for t in input_tokens)
                output_str = " ".join(f"[{t}]" for t in output_tokens)

            self.token_diff_text.insert(
                "1.0",
                f"Input ({len(input_tokens)} tokens):\n{input_str}\n\n"
                f"Output ({len(output_tokens)} tokens):\n{output_str}",
            )

        except ValueError as e:
            self.token_diff_text.insert("1.0", f"Could not load tokenizer: {e}")
        except Exception as e:
            self.token_diff_text.insert("1.0", f"Error: {e}")

        self.token_diff_text.config(state=tk.DISABLED)

    def _update_metrics(self) -> None:
        """Update the metrics table using attack submodule metrics."""
        input_text = self.get_input()
        output_text = self.get_output()

        # Clear existing rows
        for item in self.metrics_tree.get_children():
            self.metrics_tree.delete(item)

        # Update columns based on enabled tokenizers
        tokenizers = self.tokenizer_panel.get_enabled_tokenizers()
        if not tokenizers:
            tokenizers = ["cl100k_base"]

        columns = ["metric"] + tokenizers
        self.metrics_tree["columns"] = columns

        for col in columns:
            display_name = col.replace("_", " ").replace("-", " ").title()
            self.metrics_tree.heading(col, text=display_name)
            self.metrics_tree.column(col, width=100, anchor="center")
        self.metrics_tree.column("metric", width=180, anchor="w")

        # Update the tokenizer dropdown
        self.diff_tokenizer_combo["values"] = tokenizers
        if self.diff_tokenizer_var.get() not in tokenizers and tokenizers:
            self.diff_tokenizer_var.set(tokenizers[0])

        if not input_text:
            return

        # Resolve tokenizers and calculate metrics
        resolved_tokenizers: dict[str, Any] = {}
        input_tokens: dict[str, list[str]] = {}
        output_tokens: dict[str, list[str]] = {}
        input_ids: dict[str, list[int]] = {}
        output_ids: dict[str, list[int]] = {}

        for tok_name in tokenizers:
            try:
                tok = resolve_tokenizer(tok_name)
                resolved_tokenizers[tok_name] = tok
                tokens_in, ids_in = tok.encode(input_text)
                input_tokens[tok_name] = tokens_in
                input_ids[tok_name] = ids_in
                if output_text:
                    tokens_out, ids_out = tok.encode(output_text)
                    output_tokens[tok_name] = tokens_out
                    output_ids[tok_name] = ids_out
                else:
                    output_tokens[tok_name] = []
                    output_ids[tok_name] = []
            except Exception:
                resolved_tokenizers[tok_name] = None
                input_tokens[tok_name] = []
                output_tokens[tok_name] = []
                input_ids[tok_name] = []
                output_ids[tok_name] = []

        # Token count input row
        row: list[str] = ["Token Count (Input)"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok):
                row.append(str(len(input_ids[tok])))
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Token count output row
        row = ["Token Count (Output)"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok):
                row.append(str(len(output_ids[tok])))
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Token delta row
        row = ["Token Delta"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok):
                delta = len(output_ids[tok]) - len(input_ids[tok])
                row.append(f"{'+' if delta > 0 else ''}{delta}")
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Attack metrics (only computed if there's output)
        if not output_text:
            return

        # Jensen-Shannon Divergence
        row = ["Jensen-Shannon Divergence"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok) and input_tokens[tok] and output_tokens[tok]:
                try:
                    jsd = jensen_shannon_divergence(input_tokens[tok], output_tokens[tok])
                    row.append(f"{jsd:.4f}")
                except Exception:
                    row.append("-")
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Normalized Edit Distance
        row = ["Normalized Edit Distance"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok) and input_tokens[tok] and output_tokens[tok]:
                try:
                    ned = normalized_edit_distance(input_tokens[tok], output_tokens[tok])
                    row.append(f"{ned:.4f}")
                except Exception:
                    row.append("-")
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Subsequence Retention
        row = ["Subsequence Retention"]
        for tok in tokenizers:
            if resolved_tokenizers.get(tok) and input_tokens[tok] and output_tokens[tok]:
                try:
                    sr = subsequence_retention(input_tokens[tok], output_tokens[tok])
                    row.append(f"{sr:.4f}")
                except Exception:
                    row.append("-")
            else:
                row.append("-")
        self.metrics_tree.insert("", "end", values=tuple(row))

        # Character count rows
        row = ["Char Count (Input)"]
        for _ in tokenizers:
            row.append(str(len(input_text)))
        self.metrics_tree.insert("", "end", values=tuple(row))

        row = ["Char Count (Output)"]
        for _ in tokenizers:
            row.append(str(len(output_text)) if output_text else "0")
        self.metrics_tree.insert("", "end", values=tuple(row))


if __name__ == "__main__":
    app = App()
    app.mainloop()
