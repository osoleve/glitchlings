"""Charts panel for visualization.

Provides ASCII-style charts that work without external dependencies,
with optional matplotlib integration for higher quality charts.
"""

from __future__ import annotations

import statistics
import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any, Callable, Dict, List

from ..model import ScanResult
from ..theme import COLORS, FONTS


class ChartsPanel(ttk.Frame):
    """Panel for visualizing metrics and distributions."""

    def __init__(
        self,
        parent: ttk.Frame,
        get_scan_results: Callable[[], Dict[str, ScanResult]],
        get_sweep_results: Callable[[], List[Any]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.get_scan_results = get_scan_results
        self.get_sweep_results = get_sweep_results

        # Variables
        self.chart_type_var = tk.StringVar(value="histogram")
        self.metric_var = tk.StringVar(value="jsd")
        self.tokenizer_var = tk.StringVar()

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["dark"], padx=1, pady=1)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))

        tk.Label(
            header_frame,
            text="▓▒░ VISUALIZATION ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["dark"],
            padx=8,
            pady=5,
        ).pack(side=tk.LEFT)

        # Main content
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        content = tk.Frame(content_container, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Controls row
        controls = tk.Frame(content, bg=COLORS["black"])
        controls.pack(fill=tk.X, padx=8, pady=8)

        # Chart type
        tk.Label(
            controls,
            text="Chart:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        chart_combo = ttk.Combobox(
            controls,
            textvariable=self.chart_type_var,
            values=["histogram", "boxplot", "line"],
            width=12,
            state="readonly",
        )
        chart_combo.pack(side=tk.LEFT, padx=(8, 20))
        chart_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Metric
        tk.Label(
            controls,
            text="Metric:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        metric_combo = ttk.Combobox(
            controls,
            textvariable=self.metric_var,
            values=["jsd", "ned", "sr", "token_delta"],
            width=12,
            state="readonly",
        )
        metric_combo.pack(side=tk.LEFT, padx=(8, 20))
        metric_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Tokenizer
        tk.Label(
            controls,
            text="Tokenizer:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        self.tokenizer_combo = ttk.Combobox(
            controls,
            textvariable=self.tokenizer_var,
            values=[],
            width=18,
            state="readonly",
        )
        self.tokenizer_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.tokenizer_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Refresh button
        refresh_btn = tk.Button(
            controls,
            text="↻ Refresh",
            font=FONTS["small"],
            fg=COLORS["green"],
            bg=COLORS["dark"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["highlight"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._update_chart,
        )
        refresh_btn.pack(side=tk.RIGHT)

        # Chart display area (ASCII art for now)
        chart_header = tk.Frame(content, bg=COLORS["dark"])
        chart_header.pack(fill=tk.X, padx=8, pady=(8, 0))

        tk.Label(
            chart_header,
            text="░ CHART",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["dark"],
            padx=4,
        ).pack(side=tk.LEFT)

        self.chart_title = tk.Label(
            chart_header,
            text="",
            font=FONTS["tiny"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=4,
        )
        self.chart_title.pack(side=tk.RIGHT)

        chart_container = tk.Frame(content, bg=COLORS["border"], padx=1, pady=1)
        chart_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.chart_text = scrolledtext.ScrolledText(
            chart_container,
            wrap=tk.NONE,
            height=20,
            font=("Consolas", 9),
            fg=COLORS["green"],
            bg=COLORS["darker"],
            relief=tk.FLAT,
            padx=12,
            pady=8,
            state=tk.DISABLED,
        )
        self.chart_text.pack(fill=tk.BOTH, expand=True)

        # Configure tags for chart colors
        self.chart_text.tag_configure("bar", foreground=COLORS["cyan"])
        self.chart_text.tag_configure("axis", foreground=COLORS["green_dim"])
        self.chart_text.tag_configure("label", foreground=COLORS["amber"])
        self.chart_text.tag_configure("title", foreground=COLORS["green_bright"])

        # Stats panel
        stats_frame = tk.Frame(content, bg=COLORS["dark"])
        stats_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.stats_label = tk.Label(
            stats_frame,
            text="No data available · Run a scan to generate charts",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["dark"],
            padx=8,
            pady=6,
        )
        self.stats_label.pack(fill=tk.X)

    def _update_chart(self) -> None:
        """Update the chart display."""
        scan_results = self.get_scan_results()

        if not scan_results:
            self._show_no_data()
            return

        # Update tokenizer dropdown
        tokenizers = list(scan_results.keys())
        self.tokenizer_combo["values"] = tokenizers
        if not self.tokenizer_var.get() or self.tokenizer_var.get() not in tokenizers:
            self.tokenizer_var.set(tokenizers[0] if tokenizers else "")

        tok_name = self.tokenizer_var.get()
        if not tok_name or tok_name not in scan_results:
            self._show_no_data()
            return

        metric = self.metric_var.get()
        chart_type = self.chart_type_var.get()

        scan_result = scan_results[tok_name]
        values = getattr(scan_result, metric, [])

        if not values:
            self._show_no_data()
            return

        # Update title
        self.chart_title.config(text=f"{metric.upper()} · {tok_name}")

        # Generate chart based on type
        if chart_type == "histogram":
            self._draw_histogram(values, metric)
        elif chart_type == "boxplot":
            self._draw_boxplot(values, metric)
        elif chart_type == "line":
            self._draw_line(values, metric)

        # Update stats
        self._update_stats(values, metric)

    def _show_no_data(self) -> None:
        """Display no data message."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)
        self.chart_text.insert(
            tk.END,
            "\n\n       No scan data available.\n\n"
            "       Enable Scan mode and run a scan to generate charts.\n\n"
            "       Charts will show distributions of metrics across seeds.",
        )
        self.chart_text.config(state=tk.DISABLED)
        self.stats_label.config(text="No data available · Run a scan to generate charts")
        self.chart_title.config(text="")

    def _draw_histogram(self, values: List[float], metric: str) -> None:
        """Draw an ASCII histogram."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)

        if not values:
            self.chart_text.config(state=tk.DISABLED)
            return

        # Calculate histogram bins
        min_val = min(values)
        max_val = max(values)

        # Handle edge case where all values are the same
        if min_val == max_val:
            max_val = min_val + 0.1

        num_bins = 10
        bin_width = (max_val - min_val) / num_bins
        bins = [0] * num_bins

        for v in values:
            bin_idx = int((v - min_val) / bin_width)
            bin_idx = min(bin_idx, num_bins - 1)  # Handle edge case
            bins[bin_idx] += 1

        max_count = max(bins) if bins else 1
        chart_width = 50

        # Title
        self.chart_text.insert(tk.END, f"\n  {metric.upper()} Distribution\n", "title")
        self.chart_text.insert(tk.END, f"  n={len(values)}\n\n", "axis")

        # Draw bars
        for i, count in enumerate(bins):
            bar_len = int((count / max_count) * chart_width) if max_count > 0 else 0
            bin_start = min_val + i * bin_width

            label = f"  {bin_start:6.3f} │"
            self.chart_text.insert(tk.END, label, "label")
            self.chart_text.insert(tk.END, "█" * bar_len, "bar")
            self.chart_text.insert(tk.END, f" {count}\n", "axis")

        # X-axis
        self.chart_text.insert(tk.END, f"  {'─' * 8}┴{'─' * chart_width}\n", "axis")
        self.chart_text.insert(tk.END, f"         └{'─' * chart_width}→ count\n", "axis")

        self.chart_text.config(state=tk.DISABLED)

    def _draw_boxplot(self, values: List[float], metric: str) -> None:
        """Draw an ASCII boxplot."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)

        if not values:
            self.chart_text.config(state=tk.DISABLED)
            return

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]
        median = statistics.median(sorted_vals)
        q1 = sorted_vals[n // 4] if n >= 4 else min_val
        q3 = sorted_vals[3 * n // 4] if n >= 4 else max_val
        mean = statistics.mean(values)

        chart_width = 60

        # Normalize positions
        range_val = max_val - min_val if max_val != min_val else 1

        def pos(v: float) -> int:
            return int(((v - min_val) / range_val) * (chart_width - 1))

        # Title
        self.chart_text.insert(tk.END, f"\n  {metric.upper()} Boxplot\n", "title")
        self.chart_text.insert(tk.END, f"  n={len(values)}\n\n", "axis")

        # Build boxplot line
        line = [" "] * chart_width
        line[pos(min_val)] = "├"
        line[pos(max_val)] = "┤"
        line[pos(q1)] = "┌"
        line[pos(q3)] = "┐"
        line[pos(median)] = "│"

        # Fill whiskers
        for i in range(pos(min_val) + 1, pos(q1)):
            line[i] = "─"
        for i in range(pos(q3) + 1, pos(max_val)):
            line[i] = "─"

        # Fill box
        for i in range(pos(q1) + 1, pos(q3)):
            if i != pos(median):
                line[i] = "█"
            else:
                line[i] = "┃"

        self.chart_text.insert(tk.END, "  ", "axis")
        self.chart_text.insert(tk.END, "".join(line) + "\n", "bar")

        # Labels
        self.chart_text.insert(tk.END, "\n", "axis")
        self.chart_text.insert(tk.END, f"  Min:    {min_val:.4f}\n", "label")
        self.chart_text.insert(tk.END, f"  Q1:     {q1:.4f}\n", "label")
        self.chart_text.insert(tk.END, f"  Median: {median:.4f}\n", "label")
        self.chart_text.insert(tk.END, f"  Q3:     {q3:.4f}\n", "label")
        self.chart_text.insert(tk.END, f"  Max:    {max_val:.4f}\n", "label")
        self.chart_text.insert(tk.END, f"\n  Mean:   {mean:.4f}\n", "title")

        self.chart_text.config(state=tk.DISABLED)

    def _draw_line(self, values: List[float], metric: str) -> None:
        """Draw an ASCII line chart showing values over seed index."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)

        if not values:
            self.chart_text.config(state=tk.DISABLED)
            return

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        chart_height = 15
        chart_width = min(60, len(values))

        # Sample values if too many
        if len(values) > chart_width:
            step = len(values) / chart_width
            sampled = [values[int(i * step)] for i in range(chart_width)]
        else:
            sampled = values

        # Title
        self.chart_text.insert(tk.END, f"\n  {metric.upper()} over Seeds\n", "title")
        self.chart_text.insert(tk.END, f"  n={len(values)}\n\n", "axis")

        # Create grid
        grid = [[" "] * (len(sampled) + 8) for _ in range(chart_height)]

        # Plot points
        for x, v in enumerate(sampled):
            y = int(((v - min_val) / range_val) * (chart_height - 1))
            y = chart_height - 1 - y  # Flip Y axis
            if 0 <= y < chart_height:
                grid[y][x + 8] = "●"

        # Add Y axis labels
        for i in range(chart_height):
            val = max_val - (i / (chart_height - 1)) * range_val
            label = f"{val:6.3f} │"
            for j, c in enumerate(label):
                grid[i][j] = c

        # Draw grid
        for row in grid:
            self.chart_text.insert(tk.END, "  ", "axis")
            for c in row:
                if c == "●":
                    self.chart_text.insert(tk.END, c, "bar")
                elif c in "│─":
                    self.chart_text.insert(tk.END, c, "axis")
                else:
                    self.chart_text.insert(tk.END, c, "label")
            self.chart_text.insert(tk.END, "\n")

        # X axis
        self.chart_text.insert(tk.END, f"  {'─' * 8}┴{'─' * len(sampled)}→ seed\n", "axis")

        self.chart_text.config(state=tk.DISABLED)

    def _update_stats(self, values: List[float], metric: str) -> None:
        """Update statistics display."""
        if not values:
            self.stats_label.config(text="No data")
            return

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        max_val = max(values)

        stats_text = (
            f"{metric.upper()}: mean={mean:.4f} ± {std:.4f}  "
            f"│  min={min_val:.4f}  max={max_val:.4f}  "
            f"│  n={len(values)}"
        )
        self.stats_label.config(text=stats_text)

    def refresh(self) -> None:
        """Refresh the chart with current data."""
        self._update_chart()
