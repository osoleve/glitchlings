"""Charts panel for visualization.

Provides ASCII-style charts that work without external dependencies,
with optional matplotlib integration for higher quality charts.
"""

from __future__ import annotations

import statistics
import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any, Callable, Dict, List, NamedTuple

from ..model import ScanResult
from ..theme import COLORS, FONTS
from .grid_sweep_panel import SweepPoint


class ChartData(NamedTuple):
    """Container for chart series and metadata."""

    trend_values: List[float]
    distribution_values: List[float]
    x_values: List[float] | None
    x_label: str
    source_label: str


class ChartsPanel(ttk.Frame):
    """Panel for visualizing metrics and distributions."""

    def __init__(
        self,
        parent: ttk.Frame,
        get_scan_results: Callable[[], Dict[str, ScanResult]],
        get_sweep_results: Callable[[], List[SweepPoint]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.get_scan_results = get_scan_results
        self.get_sweep_results = get_sweep_results

        # Variables
        self.source_var = tk.StringVar(value="scan")
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

        # Data source
        tk.Label(
            controls,
            text="Source:",
            font=FONTS["small"],
            fg=COLORS["green_dim"],
            bg=COLORS["black"],
        ).pack(side=tk.LEFT)

        self.source_combo = ttk.Combobox(
            controls,
            textvariable=self.source_var,
            values=[],
            width=14,
            state="readonly",
        )
        self.source_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

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

        self.metric_combo = ttk.Combobox(
            controls,
            textvariable=self.metric_var,
            values=["jsd", "ned", "sr", "token_delta"],
            width=12,
            state="readonly",
        )
        self.metric_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.metric_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

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
            text="No data available · Run a scan or sweep to generate charts",
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
        sweep_results = self.get_sweep_results() if self.get_sweep_results else []

        sources: List[str] = []
        if scan_results:
            sources.append("scan")
        if sweep_results:
            sources.append("sweep")

        self.source_combo["values"] = sources
        if not self.source_var.get() or self.source_var.get() not in sources:
            self.source_var.set(sources[0] if sources else "")

        if not sources:
            self._show_no_data()
            return

        source = self.source_var.get()

        # Update tokenizer dropdown based on source
        tokenizers = self._get_tokenizers_for_source(source, scan_results, sweep_results)
        self.tokenizer_combo["values"] = tokenizers
        if not self.tokenizer_var.get() or self.tokenizer_var.get() not in tokenizers:
            self.tokenizer_var.set(tokenizers[0] if tokenizers else "")

        tok_name = self.tokenizer_var.get()
        if not tok_name:
            self._show_no_data()
            return

        # Metric options depend on source
        metrics = self._get_metrics_for_source(source, tok_name, scan_results, sweep_results)
        self.metric_combo["values"] = metrics
        if not self.metric_var.get() or self.metric_var.get() not in metrics:
            self.metric_var.set(metrics[0] if metrics else "")

        metric = self.metric_var.get()
        chart_type = self.chart_type_var.get()
        data = self._build_chart_data(source, tok_name, metric, scan_results, sweep_results)

        if data is None:
            self._show_no_data()
            return

        # Update title
        self.chart_title.config(text=f"{metric.upper()} · {tok_name} [{data.source_label}]")

        # Generate chart based on type
        if chart_type == "histogram":
            self._draw_histogram(data.distribution_values, metric)
        elif chart_type == "boxplot":
            self._draw_boxplot(data.distribution_values, metric)
        elif chart_type == "line":
            self._draw_line(
                data.trend_values,
                metric,
                x_label=data.x_label,
                x_values=data.x_values,
            )

        # Update stats
        stats_values = data.distribution_values or data.trend_values
        self._update_stats(stats_values, metric, data.source_label)

    def _get_tokenizers_for_source(
        self,
        source: str,
        scan_results: Dict[str, ScanResult],
        sweep_results: List[SweepPoint],
    ) -> List[str]:
        if source == "sweep":
            tokenizer_set: set[str] = set()
            for point in sweep_results:
                tokenizer_set.update(point.metrics.keys())
            return sorted(tokenizer_set)
        return list(scan_results.keys())

    def _get_metrics_for_source(
        self,
        source: str,
        tokenizer: str,
        scan_results: Dict[str, ScanResult],
        sweep_results: List[SweepPoint],
    ) -> List[str]:
        if source == "sweep":
            metric_set = set()
            for point in sweep_results:
                tok_metrics = point.metrics.get(tokenizer)
                if not tok_metrics:
                    continue
                for name, values in tok_metrics.items():
                    if values:
                        metric_set.add(name)
            metrics = sorted(metric_set)
            return metrics or ["jsd", "ned", "sr"]

        metrics = ["jsd", "ned", "sr", "token_delta", "token_count_out", "char_count_out"]
        available = []
        for name in metrics:
            if any(getattr(result, name, []) for result in scan_results.values()):
                available.append(name)
        return available or metrics

    def _coerce_numeric(self, values: List[Any]) -> List[float]:
        numbers: List[float] = []
        for value in values:
            try:
                numbers.append(float(value))
            except (TypeError, ValueError):
                continue
        return numbers

    def _build_chart_data(
        self,
        source: str,
        tokenizer: str,
        metric: str,
        scan_results: Dict[str, ScanResult],
        sweep_results: List[SweepPoint],
    ) -> ChartData | None:
        if source == "sweep":
            trend_values: List[float] = []
            distribution_values: List[float] = []
            x_values: List[float] = []
            for point in sweep_results:
                tok_metrics = point.metrics.get(tokenizer)
                if not tok_metrics:
                    continue
                metric_values = self._coerce_numeric(list(tok_metrics.get(metric, [])))
                if not metric_values:
                    continue
                distribution_values.extend(metric_values)
                trend_values.append(statistics.mean(metric_values))
                x_values.append(point.param_value)

            if not trend_values and not distribution_values:
                return None

            x_label = sweep_results[0].parameter_name or "param"
            return ChartData(
                trend_values or distribution_values,
                distribution_values or trend_values,
                x_values if trend_values else None,
                x_label,
                "sweep",
            )

        result = scan_results.get(tokenizer)
        if result is None:
            return None

        raw_values = getattr(result, metric, [])
        values = self._coerce_numeric(list(raw_values))
        if not values:
            return None

        return ChartData(values, values, None, "seed", "scan")

    def _show_no_data(self) -> None:
        """Display no data message."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)
        self.chart_text.insert(
            tk.END,
            "\n\n       No chart data available.\n\n"
            "       Run a scan or sweep to generate metrics.\n\n"
            "       Charts will render distributions or parameter trends when data arrives.",
        )
        self.chart_text.config(state=tk.DISABLED)
        self.stats_label.config(text="No data available · Run a scan or sweep to generate charts")
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

    def _draw_line(
        self,
        values: List[float],
        metric: str,
        *,
        x_label: str = "seed",
        x_values: List[float] | None = None,
    ) -> None:
        """Draw an ASCII line chart showing values over an index or parameter grid."""
        self.chart_text.config(state=tk.NORMAL)
        self.chart_text.delete("1.0", tk.END)

        if not values:
            self.chart_text.config(state=tk.DISABLED)
            return

        x_points = (
            list(x_values)
            if x_values is not None and len(x_values) == len(values)
            else list(range(len(values)))
        )

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        chart_height = 15
        chart_width = min(60, len(values))

        # Sample values if too many
        if len(values) > chart_width:
            step = len(values) / chart_width
            indices = [int(i * step) for i in range(chart_width)]
            sampled = [values[idx] for idx in indices]
            sampled_x = [x_points[idx] for idx in indices]
        else:
            sampled = values
            sampled_x = x_points

        # Title
        x_title = x_label.replace("_", " ").title() if x_label else "Index"
        self.chart_text.insert(tk.END, f"\n  {metric.upper()} over {x_title}s\n", "title")
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
        self.chart_text.insert(
            tk.END, f"  {'─' * 8}┴{'─' * len(sampled)}→ {x_label}\n", "axis"
        )
        if sampled_x:
            start_val, end_val = sampled_x[0], sampled_x[-1]
            try:
                self.chart_text.insert(
                    tk.END,
                    f"  start={start_val:.3f}  │  end={end_val:.3f}\n",
                    "axis",
                )
            except Exception:
                pass

        self.chart_text.config(state=tk.DISABLED)

    def _update_stats(
        self, values: List[float], metric: str, source_label: str | None = None
    ) -> None:
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
        if source_label:
            stats_text = f"{stats_text}  │  {source_label}"
        self.stats_label.config(text=stats_text)

    def refresh(self) -> None:
        """Refresh the chart with current data."""
        self._update_chart()
