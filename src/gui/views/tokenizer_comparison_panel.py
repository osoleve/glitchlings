"""Tokenizer comparison panel for analyzing how different tokenizers handle text.

Shows side-by-side token boundaries, vocabulary differences, and encoding statistics.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Tuple

from glitchlings.attack.tokenization import resolve_tokenizer

from ..theme import COLORS, FONTS

# Color palette for token boundaries (cycling through these)
TOKEN_COLORS = [
    "#4a6b3a",  # Dark green
    "#3a4a6b",  # Dark blue
    "#6b3a4a",  # Dark red
    "#6b5a3a",  # Dark orange
    "#4a3a6b",  # Dark purple
    "#3a6b5a",  # Dark teal
]


class TokenizerComparisonPanel(ttk.Frame):
    """Panel for comparing how different tokenizers process the same text."""

    def __init__(
        self,
        parent: ttk.Frame,
        get_input_text: Callable[[], str],
        get_tokenizers: Callable[[], List[str]],
    ) -> None:
        super().__init__(parent)
        self.get_input_text = get_input_text
        self.get_tokenizers = get_tokenizers

        # Cached results
        self._cached_results: Dict[str, Tuple[List[str], List[int]]] = {}

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        # Header
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        tk.Label(
            header_frame,
            text="▓▒░ TOKENIZER COMPARISON ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=8,
            pady=5,
        ).pack(side=tk.LEFT)

        # Refresh button
        refresh_btn = tk.Button(
            header_frame,
            text="⟳ REFRESH",
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self.refresh,
        )
        refresh_btn.pack(side=tk.RIGHT, padx=8)

        # Main content container
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        content = tk.Frame(content_container, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Split into left (visualization) and right (stats) panels
        paned = ttk.PanedWindow(content, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left: Token visualization
        viz_frame = tk.Frame(paned, bg=COLORS["black"])
        paned.add(viz_frame, weight=3)

        viz_header = tk.Frame(viz_frame, bg=COLORS["dark"])
        viz_header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            viz_header,
            text="░ TOKEN BOUNDARIES",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=4,
        ).pack(side=tk.LEFT)

        # Scrollable container for tokenizer visualizations
        viz_scroll_container = tk.Frame(viz_frame, bg=COLORS["border"], padx=1, pady=1)
        viz_scroll_container.pack(fill=tk.BOTH, expand=True)

        self.viz_canvas = tk.Canvas(
            viz_scroll_container,
            bg=COLORS["darker"],
            highlightthickness=0,
        )
        viz_scrollbar_y = ttk.Scrollbar(
            viz_scroll_container, orient=tk.VERTICAL, command=self.viz_canvas.yview
        )
        viz_scrollbar_x = ttk.Scrollbar(
            viz_scroll_container, orient=tk.HORIZONTAL, command=self.viz_canvas.xview
        )

        self.viz_inner = tk.Frame(self.viz_canvas, bg=COLORS["darker"])

        self.viz_canvas.configure(
            yscrollcommand=viz_scrollbar_y.set, xscrollcommand=viz_scrollbar_x.set
        )

        viz_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        viz_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.viz_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.viz_canvas_window = self.viz_canvas.create_window(
            (0, 0), window=self.viz_inner, anchor="nw"
        )

        self.viz_inner.bind(
            "<Configure>",
            lambda e: self.viz_canvas.configure(scrollregion=self.viz_canvas.bbox("all")),
        )
        self.viz_canvas.bind(
            "<Configure>",
            lambda e: self.viz_canvas.itemconfig(self.viz_canvas_window, width=e.width),
        )

        # Right: Statistics panel
        stats_frame = tk.Frame(paned, bg=COLORS["black"])
        paned.add(stats_frame, weight=1)

        stats_header = tk.Frame(stats_frame, bg=COLORS["dark"])
        stats_header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            stats_header,
            text="░ ENCODING STATISTICS",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=4,
        ).pack(side=tk.LEFT)

        stats_container = tk.Frame(stats_frame, bg=COLORS["border"], padx=1, pady=1)
        stats_container.pack(fill=tk.BOTH, expand=True)

        # Stats treeview
        self.stats_tree = ttk.Treeview(
            stats_container,
            columns=("tokenizer", "tokens", "chars_per_tok", "unique"),
            show="headings",
            height=10,
        )

        self.stats_tree.heading("tokenizer", text="Tokenizer")
        self.stats_tree.heading("tokens", text="Tokens")
        self.stats_tree.heading("chars_per_tok", text="Chars/Tok")
        self.stats_tree.heading("unique", text="Unique")

        self.stats_tree.column("tokenizer", width=120, anchor="w")
        self.stats_tree.column("tokens", width=60, anchor="center")
        self.stats_tree.column("chars_per_tok", width=80, anchor="center")
        self.stats_tree.column("unique", width=60, anchor="center")

        stats_scroll = ttk.Scrollbar(
            stats_container, orient=tk.VERTICAL, command=self.stats_tree.yview
        )
        self.stats_tree.configure(yscrollcommand=stats_scroll.set)

        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh(self) -> None:
        """Refresh the comparison view with current text and tokenizers."""
        text = self.get_input_text()
        tokenizers = self.get_tokenizers()

        if not text or not tokenizers:
            self._clear_display()
            return

        # Encode with each tokenizer
        self._cached_results.clear()
        for tok_name in tokenizers:
            try:
                tok = resolve_tokenizer(tok_name)
                tokens, ids = tok.encode(text)
                self._cached_results[tok_name] = (tokens, ids)
            except Exception:
                self._cached_results[tok_name] = ([], [])

        self._update_visualization()
        self._update_statistics(text)

    def _clear_display(self) -> None:
        """Clear all displays."""
        for widget in self.viz_inner.winfo_children():
            widget.destroy()

        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)

    def _update_visualization(self) -> None:
        """Update the token boundary visualization."""
        # Clear existing visualizations
        for widget in self.viz_inner.winfo_children():
            widget.destroy()

        for tok_name, (tokens, ids) in self._cached_results.items():
            if not tokens:
                continue

            # Frame for this tokenizer
            tok_frame = tk.Frame(self.viz_inner, bg=COLORS["darker"])
            tok_frame.pack(fill=tk.X, pady=4, padx=4)

            # Tokenizer name label
            tk.Label(
                tok_frame,
                text=f"● {tok_name}",
                font=FONTS["small"],
                fg=COLORS["cyan"],
                bg=COLORS["darker"],
            ).pack(anchor="w")

            # Token visualization - use a Text widget for rich formatting
            token_text = tk.Text(
                tok_frame,
                height=3,
                wrap=tk.WORD,
                font=FONTS["mono"],
                fg=COLORS["green"],
                bg=COLORS["black"],
                relief=tk.SOLID,
                bd=1,
                padx=4,
                pady=4,
            )
            token_text.pack(fill=tk.X, pady=(2, 0))

            # Configure tags for token backgrounds
            for i, color in enumerate(TOKEN_COLORS):
                token_text.tag_configure(f"tok_{i}", background=color)

            # Insert tokens with alternating backgrounds
            for i, (token, token_id) in enumerate(zip(tokens, ids)):
                tag = f"tok_{i % len(TOKEN_COLORS)}"
                # Escape display representation of token
                display_token = repr(token)[1:-1]  # Remove quotes from repr
                token_text.insert(tk.END, f"[{display_token}]", tag)

            token_text.config(state=tk.DISABLED)

            # ID line - show token IDs in same positions
            id_frame = tk.Frame(tok_frame, bg=COLORS["darker"])
            id_frame.pack(fill=tk.X, pady=(2, 0))

            tk.Label(
                id_frame,
                text="IDs: " + " ".join(str(i) for i in ids[:20])
                + ("..." if len(ids) > 20 else ""),
                font=FONTS["tiny"],
                fg=COLORS["green_dim"],
                bg=COLORS["darker"],
            ).pack(anchor="w")

            # Separator
            sep = tk.Frame(self.viz_inner, bg=COLORS["border"], height=1)
            sep.pack(fill=tk.X, pady=4)

    def _update_statistics(self, text: str) -> None:
        """Update the statistics display."""
        # Clear existing stats
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)

        char_count = len(text)

        for tok_name, (tokens, ids) in self._cached_results.items():
            token_count = len(tokens)
            unique_count = len(set(tokens))

            if token_count > 0:
                chars_per_tok = f"{char_count / token_count:.2f}"
            else:
                chars_per_tok = "-"

            self.stats_tree.insert(
                "",
                tk.END,
                values=(tok_name, token_count, chars_per_tok, unique_count),
            )

    def get_comparison_data(self) -> Dict[str, Any]:
        """Return the current comparison data for export."""
        data: Dict[str, Any] = {
            "tokenizers": {},
            "text_length": len(self.get_input_text()),
        }

        for tok_name, (tokens, ids) in self._cached_results.items():
            data["tokenizers"][tok_name] = {
                "token_count": len(tokens),
                "unique_tokens": len(set(tokens)),
                "tokens": tokens[:100],  # Limit for export
                "ids": ids[:100],
            }

        return data
