"""Grid sweep panel for parameter exploration.

Allows sweeping over glitchling parameters to analyze metric sensitivity.
"""

from __future__ import annotations

import statistics
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import Callable, Dict, List

from glitchlings.zoo import Gaggle

from ..service import GlitchlingService
from ..theme import AVAILABLE_GLITCHLINGS, COLORS, FONTS, GLITCHLING_PARAMS


@dataclass
class SweepPoint:
    """Results for a single sweep point."""

    param_value: float
    metrics: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    glitchling_name: str = ""
    parameter_name: str = ""


@dataclass
class SweepConfig:
    """Configuration for a parameter sweep."""

    glitchling_name: str
    parameter_name: str
    start: float
    end: float
    step: float
    seeds_per_point: int = 10


class GridSweepPanel(ttk.Frame):
    """Panel for running parameter sweeps.

    Can optionally place the results table in an external container
    (e.g., a notebook tab) by passing results_container.
    """

    def __init__(
        self,
        parent: ttk.Frame,
        service: GlitchlingService | None,
        get_input_text: Callable[[], str],
        get_tokenizers: Callable[[], List[str]],
        on_results_changed: Callable[[], None] | None = None,
        results_container: ttk.Frame | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.get_input_text = get_input_text
        self.get_tokenizers = get_tokenizers
        self.on_results_changed = on_results_changed
        self.results_container = results_container

        # State
        self.running = False
        self.results: List[SweepPoint] = []

        # Variables
        self.glitchling_var = tk.StringVar()
        self.param_var = tk.StringVar()
        self.start_var = tk.StringVar(value="0.0")
        self.end_var = tk.StringVar(value="1.0")
        self.step_var = tk.StringVar(value="0.1")
        self.seeds_var = tk.StringVar(value="10")

        self._create_widgets()
        self._on_glitchling_change()

    def _create_widgets(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        tk.Label(
            header_frame,
            text="▓▒░ PARAMETER SWEEP ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=8,
            pady=5,
        ).pack(side=tk.LEFT)

        # Main content - only expand if results are inline
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        if self.results_container is None:
            content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        else:
            content_container.pack(fill=tk.X, padx=2, pady=2)

        content = tk.Frame(content_container, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Configuration section
        config_frame = tk.Frame(content, bg=COLORS["black"])
        config_frame.pack(fill=tk.X, padx=8, pady=8)

        # Row 1: Glitchling and Parameter selection
        row1 = tk.Frame(config_frame, bg=COLORS["black"])
        row1.pack(fill=tk.X, pady=4)

        tk.Label(
            row1,
            text="Glitchling:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        glitchling_names = [cls.__name__ for cls in AVAILABLE_GLITCHLINGS]
        self.glitchling_combo = ttk.Combobox(
            row1,
            textvariable=self.glitchling_var,
            values=glitchling_names,
            width=15,
            state="readonly",
        )
        self.glitchling_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.glitchling_combo.bind("<<ComboboxSelected>>", lambda e: self._on_glitchling_change())
        if glitchling_names:
            self.glitchling_var.set(glitchling_names[0])

        tk.Label(
            row1,
            text="Parameter:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        self.param_combo = ttk.Combobox(
            row1,
            textvariable=self.param_var,
            values=[],
            width=18,
            state="readonly",
        )
        self.param_combo.pack(side=tk.LEFT, padx=(8, 0))

        # Row 2: Range configuration
        row2 = tk.Frame(config_frame, bg=COLORS["black"])
        row2.pack(fill=tk.X, pady=4)

        tk.Label(
            row2,
            text="Range:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        start_entry = tk.Entry(
            row2,
            textvariable=self.start_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        start_entry.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(
            row2,
            text="to",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT, padx=8)

        end_entry = tk.Entry(
            row2,
            textvariable=self.end_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        end_entry.pack(side=tk.LEFT)

        tk.Label(
            row2,
            text="step",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT, padx=(15, 0))

        step_entry = tk.Entry(
            row2,
            textvariable=self.step_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            insertbackground=COLORS["green_bright"],
            relief=tk.SOLID,
            bd=1,
        )
        step_entry.pack(side=tk.LEFT, padx=(8, 0))

        # Row 3: Seeds per point
        row3 = tk.Frame(config_frame, bg=COLORS["black"])
        row3.pack(fill=tk.X, pady=4)

        tk.Label(
            row3,
            text="Seeds per point:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        seeds_spin = tk.Spinbox(
            row3,
            from_=1,
            to=1000,
            textvariable=self.seeds_var,
            width=8,
            font=FONTS["mono"],
            fg=COLORS["amber"],
            bg=COLORS["darker"],
            buttonbackground=COLORS["dark"],
            relief=tk.SOLID,
            bd=1,
        )
        seeds_spin.pack(side=tk.LEFT, padx=(8, 0))

        # Run button
        self.run_btn = tk.Button(
            row3,
            text="▶ RUN SWEEP",
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
            command=self._run_sweep,
        )
        self.run_btn.pack(side=tk.RIGHT)

        # Progress bar
        self.progress_frame = tk.Frame(config_frame, bg=COLORS["black"])
        self.progress_frame.pack(fill=tk.X, pady=(8, 0))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        )
        self.progress_label.pack(anchor="w", pady=(2, 0))

        # Results section - place in external container if provided
        results_parent = self.results_container if self.results_container else content

        results_header = tk.Frame(results_parent, bg=COLORS["dark"])
        if self.results_container:
            results_header.pack(fill=tk.X, padx=2, pady=(2, 0))
        else:
            results_header.pack(fill=tk.X, padx=8, pady=(15, 0))

        tk.Label(
            results_header,
            text="░ SWEEP RESULTS",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=4,
        ).pack(side=tk.LEFT)

        # Results table
        table_container = tk.Frame(results_parent, bg=COLORS["border"], padx=1, pady=1)
        if self.results_container:
            table_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        else:
            table_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        table_inner = tk.Frame(table_container, bg=COLORS["darker"])
        table_inner.pack(fill=tk.BOTH, expand=True)

        # Create treeview for results
        columns = ("param", "jsd", "ned", "sr")
        self.results_tree = ttk.Treeview(
            table_inner,
            columns=columns,
            show="headings",
            height=10,
        )

        # Configure columns
        col_config = [
            ("param", "Parameter", 80),
            ("jsd", "JSD", 140),
            ("ned", "NED", 140),
            ("sr", "SR", 140),
        ]

        for col_id, heading, width in col_config:
            self.results_tree.heading(col_id, text=heading)
            self.results_tree.column(col_id, width=width, anchor="center")

        self.results_tree.column("param", anchor="w")

        results_scroll = ttk.Scrollbar(
            table_inner,
            orient=tk.VERTICAL,
            command=self.results_tree.yview,
        )
        self.results_tree.configure(yscrollcommand=results_scroll.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_glitchling_change(self) -> None:
        """Update parameter dropdown when glitchling changes."""
        glitchling_name = self.glitchling_var.get()
        params = GLITCHLING_PARAMS.get(glitchling_name, {})

        # Filter to numeric parameters only
        numeric_params = [
            name for name, info in params.items() if info.get("type") in ("float", "int")
        ]

        self.param_combo["values"] = numeric_params
        if numeric_params:
            self.param_var.set(numeric_params[0])
            # Set range based on parameter info
            param_info = params.get(numeric_params[0], {})
            self.start_var.set(str(param_info.get("min", 0.0)))
            self.end_var.set(str(param_info.get("max", 1.0)))

    def _run_sweep(self) -> None:
        """Start or cancel a parameter sweep."""
        if self.running:
            self.running = False
            return

        # Validate input
        input_text = self.get_input_text()
        if not input_text:
            return

        try:
            start = float(self.start_var.get())
            end = float(self.end_var.get())
            step = float(self.step_var.get())
            seeds = int(self.seeds_var.get())
        except ValueError:
            return

        if step <= 0 or start >= end:
            return

        glitchling_name = self.glitchling_var.get()
        param_name = self.param_var.get()
        tokenizers = self.get_tokenizers()

        if not glitchling_name or not param_name:
            return

        # Find glitchling class
        glitchling_cls = None
        for cls in AVAILABLE_GLITCHLINGS:
            if cls.__name__ == glitchling_name:
                glitchling_cls = cls
                break

        if not glitchling_cls:
            return

        self.running = True
        self.run_btn.config(text="■ CANCEL", bg=COLORS["red"])
        self.results = []
        self._notify_results_changed()

        # Clear results table
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Run in background thread
        thread = threading.Thread(
            target=self._sweep_worker,
            args=(
                input_text,
                glitchling_cls,
                param_name,
                start,
                end,
                step,
                seeds,
                tokenizers,
            ),
            daemon=True,
        )
        thread.start()

    def _sweep_worker(
        self,
        input_text: str,
        glitchling_cls: type,
        param_name: str,
        start: float,
        end: float,
        step: float,
        seeds: int,
        tokenizers: List[str],
    ) -> None:
        """Worker thread for running sweep."""
        # Calculate sweep points
        points: List[float] = []
        current = start
        while current <= end + 0.0001:  # Small epsilon for float comparison
            points.append(round(current, 4))
            current += step

        total = len(points) * seeds

        for i, param_value in enumerate(points):
            if not self.running:
                break

            point_metrics: Dict[str, Dict[str, List[float]]] = {}

            for seed_offset in range(seeds):
                if not self.running:
                    break

                seed = 42 + seed_offset

                # Create glitchling with this parameter value
                glitchling = glitchling_cls(seed=seed, **{param_name: param_value})
                gaggle = Gaggle([glitchling], seed=seed)
                output = str(gaggle.corrupt(input_text))

                # Calculate metrics for each tokenizer
                if self.service is None:
                    continue
                metrics = self.service.calculate_metrics(input_text, output, tokenizers)

                for tok_name, tok_metrics in metrics.items():
                    if tok_name not in point_metrics:
                        point_metrics[tok_name] = {"jsd": [], "ned": [], "sr": []}

                    for metric in ["jsd", "ned", "sr"]:
                        val = tok_metrics.get(metric, "-")
                        if val != "-":
                            try:
                                point_metrics[tok_name][metric].append(float(val))
                            except (ValueError, TypeError):
                                pass

                # Update progress
                progress = ((i * seeds + seed_offset + 1) / total) * 100
                self._schedule_progress_update(progress, i + 1, len(points), seed_offset + 1, seeds)

            # Store results for this point
            sweep_point = SweepPoint(
                param_value=param_value,
                metrics=point_metrics,
                glitchling_name=glitchling_cls.__name__,
                parameter_name=param_name,
            )
            self.results.append(sweep_point)

            # Update results table
            result_point = sweep_point
            self.after(0, lambda rp=result_point: self._add_result_row(rp))  # type: ignore[misc]

        self.after(0, self._on_sweep_complete)

    def _update_progress(
        self, percent: float, point: int, total_points: int, seed: int, total_seeds: int
    ) -> None:
        """Update progress bar."""
        self.progress_var.set(percent)
        self.progress_label.config(text=f"Point {point}/{total_points} · Seed {seed}/{total_seeds}")

    def _schedule_progress_update(
        self, progress: float, point: int, total_points: int, seed: int, total_seeds: int
    ) -> None:
        """Schedule a progress update on the main thread."""
        self.after(
            0,
            lambda: self._update_progress(progress, point, total_points, seed, total_seeds),
        )

    def _notify_results_changed(self) -> None:
        """Notify listeners that sweep results have changed."""
        if self.on_results_changed:
            self.on_results_changed()

    def _add_result_row(self, point: SweepPoint) -> None:
        """Add a row to the results table."""
        # Aggregate across tokenizers (use first tokenizer for now)
        if not point.metrics:
            return

        first_tok = next(iter(point.metrics.values()))

        def fmt(values: List[float]) -> str:
            if not values:
                return "-"
            mean = statistics.mean(values)
            if len(values) > 1:
                std = statistics.stdev(values)
                return f"{mean:.4f} ± {std:.4f}"
            return f"{mean:.4f}"

        jsd = fmt(first_tok.get("jsd", []))
        ned = fmt(first_tok.get("ned", []))
        sr = fmt(first_tok.get("sr", []))

        self.results_tree.insert(
            "",
            "end",
            values=(
                f"{point.param_value:.3f}",
                jsd,
                ned,
                sr,
            ),
        )
        self._notify_results_changed()

    def _on_sweep_complete(self) -> None:
        """Handle sweep completion."""
        self.running = False
        self.run_btn.config(text="▶ RUN SWEEP", bg=COLORS["green"])
        self.progress_label.config(text=f"Complete · {len(self.results)} points")
        self._notify_results_changed()

    def get_results(self) -> List[SweepPoint]:
        """Return current sweep results."""
        return self.results
