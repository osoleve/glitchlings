"""Glitchlings GUI application.

A vector terminal-styled interface for corrupting text with glitchlings.
Features a modernized CRT aesthetic with mint-and-cyan glow and subtle scanline vibe.
"""

from __future__ import annotations

import sys
import os

# Allow running directly by adding project root to path and setting package
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    __package__ = "src.gui"

import tkinter as tk
from tkinter import filedialog, ttk

from .theme import COLORS, FONTS, APP_TITLE, APP_VERSION
from .model import SessionState
from .service import GlitchlingService
from .controller import Controller
from .views.main_window import MainFrame


class App(tk.Tk):
    """Main application window with vector terminal theme."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"༼ つ ◕_◕ ༽つ {APP_TITLE} v{APP_VERSION}")

        # Set initial geometry and center on screen
        width, height = 1440, 920
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1150, 780)

        # Initialize MVC components
        self.model = SessionState()
        self.service = GlitchlingService()
        self.controller = Controller(self.model, self.service)

        # Apply vector terminal theme
        self._apply_theme()

        self.main_frame: MainFrame

        # Create menu bar
        self._create_menu_bar()

        # Create main frame
        self.main_frame = MainFrame(self, self.controller)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Bind global shortcuts
        self.bind("<F5>", lambda e: self.controller.transform_text())
        self.bind("<Escape>", lambda e: self.main_frame.input_text.focus_set())
        self.bind("<Control-Return>", lambda e: self.controller.transform_text())
        self.bind("<Control-r>", lambda e: self.controller.randomize_seed())
        self.bind("<Control-l>", lambda e: self.main_frame.clear_all())

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
            font=FONTS["metric"],
            rowheight=24,
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
        about.title("ABOUT GLITCHLINGS")
        about.geometry("480x420")
        about.configure(bg=COLORS["black"])
        about.resizable(False, False)

        # Center the dialog relative to parent
        about.transient(self)
        about.grab_set()

        # Center on screen
        about.update_idletasks()
        x = (about.winfo_screenwidth() - 480) // 2
        y = (about.winfo_screenheight() - 420) // 2
        about.geometry(f"+{x}+{y}")

        # Border frame - double border effect
        outer_border = tk.Frame(about, bg=COLORS["green_dim"], padx=2, pady=2)
        outer_border.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        border = tk.Frame(outer_border, bg=COLORS["border"], padx=1, pady=1)
        border.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(border, bg=COLORS["black"])
        inner.pack(fill=tk.BOTH, expand=True)

        # ASCII art header
        header_text = """
╔════════════════════════════════════════════╗
║    ༼ つ ◕_◕ ༽つ  GLITCHLINGS            ║
║       ▓▒░ TERMINAL v{ver:<9} ░▒▓         ║
╚════════════════════════════════════════════╝
""".format(ver=APP_VERSION)
        header = tk.Label(
            inner,
            text=header_text,
            font=("Consolas", 11),
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
            justify=tk.CENTER,
        )
        header.pack(pady=(10, 0))

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

        # Feature list
        features_frame = tk.Frame(inner, bg=COLORS["black"])
        features_frame.pack(pady=10)

        features = [
            "● 10 unique glitchling creatures",
            "● Deterministic transformations with seeds",
            "● Real-time token diff analysis",
            "● Multi-tokenizer metrics comparison",
        ]
        for feat in features:
            tk.Label(
                features_frame,
                text=feat,
                font=FONTS["small"],
                fg=COLORS["cyan"],
                bg=COLORS["black"],
                anchor="w",
            ).pack(anchor="w", padx=20)

        # Decorative separator
        sep_frame = tk.Frame(inner, bg=COLORS["black"])
        sep_frame.pack(fill=tk.X, padx=40, pady=10)
        tk.Frame(sep_frame, bg=COLORS["green_dim"], height=1).pack(fill=tk.X)

        # Status line
        status = tk.Label(
            inner,
            text="▓▒░ SYSTEM OPERATIONAL ░▒▓",
            font=FONTS["status"],
            fg=COLORS["cyan_bright"],
            bg=COLORS["black"],
        )
        status.pack(pady=8)

        # Close button
        close_btn = tk.Button(
            inner,
            text="[ CLOSE ]",
            font=FONTS["section"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["black"],
            activebackground=COLORS["green"],
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=6,
            cursor="hand2",
            command=about.destroy,
        )
        close_btn.pack(pady=15)

        # Bind escape to close
        about.bind("<Escape>", lambda e: about.destroy())


if __name__ == "__main__":
    app = App()
    app.mainloop()
