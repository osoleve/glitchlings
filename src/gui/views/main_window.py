import difflib
import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any, Dict, Iterable, List, Tuple

from glitchlings import SAMPLE_TEXT
from glitchlings.attack.tokenization import resolve_tokenizer

from ..theme import APP_VERSION, COLORS, DEFAULT_TOKENIZERS, FONTS, SCAN_PRESET_OPTIONS
from .glitchling_panel import GlitchlingPanel
from .tokenizer_panel import TokenizerPanel
from .utils import create_tooltip


class VectorFrame(tk.Frame):
    content: tk.Frame
    title_bar: tk.Frame


class MainFrame(ttk.Frame):
    """Main content frame with all UI components."""

    def __init__(self, parent: tk.Tk, controller: Any) -> None:
        super().__init__(parent)
        self.controller = controller
        self.pack(fill=tk.BOTH, expand=True)

        self.seed_var = tk.IntVar(value=151)
        self.auto_update_var = tk.BooleanVar(value=True)
        self.diff_mode_var = tk.StringVar(value="label")
        self.diff_tokenizer_var = tk.StringVar(value="cl100k_base")

        # Scan mode variables
        self.scan_mode_var = tk.BooleanVar(value=False)
        self.scan_count_var = tk.StringVar(value="100")

        self.current_output: str = ""

        self.glitchling_panel: GlitchlingPanel
        self.tokenizer_panel: TokenizerPanel
        self.input_text: scrolledtext.ScrolledText
        self.token_diff_text: scrolledtext.ScrolledText
        self.diff_tokenizer_combo: ttk.Combobox
        self.metrics_tree: ttk.Treeview
        self.status_var: tk.StringVar
        self.status_indicator: tk.Label
        self.scan_count_combo: ttk.Combobox
        self.transform_btn: tk.Button

        self._create_widgets()

        # Register self with controller
        if self.controller:
            self.controller.set_view(self)
            # Sync initial input text to model
            self.controller.update_input_text(self.get_input())

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

        # Right panel is split into upper (Input) and lower (Token Diff/Metrics)
        right_pane = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        # Upper section: Input
        upper_frame = ttk.Frame(right_pane)
        right_pane.add(upper_frame, weight=1)

        # Input section with vector styling
        input_frame = self._create_vector_labelframe(upper_frame, "INPUT")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        # Add clear button to input
        if hasattr(input_frame, "title_bar"):
            clear_btn = tk.Button(
                input_frame.title_bar,
                text="Clear",
                font=FONTS["tiny"],
                fg=COLORS["red"],
                bg=COLORS["dark"],
                activeforeground=COLORS["amber"],
                activebackground=COLORS["red_dim"],
                bd=0,
                relief=tk.FLAT,
                cursor="hand2",
                command=self._clear_input,
            )
            clear_btn.pack(side=tk.RIGHT, padx=6)

        self.input_text = self._create_vector_text(input_frame, height=12)
        self.input_text.insert("1.0", SAMPLE_TEXT)
        self.input_text.bind("<KeyRelease>", lambda e: self._on_input_change())

        # Lower section: Token Diff and Metrics
        lower_frame = ttk.Frame(right_pane)
        right_pane.add(lower_frame, weight=2)

        # Token Diff section
        token_frame = self._create_vector_labelframe(lower_frame, "TOKEN DIFF")
        token_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        # Token diff header with controls - put in content frame
        if hasattr(token_frame, "content"):
            token_content = token_frame.content
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

        raw_radio = tk.Radiobutton(
            token_header,
            text="Raw",
            variable=self.diff_mode_var,
            value="raw",
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
        raw_radio.pack(side=tk.LEFT, padx=8)

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
            values=DEFAULT_TOKENIZERS,
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
            metrics_content = metrics_frame.content
        else:
            metrics_content = metrics_frame

        # Create a container with border for the treeview
        tree_container = tk.Frame(metrics_content, bg=COLORS["border"], padx=1, pady=1)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tree_inner = tk.Frame(tree_container, bg=COLORS["darker"])
        tree_inner.pack(fill=tk.BOTH, expand=True)

        # Create treeview for metrics table
        columns = ("metric", *DEFAULT_TOKENIZERS)
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
        self.metrics_tree.insert("", "end", values=("Token Delta", "-", "-", "-"))

        # Status bar at the bottom
        self._create_status_bar()

    def _create_status_bar(self) -> None:
        """Create a status bar at the bottom of the window."""
        status_frame = tk.Frame(self, bg=COLORS["dark"], height=28)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=(0, 2))
        status_frame.pack_propagate(False)

        # Left side - status indicator and message
        self.status_indicator = tk.Label(
            status_frame,
            text="●",
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            padx=4,
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready · Select glitchlings to begin")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=FONTS["status"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            anchor="w",
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Right side - keyboard shortcut hints
        hint_label = tk.Label(
            status_frame,
            text="F5/Ctrl+↵: Transform │ Ctrl+R: Random Seed │ Ctrl+S: Save",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=8,
        )
        hint_label.pack(side=tk.RIGHT)

        # Separator
        tk.Label(
            status_frame,
            text="│",
            font=FONTS["tiny"],
            fg=COLORS["border"],
            bg=COLORS["dark"],
        ).pack(side=tk.RIGHT)

        # Version
        version_label = tk.Label(
            status_frame,
            text=f"v{APP_VERSION}",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=6,
        )
        version_label.pack(side=tk.RIGHT)

    def _create_vector_labelframe(
        self, parent: ttk.Frame | tk.Frame, title: str, with_copy: bool = False
    ) -> VectorFrame:
        """Create a vector-styled labelframe with optional copy button."""
        outer = VectorFrame(parent, bg=COLORS["border"], padx=1, pady=1)

        inner = tk.Frame(outer, bg=COLORS["black"])
        inner.pack(fill=tk.BOTH, expand=True)

        # Title bar with clean styling
        title_bar = tk.Frame(inner, bg=COLORS["dark"], height=26)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        # Left decoration
        tk.Label(
            title_bar,
            text="▒",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=(6, 0), pady=4)

        title_label = tk.Label(
            title_bar,
            text=title,
            font=FONTS["title"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=4,
        )
        title_label.pack(side=tk.LEFT, pady=4)

        # Right decoration
        tk.Label(
            title_bar,
            text="▒",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, pady=4)

        # Store title bar reference for adding buttons later
        outer.title_bar = title_bar

        # Content area with slight padding
        content = tk.Frame(inner, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Return outer frame for packing, but configure it to behave like content
        outer.content = content
        return outer

    def _create_vector_text(
        self,
        parent: tk.Frame | VectorFrame,
        height: int = 6,
        state: str = tk.NORMAL,
        color: str | None = None,
    ) -> scrolledtext.ScrolledText:
        """Create a vector-styled text widget."""
        # Get the content frame if this is a vector labelframe
        if hasattr(parent, "content"):
            parent = parent.content

        fg_color = color if color else COLORS["green"]

        # Create a border frame
        border_frame = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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
            padx=12,
            pady=10,
            state=state,
            cursor="xterm" if state == tk.NORMAL else "arrow",
            undo=True,  # Enable undo/redo
        )
        text.pack(fill=tk.BOTH, expand=True)

        # Add right-click context menu for editable text
        if state == tk.NORMAL:
            self._add_text_context_menu(text)

        return text

    def _add_text_context_menu(self, text_widget: scrolledtext.ScrolledText) -> None:
        """Add a right-click context menu to a text widget."""
        menu = tk.Menu(
            text_widget,
            tearoff=0,
            bg=COLORS["dark"],
            fg=COLORS["green"],
            activebackground=COLORS["highlight"],
            activeforeground=COLORS["green_bright"],
            font=FONTS["small"],
        )
        menu.add_command(
            label="Cut",
            command=lambda: text_widget.event_generate("<<Cut>>"),
            accelerator="Ctrl+X",
        )
        menu.add_command(
            label="Copy",
            command=lambda: text_widget.event_generate("<<Copy>>"),
            accelerator="Ctrl+C",
        )
        menu.add_command(
            label="Paste",
            command=lambda: text_widget.event_generate("<<Paste>>"),
            accelerator="Ctrl+V",
        )
        menu.add_separator()
        menu.add_command(
            label="Select All",
            command=lambda: text_widget.tag_add(tk.SEL, "1.0", tk.END),
            accelerator="Ctrl+A",
        )
        menu.add_separator()
        menu.add_command(
            label="Undo",
            command=lambda: text_widget.event_generate("<<Undo>>"),
            accelerator="Ctrl+Z",
        )
        menu.add_command(
            label="Redo",
            command=lambda: text_widget.event_generate("<<Redo>>"),
            accelerator="Ctrl+Y",
        )

        def show_menu(event: tk.Event) -> None:
            menu.tk_popup(event.x_root, event.y_root)

        text_widget.bind("<Button-3>", show_menu)

    def _create_top_bar(self) -> None:
        # Header bar with vector styling
        top_bar = tk.Frame(self, bg=COLORS["dark"])
        top_bar.pack(fill=tk.X, padx=2, pady=(2, 0))

        # Title on the left with decorative border
        title_frame = tk.Frame(top_bar, bg=COLORS["dark"])
        title_frame.pack(side=tk.LEFT, padx=8, pady=6)

        title = tk.Label(
            title_frame,
            text="༼ つ ◕_◕ ༽つ GLITCHLINGS",
            font=FONTS["header"],
            fg=COLORS["green_bright"],
            bg=COLORS["dark"],
        )
        title.pack(side=tk.LEFT)

        # Controls on the right - grouped together
        controls_frame = tk.Frame(top_bar, bg=COLORS["dark"])
        controls_frame.pack(side=tk.RIGHT, padx=8, pady=6)

        # Seed control with border
        seed_frame = tk.Frame(controls_frame, bg=COLORS["dark"])
        seed_frame.pack(side=tk.LEFT, padx=(0, 12))

        seed_label = tk.Label(
            seed_frame,
            text="SEED",
            font=FONTS["tiny"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
        )
        seed_label.pack(side=tk.LEFT, padx=(0, 5))

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

        # Randomize seed button with tooltip
        rand_btn = tk.Button(
            seed_frame,
            text="🎲",
            font=FONTS["body"],
            fg=COLORS["amber"],
            bg=COLORS["dark"],
            activeforeground=COLORS["amber_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._randomize_seed,
        )
        rand_btn.pack(side=tk.LEFT, padx=(4, 0))
        create_tooltip(rand_btn, "Randomize seed (Ctrl+R)")

        # Auto-update checkbox with tooltip
        auto_check = tk.Checkbutton(
            controls_frame,
            text="Auto",
            variable=self.auto_update_var,
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["dark"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
            command=self._on_settings_change,
        )
        auto_check.pack(side=tk.LEFT, padx=(0, 8))
        create_tooltip(auto_check, "Auto-transform on changes")

        # Scan mode separator
        tk.Label(
            controls_frame,
            text="│",
            font=FONTS["body"],
            fg=COLORS["border"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=4)

        # Scan mode controls
        scan_frame = tk.Frame(controls_frame, bg=COLORS["dark"])
        scan_frame.pack(side=tk.LEFT, padx=(0, 8))

        scan_check = tk.Checkbutton(
            scan_frame,
            text="Scan",
            variable=self.scan_mode_var,
            font=FONTS["small"],
            fg=COLORS["magenta"],
            bg=COLORS["dark"],
            activeforeground=COLORS["cyan_bright"],
            activebackground=COLORS["dark"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
            command=self._on_scan_mode_toggle,
        )
        scan_check.pack(side=tk.LEFT)
        create_tooltip(scan_check, "Calculate average metrics over multiple seeds")

        # Scan count dropdown
        self.scan_count_combo = ttk.Combobox(
            scan_frame,
            textvariable=self.scan_count_var,
            values=SCAN_PRESET_OPTIONS,
            width=6,
            state="readonly",
        )
        self.scan_count_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.scan_count_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change())

        tk.Label(
            scan_frame,
            text="seeds",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=(2, 0))

        # Transform button - primary action with better styling and hover
        self.transform_btn = tk.Button(
            controls_frame,
            text="▶ TRANSFORM",
            font=FONTS["section"],
            fg=COLORS["black"],
            bg=COLORS["green"],
            activeforeground=COLORS["black"],
            activebackground=COLORS["green_bright"],
            bd=0,
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._transform_text,
        )
        self.transform_btn.pack(side=tk.LEFT, padx=(4, 0))
        create_tooltip(self.transform_btn, "Transform text (F5 or Ctrl+Enter)")

        # Hover effects for transform button
        self.transform_btn.bind(
            "<Enter>",
            lambda e: self.transform_btn.config(bg=COLORS["green_bright"])
            if not self.scan_mode_var.get()
            else self.transform_btn.config(bg=COLORS["cyan"]),
        )
        self.transform_btn.bind(
            "<Leave>",
            lambda e: self.transform_btn.config(bg=COLORS["green"])
            if not self.scan_mode_var.get()
            else self.transform_btn.config(bg=COLORS["magenta"]),
        )

    def _randomize_seed(self) -> None:
        """Randomize the seed value."""
        if self.controller:
            self.controller.randomize_seed()

    def _on_scan_mode_toggle(self) -> None:
        """Called when scan mode is toggled."""
        if self.controller:
            self.controller.toggle_scan_mode(self.scan_mode_var.get())

    def _on_settings_change(self) -> None:
        """Called when any setting changes."""
        if self.controller:
            try:
                scan_count = int(self.scan_count_var.get())
            except ValueError:
                scan_count = 100

            self.controller.update_settings(
                self.seed_var.get(),
                self.auto_update_var.get(),
                self.scan_mode_var.get(),
                scan_count,
            )

    def _on_input_change(self) -> None:
        """Called when input text changes."""
        if self.controller:
            self.controller.update_input_text(self.get_input())

    def _transform_text(self) -> None:
        """Apply selected glitchlings to the input text."""
        if self.controller:
            self.controller.transform_text()

    def _clear_input(self) -> None:
        """Clear just the input text."""
        self.input_text.delete("1.0", tk.END)
        self._on_input_change()

    # --- Public Interface for Controller ---

    def get_input(self) -> str:
        """Get the current input text."""
        return self.input_text.get("1.0", tk.END).strip()

    def set_input(self, text: str) -> None:
        """Set the input text."""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)

    def get_output(self) -> str:
        """Get the current output text."""
        return self.current_output

    def set_output(self, text: str) -> None:
        """Set the output text."""
        self.current_output = text
        self._update_token_diff()

    def set_status(self, message: str, color: str = "green") -> None:
        """Set the status message with colored indicator."""
        self.status_var.set(message)
        color_map = {
            "green": COLORS["green"],
            "amber": COLORS["amber"],
            "red": COLORS["red"],
            "cyan": COLORS["cyan"],
            "magenta": COLORS["magenta"],
        }
        self.status_indicator.config(fg=color_map.get(color, COLORS["green"]))

    def update_seed(self, seed: int) -> None:
        self.seed_var.set(seed)

    def set_auto_update(self, enabled: bool) -> None:
        self.auto_update_var.set(enabled)

    def update_transform_button(self, is_scan: bool) -> None:
        if is_scan:
            self.transform_btn.config(text="▶ SCAN", bg=COLORS["magenta"])
        else:
            self.transform_btn.config(text="▶ TRANSFORM", bg=COLORS["green"])

    def set_scan_running(self, running: bool) -> None:
        if running:
            self.transform_btn.config(text="■ CANCEL", bg=COLORS["red"])
        else:
            self.update_transform_button(self.scan_mode_var.get())

    def get_enabled_glitchlings(self) -> List[Tuple[Any, Dict[str, Any]]]:
        return self.glitchling_panel.get_enabled_glitchlings()

    def get_enabled_tokenizers(self) -> List[str]:
        return self.tokenizer_panel.get_enabled_tokenizers()

    def _configure_metrics_table(self, tokenizers: List[str]) -> List[str]:
        """Set up columns and dropdown entries for the metrics table."""
        tokenizers = tokenizers or [DEFAULT_TOKENIZERS[0]]
        columns = ["metric", *tokenizers]
        self.metrics_tree["columns"] = columns

        for col in columns:
            display_name = col.replace("_", " ").replace("-", " ").title()
            self.metrics_tree.heading(col, text=display_name)
            self.metrics_tree.column(col, width=100, anchor="center")
        self.metrics_tree.column("metric", width=180, anchor="w")

        self.diff_tokenizer_combo["values"] = tokenizers
        if tokenizers and self.diff_tokenizer_var.get() not in tokenizers:
            self.diff_tokenizer_var.set(tokenizers[0])

        return tokenizers

    def _replace_metrics_rows(self, rows: Iterable[Tuple[str, List[str]]]) -> None:
        """Replace metrics rows with supplied data."""
        for item in self.metrics_tree.get_children():
            self.metrics_tree.delete(item)

        for metric_name, values in rows:
            self.metrics_tree.insert("", "end", values=(metric_name, *values))

    def update_metrics_display(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """Update the metrics table."""
        tokenizers = self._configure_metrics_table(list(metrics.keys()))
        if not metrics:
            self._replace_metrics_rows([])
            return

        rows: List[Tuple[str, List[str]]] = []

        rows.append(
            (
                "Token Delta",
                [str(metrics[tok].get("token_delta", "-")) for tok in tokenizers],
            )
        )
        rows.append(
            (
                "Jensen-Shannon Divergence",
                [str(metrics[tok].get("jsd", "-")) for tok in tokenizers],
            )
        )
        rows.append(
            (
                "Normalized Edit Distance",
                [str(metrics[tok].get("ned", "-")) for tok in tokenizers],
            )
        )
        rows.append(
            ("Subsequence Retention", [str(metrics[tok].get("sr", "-")) for tok in tokenizers])
        )

        self._replace_metrics_rows(rows)

    def display_scan_results(
        self, tokenizers: List[str], formatted_rows: List[Tuple[str, List[str]]]
    ) -> None:
        """Update metrics table with scan results."""
        active_tokenizers = self._configure_metrics_table(tokenizers)
        if not formatted_rows:
            self._replace_metrics_rows([])
            return

        expected_cols = len(active_tokenizers)
        normalized_rows: List[Tuple[str, List[str]]] = []
        for metric_name, values in formatted_rows:
            row_values = list(values)[:expected_cols]
            if len(row_values) < expected_cols:
                row_values.extend(["-"] * (expected_cols - len(row_values)))
            normalized_rows.append((metric_name, row_values))

        self._replace_metrics_rows(normalized_rows)

    def clear_all(self) -> None:
        """Clear all text and reset seed."""
        self.input_text.delete("1.0", tk.END)
        self.set_output("")
        self.seed_var.set(151)
        if self.controller:
            self.controller.update_settings(
                151, self.auto_update_var.get(), self.scan_mode_var.get(), 100
            )

    def _update_token_diff(self) -> None:
        """Update the token diff display with inline diff highlighting."""
        input_text = self.get_input()
        output_text = self.get_output()

        self.token_diff_text.config(state=tk.NORMAL)
        self.token_diff_text.delete("1.0", tk.END)

        # Configure diff tags for highlighting
        self.token_diff_text.tag_configure(
            "added", foreground=COLORS["black"], background=COLORS["green"]
        )
        self.token_diff_text.tag_configure(
            "removed", foreground=COLORS["black"], background=COLORS["red"]
        )
        self.token_diff_text.tag_configure(
            "changed", foreground=COLORS["black"], background=COLORS["amber"]
        )
        self.token_diff_text.tag_configure("unchanged", foreground=COLORS["green_dim"])
        self.token_diff_text.tag_configure("header", foreground=COLORS["cyan"])

        if not input_text or not output_text:
            self.token_diff_text.insert("1.0", "No text to compare")
            self.token_diff_text.config(state=tk.DISABLED)
            return

        mode = self.diff_mode_var.get()

        if mode == "raw":
            self.token_diff_text.insert("1.0", output_text)
            self.token_diff_text.config(state=tk.DISABLED)
            return

        try:
            tokenizer_name = self.diff_tokenizer_var.get()
            tok = resolve_tokenizer(tokenizer_name)

            if tok is None:
                self.token_diff_text.insert("1.0", f"Tokenizer '{tokenizer_name}' unavailable")
                self.token_diff_text.config(state=tk.DISABLED)
                return

            input_tokens, input_ids = tok.encode(input_text)
            output_tokens, output_ids = tok.encode(output_text)

            # Get token representations based on mode
            if mode == "id":
                input_items = [str(t) for t in input_ids]
                output_items = [str(t) for t in output_ids]
            else:
                input_items = input_tokens
                output_items = output_tokens

            # Insert header
            delta = len(output_tokens) - len(input_tokens)
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            header = f"Token Diff: {len(input_tokens)} → {len(output_tokens)} ({delta_str})\t"
            self.token_diff_text.insert(tk.END, header, "header")

            # Compute diff using SequenceMatcher
            matcher = difflib.SequenceMatcher(None, input_items, output_items)

            # Legend
            self.token_diff_text.insert(tk.END, "[+added] ", "added")
            self.token_diff_text.insert(tk.END, "[-removed] ", "removed")
            self.token_diff_text.insert(tk.END, "\n\n")
            # Process diff opcodes
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    # Unchanged tokens - show dimmed
                    for item in input_items[i1:i2]:
                        display = f"[{item}] " if mode == "label" else f"{item} "
                        self.token_diff_text.insert(tk.END, display, "unchanged")
                elif tag == "replace":
                    # Changed tokens - show old struck through, new highlighted
                    for item in input_items[i1:i2]:
                        display = f"[-{item}] " if mode == "label" else f"-{item} "
                        self.token_diff_text.insert(tk.END, display, "removed")
                    for item in output_items[j1:j2]:
                        display = f"[+{item}] " if mode == "label" else f"+{item} "
                        self.token_diff_text.insert(tk.END, display, "added")
                elif tag == "delete":
                    # Deleted tokens - show in red
                    for item in input_items[i1:i2]:
                        display = f"[-{item}] " if mode == "label" else f"-{item} "
                        self.token_diff_text.insert(tk.END, display, "removed")
                elif tag == "insert":
                    # Inserted tokens - show in green
                    for item in output_items[j1:j2]:
                        display = f"[+{item}] " if mode == "label" else f"+{item} "
                        self.token_diff_text.insert(tk.END, display, "added")

        except ValueError as e:
            self.token_diff_text.insert("1.0", f"Could not load tokenizer: {e}")
        except Exception as e:
            self.token_diff_text.insert("1.0", f"Error: {e}")

        self.token_diff_text.config(state=tk.DISABLED)
