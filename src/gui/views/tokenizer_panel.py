import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Any, List

from ..theme import COLORS, DEFAULT_TOKENIZERS, FONTS
from .utils import create_tooltip


class TokenizerPanel(ttk.Frame):
    """Panel for managing tokenizers."""

    def __init__(
        self,
        parent: ttk.PanedWindow,
        on_change_callback: Any,
        initial_tokenizers: List[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_change = on_change_callback
        self.tokenizers: List[str] = []
        self.tokenizer_vars: dict[str, tk.BooleanVar] = {}
        self.tokenizer_frames: dict[str, tk.Frame] = {}
        self.initial_tokenizers = initial_tokenizers

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header with vector terminal styling
        header_frame = tk.Frame(self, bg=COLORS["surface"], height=40)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        header_frame.pack_propagate(False)

        header = tk.Label(
            header_frame,
            text="▓▒░ TOKENIZERS ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["surface"],
            padx=12,
        )
        header.pack(side=tk.LEFT, pady=10)

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

        defaults = self.initial_tokenizers or list(DEFAULT_TOKENIZERS)
        for tok in defaults:
            self._add_tokenizer(tok)

        # Separator - more subtle
        sep = tk.Frame(self.scrollable_frame, bg=COLORS["border_subtle"], height=1)
        sep.pack(fill=tk.X, padx=12, pady=10)

        # Add new tokenizer row
        add_frame = tk.Frame(self.scrollable_frame, bg=COLORS["black"])
        add_frame.pack(fill=tk.X, padx=6, pady=6)

        add_label = tk.Label(
            add_frame,
            text="Add:",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        )
        add_label.pack(side=tk.LEFT, padx=(0, 6))

        self.new_tok_entry = tk.Entry(
            add_frame,
            width=20,
            font=FONTS["small"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        self.new_tok_entry.pack(side=tk.LEFT, padx=4)
        self.new_tok_entry.bind("<Return>", lambda e: self._add_new_tokenizer())
        create_tooltip(self.new_tok_entry, "Enter tokenizer name (tiktoken or HuggingFace)")

        add_btn = tk.Button(
            add_frame,
            text="+ Add",
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["surface"],
            activeforeground=COLORS["darker"],
            activebackground=COLORS["green"],
            bd=0,
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._add_new_tokenizer,
        )
        add_btn.pack(side=tk.LEFT, padx=8)

        def _add_enter(e: tk.Event) -> None:
            add_btn.config(bg=COLORS["green"], fg=COLORS["darker"])

        def _add_leave(e: tk.Event) -> None:
            add_btn.config(bg=COLORS["surface"], fg=COLORS["green"])

        add_btn.bind("<Enter>", _add_enter)
        add_btn.bind("<Leave>", _add_leave)

    def _add_tokenizer(self, name: str) -> None:
        if name in self.tokenizers:
            return

        self.tokenizers.append(name)
        var = tk.BooleanVar(value=True)
        self.tokenizer_vars[name] = var

        frame = tk.Frame(self.scrollable_frame, bg=COLORS["black"])
        frame.pack(fill=tk.X, padx=6, pady=4)
        self.tokenizer_frames[name] = frame

        # Status indicator
        status_dot = tk.Label(
            frame,
            text="●",
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["black"],
        )
        status_dot.pack(side=tk.LEFT, padx=(0, 6))

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
            width=3,
            font=FONTS["small"],
            fg=COLORS["text_muted"],
            bg=COLORS["black"],
            activeforeground=COLORS["red"],
            activebackground=COLORS["black"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=partial(self._remove_tokenizer, name),
        )
        remove_btn.pack(side=tk.RIGHT, padx=4)

    def _add_new_tokenizer(self) -> None:
        name = self.new_tok_entry.get().strip()
        if name:
            self._add_tokenizer(name)
            self.new_tok_entry.delete(0, tk.END)
            self.on_change()

    def _remove_tokenizer(self, name: str) -> None:
        if name in self.tokenizers:
            self.tokenizers.remove(name)
            del self.tokenizer_vars[name]
            if name in self.tokenizer_frames:
                self.tokenizer_frames[name].destroy()
                del self.tokenizer_frames[name]
            self.on_change()

    def set_tokenizers(self, tokenizers: List[str]) -> None:
        """Replace tokenizer list with a new set."""
        for frame in list(self.tokenizer_frames.values()):
            frame.destroy()
        self.tokenizers = []
        self.tokenizer_frames = {}
        self.tokenizer_vars = {}

        for tok in tokenizers:
            self._add_tokenizer(tok)
        self.on_change()

    def get_enabled_tokenizers(self) -> List[str]:
        """Return list of enabled tokenizer names."""
        return [name for name in self.tokenizers if self.tokenizer_vars[name].get()]

    def get_all_tokenizers(self) -> List[str]:
        """Return all configured tokenizer names (enabled or not)."""
        return list(self.tokenizers)
