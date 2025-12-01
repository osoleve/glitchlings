"""Glitchlings GUI application.

A vector terminal-styled interface for corrupting text with glitchlings.
Features a modernized CRT aesthetic with mint-and-cyan glow and subtle scanline vibe.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Literal

# Allow running directly by adding project root to path and setting package
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    __package__ = "src.gui"

from .controller import Controller
from .export import ExportData
from .model import SessionState
from .preferences import Preferences, load_preferences, save_preferences
from .service import GlitchlingService
from .session import SessionConfig
from .theme import APP_TITLE, APP_VERSION, COLORS, MENU_STYLES, apply_theme_styles
from .views.about import show_about_dialog
from .views.export_dialog import ExportDialog
from .views.main_window import MainFrame
from .views.preferences_dialog import PreferencesDialog
from .views.session_dialog import LoadSessionDialog, SaveSessionDialog

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

        self.preferences: Preferences = load_preferences()
        self._prefs_dialog: PreferencesDialog | None = None

        # Initialize MVC components
        self.model = SessionState()
        self.service = GlitchlingService()
        self.controller = Controller(self.model, self.service)

        # Apply vector terminal theme
        self._apply_theme()

        self.main_frame: MainFrame
        self._menu_options = {**MENU_STYLES, "tearoff": 0}

        self._create_menu_bar()

        self.main_frame = MainFrame(
            self,
            self.controller,
            self.preferences,
            self._persist_preferences,
            self._copy_output,
        )
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
        file_menu.add_separator()
        file_menu.add_command(
            label="Load Session...", command=self._load_session, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Save Session...", command=self._save_session, accelerator="Ctrl+S"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Import Text...", command=self._open_file)
        file_menu.add_command(label="Export Text...", command=self._save_file)
        file_menu.add_command(
            label="Export Report...", command=self._export_report, accelerator="Ctrl+E"
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Preferences...",
            command=self._open_preferences,
            accelerator="Ctrl+,",
        )
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
            "<F5>": lambda _event: self.main_frame._transform_text(),
            "<Escape>": lambda _event: self.main_frame.input_text.focus_set(),
            "<Control-Return>": lambda _event: self.main_frame._transform_text(),
            "<Control-r>": lambda _event: self.controller.randomize_seed(),
            "<Control-l>": lambda _event: self.main_frame.clear_all(),
            "<Control-n>": lambda _event: self._new_session(),
            "<Control-o>": lambda _event: self._load_session(),
            "<Control-s>": lambda _event: self._save_session(),
            "<Control-e>": lambda _event: self._export_report(),
            "<Control-comma>": lambda _event: self._open_preferences(),
        }

        for sequence, handler in shortcuts.items():
            self.bind(sequence, handler)

    def _new_session(self) -> None:
        self.main_frame.clear_all()

    def _build_session_config(self) -> SessionConfig:
        """Build a SessionConfig from current state."""
        glitchlings = [(cls.__name__, params) for cls, params in self.model.enabled_glitchlings]
        return SessionConfig(
            glitchlings=glitchlings,
            tokenizers=list(self.model.enabled_tokenizers),
            seed=self.model.seed,
            auto_update=self.model.auto_update,
            scan_mode=self.model.scan_mode,
            scan_count=self.model.scan_count,
            diff_mode=self.model.diff_mode,
            diff_tokenizer=self.model.diff_tokenizer,
            input_text=self.main_frame.get_input(),
        )

    def _save_session(self) -> None:
        """Open save session dialog."""
        config = self._build_session_config()
        SaveSessionDialog(self, config, self._on_session_saved)

    def _on_session_saved(self, path: "Path") -> None:
        """Called after session is saved."""
        self.main_frame.set_status(f"Session saved: {path.name}", "green")

    def _load_session(self) -> None:
        """Load a session from file."""
        from .session import resolve_glitchlings

        config = LoadSessionDialog.load(self)
        if config is None:
            return

        # Apply loaded configuration
        self.main_frame.apply_session(config)
        self.model.seed = config.seed
        self.model.auto_update = config.auto_update
        self.model.scan_mode = config.scan_mode
        self.model.scan_count = config.scan_count
        self.model.diff_mode = config.diff_mode
        self.model.diff_tokenizer = config.diff_tokenizer
        self.model.enabled_glitchlings = resolve_glitchlings(config)
        self.model.enabled_tokenizers = list(config.tokenizers)

        if config.input_text:
            self.main_frame.set_input(config.input_text)

        self.main_frame.set_status(f"Session loaded: {config.name or 'unnamed'}", "cyan")

    def _export_report(self) -> None:
        """Open export dialog."""
        config = self._build_session_config()

        export_data = ExportData(
            config=config,
            input_text=self.main_frame.get_input(),
            output_text=self.main_frame.get_output(),
            metrics=self._get_current_metrics(),
            scan_results=self.model.scan_results,
        )

        ExportDialog(self, export_data)

    def _get_current_metrics(self) -> dict[str, dict[str, object]]:
        """Get current metrics from service if available."""
        if not self.model.output_text:
            return {}
        return self.service.calculate_metrics(
            self.model.input_text,
            self.model.output_text,
            list(self.model.enabled_tokenizers),
        )

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
        try:
            text = self.main_frame.get_output()
            if self.preferences.copy_metadata:
                glitchling_lines = []
                for cls, params in self.model.enabled_glitchlings:
                    param_str = (
                        ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
                        if params
                        else "default"
                    )
                    glitchling_lines.append(f"{cls.__name__} ({param_str})")

                glitchling_str = ", ".join(glitchling_lines) if glitchling_lines else "None"
                tokenizer_str = (
                    ", ".join(self.model.enabled_tokenizers)
                    if self.model.enabled_tokenizers
                    else "None"
                )
                meta_lines = [
                    f"Seed: {self.model.seed}",
                    f"Glitchlings: {glitchling_str}",
                    f"Tokenizers: {tokenizer_str}",
                ]
                text = f"{text}\n\n---\nMetadata:\n" + "\n".join(meta_lines)

            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError:
            pass

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
        if self.main_frame.sidebar_collapsed:
            self.main_frame._toggle_sidebar()
        self.main_frame.input_text.focus_set()

    def _open_preferences(self) -> None:
        if self._prefs_dialog and self._prefs_dialog.winfo_exists():
            self._prefs_dialog.lift()
            return

        self._prefs_dialog = PreferencesDialog(
            self, self.preferences, self._apply_preferences_from_dialog
        )
        self._prefs_dialog.bind("<Destroy>", lambda _e: self._clear_prefs_dialog())

    def _clear_prefs_dialog(self) -> None:
        self._prefs_dialog = None

    def _persist_preferences(self, preferences: Preferences) -> None:
        self.preferences = preferences
        save_preferences(preferences)

    def _apply_preferences_from_dialog(self, preferences: Preferences) -> None:
        self._persist_preferences(preferences)
        self.main_frame.apply_preferences(preferences)

    def _show_about(self) -> None:
        show_about_dialog(self)


if __name__ == "__main__":
    app = App()
    app.mainloop()
