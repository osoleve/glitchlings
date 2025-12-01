from __future__ import annotations

import difflib
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext, ttk
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Tuple, cast

from glitchlings import SAMPLE_TEXT
from glitchlings.attack.tokenization import resolve_tokenizer

from ..model import ScanResult
from ..preferences import Preferences
from ..theme import APP_VERSION, COLORS, DEFAULT_TOKENIZERS, FONTS
from .glitchling_panel import GlitchlingPanel
from .tokenizer_panel import TokenizerPanel
from .utils import create_tooltip

if TYPE_CHECKING:
    from ..session import SessionConfig


class VectorFrame(tk.Frame):
    content: tk.Frame
    title_bar: tk.Frame


class MainFrame(ttk.Frame):
    """Main content frame with all UI components."""

    def __init__(
        self,
        parent: tk.Tk,
        controller: Any,
        preferences: Preferences,
        on_preferences_change: Callable[[Preferences], None] | None = None,
        copy_output_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.preferences = preferences
        self.on_preferences_change = on_preferences_change
        self.copy_output_callback = copy_output_callback
        self.pack(fill=tk.BOTH, expand=True)

        self.seed_var = tk.IntVar(value=151)
        self.auto_update_var = tk.BooleanVar(value=True)
        self.diff_mode_var = tk.StringVar(value="label")
        self.diff_tokenizer_var = tk.StringVar(value="cl100k_base")

        # Multi-seed aggregation (for main transform)
        self.multi_seed_var = tk.BooleanVar(value=False)
        self.multi_seed_count_var = tk.StringVar(value="10")

        self.current_output: str = ""

        self.glitchling_panel: GlitchlingPanel
        self.tokenizer_panel: TokenizerPanel
        self.input_text: scrolledtext.ScrolledText
        self.token_diff_text: scrolledtext.ScrolledText
        self.diff_tokenizer_combo: ttk.Combobox
        self.metrics_tree: ttk.Treeview
        self.status_var: tk.StringVar
        self.status_indicator: tk.Label
        self.multi_seed_combo: ttk.Combobox
        self.transform_btn: tk.Button
        self.output_preview_text: scrolledtext.ScrolledText
        self.main_pane: ttk.PanedWindow
        self.sidebar_frame: ttk.Frame
        self.sidebar_toggle_btn: tk.Button
        self.content_tabs: ttk.Notebook
        self.input_tab: ttk.Frame
        self.token_diff_tab: ttk.Frame
        self.sidebar_collapsed = False
        self._sidebar_last_width = 320
        self.content_font = tkfont.Font(
            family=self.preferences.font_family,
            size=self.preferences.font_size,
        )

        self._create_widgets()

        if self.preferences.last_tab == "diff":
            self.content_tabs.select(self.token_diff_tab)

        if self.preferences.sidebar_collapsed:
            self.after(10, self._toggle_sidebar)

        # Register self with controller
        if self.controller:
            self.controller.set_view(self)
            # Sync initial input text to model
            self.controller.update_input_text(self.get_input())

    def _create_widgets(self) -> None:
        # Top bar with seed
        self._create_top_bar()

        # Main content with paned windows
        self.main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        # Left sidebar (collapsible) with Glitchlings + Tokenizers
        self.sidebar_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.sidebar_frame, weight=1)

        sidebar_header = tk.Frame(self.sidebar_frame, bg=COLORS["dark"])
        sidebar_header.pack(fill=tk.X, padx=4, pady=(0, 4))

        tk.Label(
            sidebar_header,
            text="PANEL STACK",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=(6, 0))

        left_pane = ttk.PanedWindow(self.sidebar_frame, orient=tk.VERTICAL)
        left_pane.pack(fill=tk.BOTH, expand=True)

        self.glitchling_panel = GlitchlingPanel(left_pane, self._on_settings_change)
        left_pane.add(self.glitchling_panel, weight=2)

        self.tokenizer_panel = TokenizerPanel(
            left_pane,
            self._on_tokenizers_change,
            initial_tokenizers=self.preferences.default_tokenizers,
        )
        left_pane.add(self.tokenizer_panel, weight=1)

        # Right panel
        right_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(right_frame, weight=3)

        # Right panel is split into upper tabs (Input/Token Diff) and lower metrics
        right_pane = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        tabs_frame = ttk.Frame(right_pane)
        right_pane.add(tabs_frame, weight=3)

        self.content_tabs = ttk.Notebook(tabs_frame)
        self.content_tabs.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 3))
        self.content_tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Store reference to right_pane for metrics visibility toggling
        self._right_pane = right_pane

        self.input_tab = ttk.Frame(self.content_tabs)
        self.token_diff_tab = ttk.Frame(self.content_tabs)
        self.dataset_tab = ttk.Frame(self.content_tabs)
        self.sweep_tab = ttk.Frame(self.content_tabs)
        self.charts_tab = ttk.Frame(self.content_tabs)

        self.content_tabs.add(self.input_tab, text="Input")
        self.content_tabs.add(self.token_diff_tab, text="Token Diff")
        self.content_tabs.add(self.dataset_tab, text="Datasets")
        self.content_tabs.add(self.sweep_tab, text="Sweep")
        self.content_tabs.add(self.charts_tab, text="Charts")

        # Input section with vector styling
        input_frame = self._create_vector_labelframe(self.input_tab, "INPUT")
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

        # Token Diff tab
        token_frame = self._create_vector_labelframe(self.token_diff_tab, "TOKEN DIFF")
        token_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        # Token diff header with controls - put in content frame
        if hasattr(token_frame, "content"):
            token_content = token_frame.content
        else:
            token_content = token_frame

        token_header = tk.Frame(token_content, bg=COLORS["black"])
        token_header.pack(fill=tk.X, padx=6, pady=(4, 2))

        # View Mode Group
        view_frame = tk.Frame(token_header, bg=COLORS["black"])
        view_frame.pack(side=tk.LEFT)

        tk.Label(
            view_frame,
            text="View:",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT, padx=(0, 4))

        id_radio = tk.Radiobutton(
            view_frame,
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
            view_frame,
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
            view_frame,
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

        # Spacer / Separator
        tk.Label(
            token_header,
            text="│",
            font=FONTS["tiny"],
            fg=COLORS["border"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT, padx=12)

        # Tokenizer Selection Group
        tok_frame = tk.Frame(token_header, bg=COLORS["black"])
        tok_frame.pack(side=tk.LEFT)

        tok_label = tk.Label(
            tok_frame,
            text="Tokenizer:",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        )
        tok_label.pack(side=tk.LEFT, padx=(0, 4))

        self.diff_tokenizer_combo = ttk.Combobox(
            tok_frame,
            textvariable=self.diff_tokenizer_var,
            values=DEFAULT_TOKENIZERS,
            width=22,
            state="readonly",
        )
        self.diff_tokenizer_combo.pack(side=tk.LEFT)
        self.diff_tokenizer_combo.bind("<<ComboboxSelected>>", lambda e: self._update_token_diff())

        initial_tokenizers = self.tokenizer_panel.get_all_tokenizers()
        if initial_tokenizers:
            self.diff_tokenizer_combo["values"] = initial_tokenizers
            if self.diff_tokenizer_var.get() not in initial_tokenizers:
                self.diff_tokenizer_var.set(initial_tokenizers[0])

        self.token_diff_text = self._create_vector_text(token_content, height=5, state=tk.DISABLED)

        # Output preview with copy
        preview_frame = self._create_vector_labelframe(
            token_content,
            "OUTPUT PREVIEW",
            with_copy=True,
            copy_command=self._copy_output_preview,
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        self.output_preview_text = self._create_vector_text(
            preview_frame, height=5, state=tk.DISABLED
        )

        # Configure tags for diff highlighting - vector colors
        self.token_diff_text.tag_configure("added", foreground=COLORS["cyan"])
        self.token_diff_text.tag_configure("removed", foreground=COLORS["red"], overstrike=True)
        self.token_diff_text.tag_configure("unchanged", foreground=COLORS["green_dim"])

        # Dataset tab
        from .dataset_panel import DatasetPanel

        self.dataset_panel = DatasetPanel(
            self.dataset_tab,
            on_dataset_loaded=self._on_dataset_loaded,
            on_sample_selected=self._on_sample_selected,
            on_process_dataset=self._start_dataset_processing,
        )
        self.dataset_panel.pack(fill=tk.BOTH, expand=True)

        # Grid Sweep tab
        from .grid_sweep_panel import GridSweepPanel

        self.sweep_panel = GridSweepPanel(
            self.sweep_tab,
            service=self.controller.service if self.controller else None,
            get_input_text=self.get_input,
            get_tokenizers=self.get_enabled_tokenizers,
            on_results_changed=self._on_sweep_results_changed,
        )
        self.sweep_panel.pack(fill=tk.BOTH, expand=True)

        # Charts tab
        from .charts_panel import ChartsPanel

        self.charts_panel = ChartsPanel(
            self.charts_tab,
            get_scan_results=self._get_scan_results,
            get_sweep_results=lambda: self.sweep_panel.get_results(),
            get_dataset_results=self._get_dataset_results,
        )
        self.charts_panel.pack(fill=tk.BOTH, expand=True)

        # Metrics section (visible only on Input/Token Diff tabs)
        self._metrics_container = ttk.Frame(right_pane)
        right_pane.add(self._metrics_container, weight=2)

        metrics_frame = self._create_vector_labelframe(self._metrics_container, "METRICS")
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

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
        self,
        parent: ttk.Frame | tk.Frame,
        title: str,
        with_copy: bool = False,
        copy_command: Callable[[], None] | None = None,
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
            text="░",
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
            text="░",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, pady=4)

        if with_copy and copy_command:
            copy_btn = tk.Button(
                title_bar,
                text="Copy",
                font=FONTS["tiny"],
                fg=COLORS["green"],
                bg=COLORS["dark"],
                activeforeground=COLORS["green_bright"],
                activebackground=COLORS["highlight"],
                bd=0,
                relief=tk.FLAT,
                cursor="hand2",
                command=copy_command,
            )
            copy_btn.pack(side=tk.RIGHT, padx=6)

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
        font: tkfont.Font | None = None,
    ) -> scrolledtext.ScrolledText:
        """Create a vector-styled text widget."""
        if hasattr(parent, "content"):
            parent = parent.content

        fg_color = color if color else COLORS["green"]

        border_frame = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        text = scrolledtext.ScrolledText(
            border_frame,
            wrap=tk.WORD,
            height=height,
            font=font or self.content_font or FONTS["mono"],
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
            undo=True,
        )
        text.pack(fill=tk.BOTH, expand=True)

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

        self.sidebar_toggle_btn = tk.Button(
            title_frame,
            text="Hide Panels",
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._toggle_sidebar,
        )
        self.sidebar_toggle_btn.pack(side=tk.LEFT, padx=(10, 0))

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

        # Multi-seed aggregation separator
        tk.Label(
            controls_frame,
            text="│",
            font=FONTS["body"],
            fg=COLORS["border"],
            bg=COLORS["dark"],
        ).pack(side=tk.LEFT, padx=4)

        # Multi-seed aggregation controls (for main transform)
        multi_seed_frame = tk.Frame(controls_frame, bg=COLORS["dark"])
        multi_seed_frame.pack(side=tk.LEFT, padx=(0, 8))

        multi_seed_check = tk.Checkbutton(
            multi_seed_frame,
            text="Avg",
            variable=self.multi_seed_var,
            font=FONTS["small"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            activeforeground=COLORS["cyan_bright"],
            activebackground=COLORS["dark"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
            command=self._on_settings_change,
        )
        multi_seed_check.pack(side=tk.LEFT)
        create_tooltip(multi_seed_check, "Show mean±std metrics averaged over multiple seeds")

        # Multi-seed count dropdown
        self.multi_seed_combo = ttk.Combobox(
            multi_seed_frame,
            textvariable=self.multi_seed_count_var,
            values=("5", "10", "25", "50"),
            width=4,
            state="readonly",
        )
        self.multi_seed_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.multi_seed_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change())

        tk.Label(
            multi_seed_frame,
            text="×",
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
            lambda e: self.transform_btn.config(bg=COLORS["green_bright"]),
        )
        self.transform_btn.bind(
            "<Leave>",
            lambda e: self.transform_btn.config(bg=COLORS["green"]),
        )

    def _toggle_sidebar(self) -> None:
        """Collapse or expand the glitchling/tokenizer sidebar."""
        if self.sidebar_collapsed:
            self.main_pane.insert(0, self.sidebar_frame, weight=1)
            if self._sidebar_last_width:
                try:
                    cast(Any, self.main_pane).sashpos(0, self._sidebar_last_width)
                except tk.TclError:
                    pass
            self.sidebar_toggle_btn.config(text="Hide Panels")
            self.sidebar_collapsed = False
            self._update_preferences(sidebar_collapsed=False)
            return

        self._sidebar_last_width = max(self.sidebar_frame.winfo_width(), 240)
        self.main_pane.forget(self.sidebar_frame)
        self.sidebar_toggle_btn.config(text="Show Panels")
        self.sidebar_collapsed = True
        self._update_preferences(sidebar_collapsed=True)

    def _update_preferences(self, **kwargs: object) -> None:
        """Persist updated preferences through the app callback."""
        self.preferences = self.preferences.with_updates(**kwargs)
        if self.on_preferences_change:
            self.on_preferences_change(self.preferences)

    def _randomize_seed(self) -> None:
        """Randomize the seed value."""
        if self.controller:
            self.controller.randomize_seed()

    def _on_tokenizers_change(self) -> None:
        """Handle updates from the tokenizer panel."""
        self._on_settings_change()
        self._update_preferences(default_tokenizers=self.tokenizer_panel.get_all_tokenizers())

    def _on_settings_change(self) -> None:
        """Called when any setting changes."""
        if self.controller:
            try:
                multi_seed_count = int(self.multi_seed_count_var.get())
            except ValueError:
                multi_seed_count = 10

            self.controller.update_settings(
                self.seed_var.get(),
                self.auto_update_var.get(),
                self.multi_seed_var.get(),
                multi_seed_count,
            )

    def _on_input_change(self) -> None:
        """Called when input text changes."""
        if self.controller:
            self.controller.update_input_text(self.get_input())

    def _on_tab_changed(self, _event: tk.Event) -> None:
        """Track tab selection for persistence and toggle metrics visibility."""
        try:
            tabs = cast(Any, self.content_tabs)
            idx = tabs.index(tabs.select())
        except tk.TclError:
            return

        self._update_preferences(last_tab="diff" if idx == 1 else "input")

        # Show metrics only on Input (0) or Token Diff (1) tabs
        self._update_metrics_visibility(idx in (0, 1))

    def _update_metrics_visibility(self, visible: bool) -> None:
        """Show or hide the metrics panel based on current tab."""
        if not hasattr(self, "_metrics_container") or not hasattr(self, "_right_pane"):
            return

        try:
            panes = list(self._right_pane.panes())
            metrics_in_pane = str(self._metrics_container) in panes
        except tk.TclError:
            return

        if visible and not metrics_in_pane:
            self._right_pane.add(self._metrics_container, weight=2)
        elif not visible and metrics_in_pane:
            self._right_pane.forget(self._metrics_container)

    def _focus_results_tab(self) -> None:
        """Move to the token diff tab when running a transform."""
        try:
            tabs = cast(Any, self.content_tabs)
            current_tab = tabs.select()
        except tk.TclError:
            return

        if current_tab == str(self.input_tab):
            tabs.select(self.token_diff_tab)

    def _copy_output_preview(self) -> None:
        """Copy output text, delegating to the app when available."""
        if self.copy_output_callback:
            self.copy_output_callback()
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(self.get_output())
        except tk.TclError:
            pass

    def _transform_text(self) -> None:
        """Apply selected glitchlings to the input text."""
        self._focus_results_tab()
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
        self._update_output_preview(text)
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

    def apply_session(self, config: "SessionConfig") -> None:
        """Apply a loaded session configuration to the UI."""
        # Update seed and settings
        self.seed_var.set(config.seed)
        self.auto_update_var.set(config.auto_update)
        self.diff_mode_var.set(config.diff_mode)
        self.diff_tokenizer_var.set(config.diff_tokenizer)

        # Update tokenizers
        self.tokenizer_panel.set_tokenizers(config.tokenizers)

        # Update glitchlings - enable matching ones with their parameters
        for name, var in self.glitchling_panel.enabled.items():
            var.set(False)  # Reset all

        for glitch_name, params in config.glitchlings:
            if glitch_name in self.glitchling_panel.enabled:
                self.glitchling_panel.enabled[glitch_name].set(True)
                # Set parameters
                if glitch_name in self.glitchling_panel.param_widgets:
                    for param_name, value in params.items():
                        if param_name in self.glitchling_panel.param_widgets[glitch_name]:
                            self.glitchling_panel.param_widgets[glitch_name][param_name].set(value)

        # Trigger settings sync
        self._on_settings_change()

    def apply_preferences(self, preferences: Preferences) -> None:
        """Apply new preference values and update UI accordingly."""
        self.preferences = preferences
        self.content_font.config(
            family=preferences.font_family,
            size=preferences.font_size,
        )

        self.tokenizer_panel.set_tokenizers(preferences.default_tokenizers)
        tok_values = self.tokenizer_panel.get_all_tokenizers()
        self._configure_metrics_table(tok_values)

        if tok_values and self.diff_tokenizer_var.get() not in tok_values:
            self.diff_tokenizer_var.set(tok_values[0])

        self._update_output_preview(self.get_output())
        self._update_token_diff()

        tabs = cast(Any, self.content_tabs)
        if preferences.last_tab == "diff":
            tabs.select(self.token_diff_tab)
        else:
            tabs.select(self.input_tab)

        if preferences.sidebar_collapsed != self.sidebar_collapsed:
            self._toggle_sidebar()

    def get_enabled_glitchlings(self) -> List[Tuple[Any, Dict[str, Any]]]:
        return self.glitchling_panel.get_enabled_glitchlings()

    def get_enabled_tokenizers(self) -> List[str]:
        return self.tokenizer_panel.get_enabled_tokenizers()

    def _get_scan_results(self) -> Dict[str, ScanResult]:
        """Get scan results for charts panel (deprecated - returns empty)."""
        return {}

    def _get_dataset_results(self) -> Dict[str, ScanResult]:
        """Get dataset batch results for charts panel."""
        if self.controller and self.controller.model:
            return cast(Dict[str, ScanResult], self.controller.model.dataset_results)
        return {}

    def set_dataset_running(self, running: bool, total: int = 0) -> None:
        """Update dataset batch UI state."""
        if hasattr(self, "dataset_panel"):
            self.dataset_panel.set_batch_running(running, total=total)

    def update_dataset_progress(self, current: int, total: int) -> None:
        """Proxy dataset progress updates to the panel."""
        if hasattr(self, "dataset_panel"):
            self.dataset_panel.update_batch_progress(current, total)

    def display_dataset_results(
        self, tokenizers: List[str], formatted_rows: List[Tuple[str, List[str]]], processed: int
    ) -> None:
        """Render aggregated dataset metrics in the dataset tab."""
        if hasattr(self, "dataset_panel"):
            self.dataset_panel.display_batch_results(tokenizers, formatted_rows, processed)

    def _start_dataset_processing(self, samples: List[str] | None = None) -> None:
        """Trigger dataset batch processing via the controller."""
        if not self.controller or not hasattr(self, "dataset_panel"):
            return
        batch_samples = samples if samples is not None else self.dataset_panel.get_samples()
        self.controller.process_dataset(batch_samples)

    def _on_sweep_results_changed(self) -> None:
        """Refresh charts when sweep results change."""
        if hasattr(self, "charts_panel"):
            self.charts_panel.refresh()

    def refresh_charts(self) -> None:
        """Public refresh entry for other components."""
        if hasattr(self, "charts_panel"):
            self.charts_panel.refresh()

    def _on_dataset_loaded(self, samples: List[str]) -> None:
        """Handle dataset loaded callback."""
        if not samples:
            self.set_status("Dataset loaded but empty", "amber")
            return

        if self.controller:
            self.controller.model.dataset_results = {}
            self.controller.model.dataset_total = 0
            self.controller.model.dataset_processed = 0

        self.refresh_charts()
        self.set_status(f"Dataset loaded: {len(samples)} samples", "cyan")

    def _on_sample_selected(self, sample: str, index: int, total: int) -> None:
        """Sync a dataset sample into the input panel."""
        self.set_input(sample)
        self._on_input_change()
        self.set_status(f"Sample {index}/{total} loaded from dataset", "cyan")

    def _update_output_preview(self, text: str) -> None:
        """Refresh the inline output preview box."""
        self.output_preview_text.config(state=tk.NORMAL)
        self.output_preview_text.delete("1.0", tk.END)
        if text:
            self.output_preview_text.insert("1.0", text)
        self.output_preview_text.config(state=tk.DISABLED)

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
