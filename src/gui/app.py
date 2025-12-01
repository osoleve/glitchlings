"""Glitchlings GUI application.

A vector terminal-styled interface for corrupting text with glitchlings.
Features a modernized CRT aesthetic with mint-and-cyan glow and subtle scanline vibe.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Literal

# Allow running directly by adding project root to path and setting package
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    __package__ = "src.gui"

from .controller import Controller
from .model import SessionState
from .service import GlitchlingService
from .theme import APP_TITLE, APP_VERSION, COLORS, MENU_STYLES, apply_theme_styles
from .views.about import show_about_dialog
from .views.main_window import MainFrame

DEFAULT_WINDOW_SIZE = (1440, 920)
MIN_WINDOW_SIZE = (1150, 780)
MenuRelief = Literal["raised", "sunken", "flat", "ridge", "solid", "groove"]


class App(tk.Tk):
    """Main application window with vector terminal theme."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"༼ つ ◕_◕ ༽つ {APP_TITLE} v{APP_VERSION}")

        # Set initial geometry and center on screen
        self._default_geometry = self._centered_geometry(*DEFAULT_WINDOW_SIZE)
        self.geometry(self._default_geometry)
        self.minsize(*MIN_WINDOW_SIZE)

        # Initialize MVC components
        self.model = SessionState()
        self.service = GlitchlingService()
        self.controller = Controller(self.model, self.service)

        # Apply vector terminal theme
        self._apply_theme()

        self.main_frame: MainFrame
        self._menu_options = {**MENU_STYLES, "tearoff": 0}

        self._create_menu_bar()

        self.main_frame = MainFrame(self, self.controller)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self._bind_shortcuts()

    def _centered_geometry(self, width: int, height: int) -> str:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        return f"{width}x{height}+{x}+{y}"

    def _apply_theme(self) -> None:
        """Apply the vector terminal CRT aesthetic."""
        self.configure(bg=COLORS["black"])
        self._style = apply_theme_styles()

    def _build_menu(
        self, parent: tk.Misc, *, borderwidth: int = 1, relief: MenuRelief = tk.SOLID
    ) -> tk.Menu:
        return tk.Menu(
            parent,
            borderwidth=borderwidth,
            relief=relief,
            **self._menu_options,
        )

    def _create_menu_bar(self) -> None:
        menubar = self._build_menu(self, borderwidth=0, relief=tk.FLAT)
        self.config(menu=menubar)

        file_menu = self._build_menu(menubar)
        menubar.add_cascade(label="▒ FILE", menu=file_menu)
        file_menu.add_command(label="New Session", command=self._new_session, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save...", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Alt+F4")

        edit_menu = self._build_menu(menubar)
        menubar.add_cascade(label="▒ EDIT", menu=edit_menu)
        edit_menu.add_command(
            label="Copy Input", command=self._copy_input, accelerator="Ctrl+Shift+C"
        )
        edit_menu.add_command(label="Copy Output", command=self._copy_output)
        edit_menu.add_command(
            label="Paste to Input", command=self._paste_input, accelerator="Ctrl+Shift+V"
        )

        view_menu = self._build_menu(menubar)
        menubar.add_cascade(label="▒ VIEW", menu=view_menu)
        view_menu.add_command(label="Reset Layout", command=self._reset_layout)

        help_menu = self._build_menu(menubar)
        menubar.add_cascade(label="▒ HELP", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _bind_shortcuts(self) -> None:
        shortcuts: dict[str, Callable[[tk.Event], None]] = {
            "<F5>": lambda _event: self.controller.transform_text(),
            "<Escape>": lambda _event: self.main_frame.input_text.focus_set(),
            "<Control-Return>": lambda _event: self.controller.transform_text(),
            "<Control-r>": lambda _event: self.controller.randomize_seed(),
            "<Control-l>": lambda _event: self.main_frame.clear_all(),
            "<Control-n>": lambda _event: self._new_session(),
            "<Control-o>": lambda _event: self._open_file(),
            "<Control-s>": lambda _event: self._save_file(),
        }

        for sequence, handler in shortcuts.items():
            self.bind(sequence, handler)

    def _new_session(self) -> None:
        self.main_frame.clear_all()

    def _open_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            messagebox.showerror("Open failed", f"Could not read file:\n{exc}")
            return

        self.main_frame.set_input(content)

    def _save_file(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.main_frame.get_output())
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save file:\n{exc}")

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
        self.state("normal")
        self.geometry(self._default_geometry)
        self.update_idletasks()
        self.main_frame.input_text.focus_set()

    def _show_about(self) -> None:
        show_about_dialog(self)



if __name__ == "__main__":
    app = App()
    app.mainloop()
