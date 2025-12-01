import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Any, Dict, List, Tuple

from ..theme import AVAILABLE_GLITCHLINGS, COLORS, FONTS, GLITCHLING_DESCRIPTIONS, GLITCHLING_PARAMS
from .utils import create_tooltip


class GlitchlingFrame(tk.Frame):
    """Custom frame that stores glitchling-specific attributes."""

    def __init__(self, parent: tk.Frame | tk.Canvas, name: str) -> None:
        super().__init__(parent, bg=COLORS["black"])
        self.glitchling_name = name
        self.expand_btn: tk.Button | None = None
        self.param_frame: tk.Frame | None = None
        self.header_frame: tk.Frame | None = None


class GlitchlingPanel(ttk.Frame):
    """Panel showing expandable glitchling list with parameter controls."""

    def __init__(self, parent: ttk.PanedWindow, on_change_callback: Any) -> None:
        super().__init__(parent)
        self.on_change = on_change_callback
        self.expanded: Dict[str, bool] = {}
        self.enabled: Dict[str, tk.BooleanVar] = {}
        self.param_widgets: Dict[str, Dict[str, Any]] = {}
        self.frames: Dict[str, GlitchlingFrame] = {}

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header with vector terminal styling
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        header_inner = tk.Frame(header_frame, bg=COLORS["dark"])
        header_inner.pack(fill=tk.X)

        header = tk.Label(
            header_inner,
            text="▓▒░ GLITCHLINGS ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=8,
            pady=5,
        )
        header.pack(side=tk.LEFT)

        # Count indicator with better styling
        self.count_var = tk.StringVar(value="0 active")
        count_label = tk.Label(
            header_inner,
            textvariable=self.count_var,
            font=FONTS["tiny"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            padx=8,
        )
        count_label.pack(side=tk.RIGHT, padx=6, pady=5)

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

        # Bind mousewheel only when hovering over canvas
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Create glitchling entries
        for cls in AVAILABLE_GLITCHLINGS:
            self._create_glitchling_entry(cls)

    def _bind_mousewheel(self, event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _create_glitchling_entry(self, cls: type[Any]) -> None:
        name = cls.__name__
        self.expanded[name] = False
        self.enabled[name] = tk.BooleanVar(value=False)
        self.enabled[name].trace_add("write", lambda *args: self._update_glitchling_style(name))
        self.param_widgets[name] = {}

        # Main frame for this glitchling with hover effect
        frame = GlitchlingFrame(self.scrollable_frame, name)
        frame.pack(fill=tk.X, padx=3, pady=2)
        self.frames[name] = frame

        # Header row with expand button and checkbox
        header_frame = tk.Frame(frame, bg=COLORS["black"])
        header_frame.pack(fill=tk.X, pady=1)
        frame.header_frame = header_frame

        # Expand/collapse button - vector style with better visual feedback
        expand_btn = tk.Button(
            header_frame,
            text="▸",
            width=2,
            font=FONTS["small"],
            fg=COLORS["green_muted"],
            bg=COLORS["black"],
            activeforeground=COLORS["cyan"],
            activebackground=COLORS["black"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=partial(self._toggle_expand, name),
        )
        expand_btn.pack(side=tk.LEFT, padx=(4, 4))
        frame.expand_btn = expand_btn

        # Bind hover effects to expand button
        def on_expand_enter(event: tk.Event) -> None:
            expand_btn.config(fg=COLORS["cyan"])

        def on_expand_leave(event: tk.Event) -> None:
            fg = COLORS["cyan"] if self.expanded.get(name) else COLORS["green_muted"]
            expand_btn.config(fg=fg)

        expand_btn.bind("<Enter>", on_expand_enter)
        expand_btn.bind("<Leave>", on_expand_leave)

        # Enable checkbox - vector style with improved visuals
        check = tk.Checkbutton(
            header_frame,
            text=name,
            variable=self.enabled[name],
            command=self.on_change,
            font=FONTS["glitch_name"],
            fg=COLORS["green"],
            bg=COLORS["black"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["black"],
            selectcolor=COLORS["darker"],
            highlightthickness=0,
            cursor="hand2",
        )
        check.pack(side=tk.LEFT, padx=2)

        # Bind hover effect to checkbox
        def on_check_enter(event: tk.Event) -> None:
            check.config(fg=COLORS["green_bright"])

        def on_check_leave(event: tk.Event) -> None:
            check.config(fg=COLORS["green"])

        check.bind("<Enter>", on_check_enter)
        check.bind("<Leave>", on_check_leave)

        # Description label (tooltip-like) - truncate if too long
        desc = GLITCHLING_DESCRIPTIONS.get(name, "")
        if desc:
            # Truncate long descriptions
            display_desc = desc if len(desc) <= 45 else desc[:42] + "..."
            desc_label = tk.Label(
                header_frame,
                text=f"· {display_desc}",
                font=FONTS["tiny"],
                fg=COLORS["green_dim"],
                bg=COLORS["black"],
            )
            desc_label.pack(side=tk.LEFT, padx=(6, 0))
            # Show full description on hover via title attribute
            create_tooltip(desc_label, desc)

        # Parameter frame (initially hidden)
        param_frame = tk.Frame(frame, bg=COLORS["black"])
        frame.param_frame = param_frame

        # Create parameter widgets
        if name in GLITCHLING_PARAMS:
            for i, (param_name, param_info) in enumerate(GLITCHLING_PARAMS[name].items()):
                self._create_param_widget(param_frame, name, param_name, param_info, i)

    def _update_glitchling_style(self, name: str) -> None:
        """Update the visual style of a glitchling entry based on enabled state."""
        self._update_count()
        frame = self.frames.get(name)
        if not frame or not frame.header_frame:
            return

        is_enabled = self.enabled[name].get()
        bg_color = COLORS["dark"] if is_enabled else COLORS["black"]
        fg_color = COLORS["green_bright"] if is_enabled else COLORS["green"]

        frame.header_frame.config(bg=bg_color)

        # Update children styles
        for child in frame.header_frame.winfo_children():
            if isinstance(child, tk.Button):  # Expand button
                child.config(bg=bg_color, activebackground=bg_color)
            elif isinstance(child, tk.Checkbutton):
                child.config(bg=bg_color, activebackground=bg_color, fg=fg_color)
            elif isinstance(child, tk.Label):
                child.config(bg=bg_color)

    def _create_param_widget(
        self,
        parent: tk.Frame,
        glitchling_name: str,
        param_name: str,
        param_info: Dict[str, Any],
        row_idx: int,
    ) -> None:
        # Format parameter name: snake_case to Title Case
        display_name = param_name.replace("_", " ").title()

        label = tk.Label(
            parent,
            text=display_name,
            anchor="w",
            font=FONTS["small"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["black"],
        )
        label.grid(row=row_idx, column=0, sticky="w", padx=(26, 10), pady=2)

        widget: Any = None
        param_type = param_info["type"]

        if param_type == "float":
            var = tk.DoubleVar(value=param_info["default"])
            widget = ttk.Spinbox(
                parent,
                from_=param_info.get("min", 0.0),
                to=param_info.get("max", 1.0),
                increment=0.01,
                textvariable=var,
                width=8,
                command=self.on_change,
            )
            widget.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var

        elif param_type == "int":
            var_int = tk.IntVar(value=param_info["default"])
            widget = ttk.Spinbox(
                parent,
                from_=param_info.get("min", 0),
                to=param_info.get("max", 100),
                increment=1,
                textvariable=var_int,
                width=8,
                command=self.on_change,
            )
            widget.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_int

        elif param_type == "choice":
            var_str = tk.StringVar(value=param_info["default"])
            widget = ttk.Combobox(
                parent,
                textvariable=var_str,
                values=param_info["choices"],
                width=14,
                state="readonly",
            )
            widget.bind("<<ComboboxSelected>>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_str

        elif param_type == "bool":
            var_bool = tk.BooleanVar(value=param_info["default"])
            widget = ttk.Checkbutton(parent, variable=var_bool, command=self.on_change)
            self.param_widgets[glitchling_name][param_name] = var_bool

        elif param_type == "text":
            var_text = tk.StringVar(value=param_info["default"])
            widget = ttk.Entry(parent, textvariable=var_text, width=14)
            widget.bind("<Return>", lambda e: self.on_change())
            self.param_widgets[glitchling_name][param_name] = var_text

        if widget:
            widget.grid(row=row_idx, column=1, sticky="w", padx=4, pady=2)

    def _update_count(self) -> None:
        """Update the count of active glitchlings."""
        count = sum(1 for v in self.enabled.values() if v.get())
        self.count_var.set(f"{count} active")

    def _toggle_expand(self, name: str) -> None:
        self.expanded[name] = not self.expanded[name]
        frame = self.frames[name]

        if frame.expand_btn is None or frame.param_frame is None:
            return

        if self.expanded[name]:
            frame.expand_btn.config(text="▾", fg=COLORS["cyan"])
            frame.param_frame.pack(fill=tk.X, after=frame.winfo_children()[0])
        else:
            frame.expand_btn.config(text="▸", fg=COLORS["green_muted"])
            frame.param_frame.pack_forget()

    def get_enabled_glitchlings(self) -> List[Tuple[type[Any], Dict[str, Any]]]:
        """Return list of (class, params) for enabled glitchlings."""
        result: List[Tuple[type[Any], Dict[str, Any]]] = []
        for cls in AVAILABLE_GLITCHLINGS:
            name = cls.__name__
            if self.enabled[name].get():
                params: Dict[str, Any] = {}
                for param_name, var in self.param_widgets[name].items():
                    val = var.get()
                    # Special handling for Mim1c classes
                    if name == "Mim1c" and param_name == "classes" and not val:
                        val = None
                    params[param_name] = val
                result.append((cls, params))
        return result
