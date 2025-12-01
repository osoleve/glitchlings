from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable

from ..preferences import Preferences, _coerce_tokenizers
from ..theme import COLORS, FONTS


class PreferencesDialog(tk.Toplevel):
    """Modal dialog for editing user preferences."""

    def __init__(
        self,
        parent: tk.Tk,
        preferences: Preferences,
        on_save: Callable[[Preferences], None],
    ) -> None:
        super().__init__(parent)
        self.title("Preferences")
        self.configure(bg=COLORS["black"])
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.preferences = preferences
        self.on_save = on_save

        self.font_var = tk.StringVar(value=preferences.font_family)
        self.font_size_var = tk.IntVar(value=preferences.font_size)
        self.tokenizers_var = tk.StringVar(
            value=", ".join(preferences.default_tokenizers)
        )
        self.copy_meta_var = tk.BooleanVar(value=preferences.copy_metadata)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg=COLORS["black"], padx=10, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Font family",
            font=FONTS["body"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        font_choices = sorted(set(tkfont.families()))
        font_combo = ttk.Combobox(
            container,
            values=font_choices,
            textvariable=self.font_var,
            width=28,
        )
        font_combo.grid(row=0, column=1, padx=(8, 0), pady=(0, 6), sticky="ew")

        tk.Label(
            container,
            text="Font size",
            font=FONTS["body"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        size_spin = tk.Spinbox(
            container,
            from_=6,
            to=48,
            textvariable=self.font_size_var,
            width=6,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            buttonbackground=COLORS["dark"],
            relief=tk.SOLID,
            bd=1,
        )
        size_spin.grid(row=1, column=1, padx=(8, 0), pady=(0, 6), sticky="w")

        tk.Label(
            container,
            text="Default tokenizers (comma separated)",
            font=FONTS["body"],
            fg=COLORS["green_bright"],
            bg=COLORS["black"],
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        tok_entry = tk.Entry(
            container,
            textvariable=self.tokenizers_var,
            width=40,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        tok_entry.grid(row=2, column=1, padx=(8, 0), pady=(0, 6), sticky="ew")

        copy_check = tk.Checkbutton(
            container,
            text="Copy metadata with output",
            variable=self.copy_meta_var,
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        copy_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 10))

        button_row = tk.Frame(container, bg=COLORS["black"])
        button_row.grid(row=4, column=0, columnspan=2, sticky="e")

        tk.Button(
            button_row,
            text="Cancel",
            font=FONTS["body"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            button_row,
            text="Save",
            font=FONTS["body"],
            fg=COLORS["black"],
            bg=COLORS["green"],
            activeforeground=COLORS["black"],
            activebackground=COLORS["green_bright"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._save,
        ).pack(side=tk.RIGHT, padx=(0, 4))

        container.columnconfigure(1, weight=1)

    def _save(self) -> None:
        tokenizers = _coerce_tokenizers(self.tokenizers_var.get().split(","))
        prefs = self.preferences.with_updates(
            font_family=self.font_var.get().strip() or self.preferences.font_family,
            font_size=max(6, int(self.font_size_var.get())),
            default_tokenizers=tokenizers,
            copy_metadata=self.copy_meta_var.get(),
        )
        self.on_save(prefs)
        self.destroy()
