"""Session save/load dialogs for the GUI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

from ..session import SessionConfig, load_session, save_session
from ..theme import COLORS, FONTS


class SaveSessionDialog(tk.Toplevel):
    """Dialog for saving session configuration."""

    def __init__(
        self,
        parent: tk.Tk,
        session_config: SessionConfig,
        on_save: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Save Session")
        self.configure(bg=COLORS["black"])
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.session_config = session_config
        self.on_save = on_save

        self.name_var = tk.StringVar(value=session_config.name)
        self.description_var = tk.StringVar(value=session_config.description)
        self.include_input_var = tk.BooleanVar(value=session_config.include_input)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["surface"], height=40)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="▓▒░ SAVE SESSION ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["surface"],
            padx=12,
        ).pack(side=tk.LEFT, pady=10)

        # Content
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        container = tk.Frame(content_container, bg=COLORS["black"], padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        # Session name
        tk.Label(
            container,
            text="Session Name:",
            font=FONTS["small"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        name_entry = tk.Entry(
            container,
            textvariable=self.name_var,
            width=40,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        name_entry.grid(row=0, column=1, padx=(8, 0), pady=(0, 6), sticky="ew")
        name_entry.focus_set()

        # Description
        tk.Label(
            container,
            text="Description:",
            font=FONTS["small"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).grid(row=1, column=0, sticky="nw", pady=(0, 6))

        desc_frame = tk.Frame(container, bg=COLORS["border"], padx=1, pady=1)
        desc_frame.grid(row=1, column=1, padx=(8, 0), pady=(0, 6), sticky="ew")

        self.desc_text = tk.Text(
            desc_frame,
            width=38,
            height=3,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.FLAT,
            padx=4,
            pady=4,
        )
        self.desc_text.pack(fill=tk.BOTH, expand=True)
        if self.session_config.description:
            self.desc_text.insert("1.0", self.session_config.description)

        # Include input checkbox
        include_check = tk.Checkbutton(
            container,
            text="Include input text in session file",
            variable=self.include_input_var,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        include_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 15))

        # Summary of what will be saved
        summary_frame = tk.Frame(container, bg=COLORS["dark"], padx=8, pady=8)
        summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        glitchling_names = [name for name, _ in self.session_config.glitchlings]
        summary_text = (
            f"Glitchlings: {', '.join(glitchling_names) or 'None'}\n"
            f"Tokenizers: {', '.join(self.session_config.tokenizers) or 'None'}\n"
            f"Seed: {self.session_config.seed}"
        )

        tk.Label(
            summary_frame,
            text=summary_text,
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            justify=tk.LEFT,
        ).pack(anchor="w")

        # Buttons
        button_row = tk.Frame(container, bg=COLORS["black"])
        button_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))

        tk.Button(
            button_row,
            text="Cancel",
            font=FONTS["button"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        save_btn = tk.Button(
            button_row,
            text="Save As...",
            font=FONTS["button"],
            fg=COLORS["darker"],
            bg=COLORS["green"],
            activeforeground=COLORS["darker"],
            activebackground=COLORS["green_bright"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._save,
        )
        save_btn.pack(side=tk.RIGHT)

        container.columnconfigure(1, weight=1)

    def _save(self) -> None:
        # Update config with dialog values
        self.session_config.name = self.name_var.get().strip()
        self.session_config.description = self.desc_text.get("1.0", tk.END).strip()
        self.session_config.include_input = self.include_input_var.get()

        # Get save path
        file_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".glitchsession",
            filetypes=[
                ("Glitchlings Session", "*.glitchsession"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
            initialfile=self.session_config.name or "session",
        )

        if not file_path:
            return

        try:
            save_session(self.session_config, file_path)
            if self.on_save:
                self.on_save(Path(file_path))
            self.destroy()
        except OSError as e:
            messagebox.showerror("Save Failed", f"Could not save session:\n{e}", parent=self)


class LoadSessionDialog:
    """Helper for loading session files."""

    @staticmethod
    def load(parent: tk.Tk) -> SessionConfig | None:
        """Show file dialog and load a session.

        Returns the loaded SessionConfig or None if cancelled/failed.
        """
        file_path = filedialog.askopenfilename(
            parent=parent,
            filetypes=[
                ("Glitchlings Session", "*.glitchsession"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return None

        try:
            return load_session(file_path)
        except (OSError, ValueError) as e:
            messagebox.showerror(
                "Load Failed",
                f"Could not load session:\n{e}",
                parent=parent,
            )
            return None
