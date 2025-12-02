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
    """Panel for visualizing metrics and distributions in a grid layout."""

    def __init__(
        self,
        parent: ttk.Frame,
        get_scan_results: Callable[[], Dict[str, ScanResult]],
        get_sweep_results: Callable[[], List[SweepPoint]] | None = None,
        get_dataset_results: Callable[[], Dict[str, ScanResult]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.get_scan_results = get_scan_results
        self.get_sweep_results = get_sweep_results
        self.get_dataset_results = get_dataset_results

        # Variables
        self.source_var = tk.StringVar(value="scan")
        self.metric_var = tk.StringVar(value="jsd")
        self.tokenizer_var = tk.StringVar()

        # Chart text widgets for grid display
        self.chart_texts: Dict[str, scrolledtext.ScrolledText] = {}
        self.chart_titles: Dict[str, tk.Label] = {}

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Header
        header_frame = tk.Frame(self, bg=COLORS["surface"], height=36)
        header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="▓▒░ VISUALIZATION ░▒▓",
            font=FONTS["section"],
            fg=COLORS["cyan"],
            bg=COLORS["surface"],
            padx=10,
        ).pack(side=tk.LEFT, pady=8)

        # Main content
        content_container = tk.Frame(self, bg=COLORS["border"], padx=1, pady=1)
        content_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        content = tk.Frame(content_container, bg=COLORS["black"])
        content.pack(fill=tk.BOTH, expand=True)

        # Controls row
        controls = tk.Frame(content, bg=COLORS["black"])
        controls.pack(fill=tk.X, padx=10, pady=10)

        # Data source
        tk.Label(
            controls,
            text="Source:",
            font=FONTS["small"],
            fg=COLORS["text_muted"],
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
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self._update_charts())

        # Metric
        tk.Label(
            controls,
            text="Metric:",
            font=FONTS["small"],
            fg=COLORS["text_muted"],
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
        self.metric_combo.bind("<<ComboboxSelected>>", lambda e: self._update_charts())

        # Tokenizer
        tk.Label(
            controls,
            text="Tokenizer:",
            font=FONTS["small"],
            fg=COLORS["text_muted"],
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
        self.tokenizer_combo.bind("<<ComboboxSelected>>", lambda e: self._update_charts())

        # Refresh button
        refresh_btn = tk.Button(
            controls,
            text="↻ Refresh",
            font=FONTS["tiny"],
            fg=COLORS["text_muted"],
            bg=COLORS["surface"],
            activeforeground=COLORS["green_bright"],
            activebackground=COLORS["surface"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._update_charts,
            padx=8,
            pady=2,
        )
        refresh_btn.pack(side=tk.RIGHT)

        # Charts grid container (2x2 grid: histogram, boxplot, line, stats)
        charts_frame = tk.Frame(content, bg=COLORS["black"])
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        # Configure 2x2 grid
        charts_frame.grid_rowconfigure(0, weight=1)
        charts_frame.grid_rowconfigure(1, weight=1)
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        # Create chart panels for each type
        chart_types = [
            ("histogram", "HISTOGRAM", 0, 0),
            ("boxplot", "BOXPLOT", 0, 1),
            ("line", "LINE CHART", 1, 0),
        ]

        for chart_type, title, row, col in chart_types:
            self._create_chart_cell(charts_frame, chart_type, title, row, col)

        # Stats panel in bottom-right (row=1, col=1)
        stats_outer = tk.Frame(charts_frame, bg=COLORS["border_subtle"], padx=1, pady=1)
        stats_outer.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)

        stats_inner = tk.Frame(stats_outer, bg=COLORS["black"])
        stats_inner.pack(fill=tk.BOTH, expand=True)

        stats_header = tk.Frame(stats_inner, bg=COLORS["surface"], height=24)
        stats_header.pack(fill=tk.X)
        stats_header.pack_propagate(False)

        tk.Label(
            stats_header,
            text="▁ STATISTICS",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["surface"],
            padx=6,
        ).pack(side=tk.LEFT, pady=4)

        stats_content = tk.Frame(stats_inner, bg=COLORS["darker"])
        stats_content.pack(fill=tk.BOTH, expand=True)

        self.stats_label = tk.Label(
            stats_content,
            text="No data available\n\nRun a sweep to generate charts",
            font=FONTS["small"],
            fg=COLORS["text_muted"],
            bg=COLORS["darker"],
            padx=14,
            pady=14,
            justify=tk.LEFT,
            anchor="nw",
        )
        self.stats_label.pack(fill=tk.BOTH, expand=True)

    def _create_chart_cell(
        self, parent: tk.Frame, chart_type: str, title: str, row: int, col: int
    ) -> None:
        """Create a single chart cell in the grid."""
        # Outer border frame
        outer = tk.Frame(parent, bg=COLORS["border_subtle"], padx=1, pady=1)
        outer.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)

        inner = tk.Frame(outer, bg=COLORS["black"])
        inner.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(inner, bg=COLORS["surface"], height=24)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"▁ {title}",
            font=FONTS["tiny"],
            fg=COLORS["cyan_dim"],
            bg=COLORS["surface"],
            padx=6,
        ).pack(side=tk.LEFT, pady=4)

        title_label = tk.Label(
            header,
            text="",
            font=FONTS["tiny"],
            fg=COLORS["text_muted"],
            bg=COLORS["surface"],
            padx=6,
        )
        title_label.pack(side=tk.RIGHT, pady=4)
        self.chart_titles[chart_type] = title_label

        # Chart text area
        chart_container = tk.Frame(inner, bg=COLORS["darker"])
        chart_container.pack(fill=tk.BOTH, expand=True)

        chart_text = scrolledtext.ScrolledText(
            chart_container,
            wrap=tk.NONE,
            height=8,
            font=("Consolas", 8),
            fg=COLORS["green"],
            bg=COLORS["darker"],
            relief=tk.FLAT,
            padx=8,
            pady=6,
            state=tk.DISABLED,
        )
        chart_text.pack(fill=tk.BOTH, expand=True)

        # Configure tags for chart colors
        chart_text.tag_configure("bar", foreground=COLORS["cyan"])
        chart_text.tag_configure("axis", foreground=COLORS["green_dim"])
        chart_text.tag_configure("label", foreground=COLORS["amber"])
        chart_text.tag_configure("title", foreground=COLORS["green_bright"])

        self.chart_texts[chart_type] = chart_text

    def _update_charts(self) -> None:
        """Update all charts in the grid."""
        scan_results = self.get_scan_results()
        sweep_results = self.get_sweep_results() if self.get_sweep_results else []
        dataset_results = self.get_dataset_results() if self.get_dataset_results else {}

        sources: List[str] = []
        if scan_results:
            sources.append("scan")
        if sweep_results:
            sources.append("sweep")
        if dataset_results:
            sources.append("dataset")

        self.source_combo["values"] = sources
        if not self.source_var.get() or self.source_var.get() not in sources:
            self.source_var.set(sources[0] if sources else "")

        if not sources:
            self._show_no_data()
            return

        source = self.source_var.get()

        # Update tokenizer dropdown based on source
        tokenizers = self._get_tokenizers_for_source(
            source, scan_results, sweep_results, dataset_results
        )
        self.tokenizer_combo["values"] = tokenizers
        if not self.tokenizer_var.get() or self.tokenizer_var.get() not in tokenizers:
            self.tokenizer_var.set(tokenizers[0] if tokenizers else "")

        tok_name = self.tokenizer_var.get()
        if not tok_name:
            self._show_no_data()
            return

        # Metric options depend on source
        metrics = self._get_metrics_for_source(
            source, tok_name, scan_results, sweep_results, dataset_results
        )
        self.metric_combo["values"] = metrics
        if not self.metric_var.get() or self.metric_var.get() not in metrics:
            self.metric_var.set(metrics[0] if metrics else "")

        metric = self.metric_var.get()
        data = self._build_chart_data(
            source, tok_name, metric, scan_results, sweep_results, dataset_results
        )

        if data is None:
            self._show_no_data()
            return

        # Update all chart titles
        title_suffix = f"{metric.upper()} · {tok_name}"
        for chart_type in self.chart_titles:
            self.chart_titles[chart_type].config(text=title_suffix)

        # Draw all charts
        self._draw_histogram(data.distribution_values, metric)
        self._draw_boxplot(data.distribution_values, metric)
        self._draw_line(
            data.trend_values,
            metric,
            x_label=data.x_label,
            x_values=data.x_values,
        )

        # Update stats
        stats_values = data.distribution_values or data.trend_values
        self._update_stats(stats_values, metric, data.source_label)

    # Keep old method name as alias for compatibility
    def _update_chart(self) -> None:
        """Alias for _update_charts for backward compatibility."""
        self._update_charts()

    def _get_tokenizers_for_source(
        self,
        source: str,
        scan_results: Dict[str, ScanResult],
        sweep_results: List[SweepPoint],
        dataset_results: Dict[str, ScanResult],
    ) -> List[str]:
        if source == "sweep":
            tokenizer_set: set[str] = set()
            for point in sweep_results:
                tokenizer_set.update(point.metrics.keys())
            return sorted(tokenizer_set)
        if source == "dataset":
            return list(dataset_results.keys())
        return list(scan_results.keys())

    def _get_metrics_for_source(
        self,
        source: str,
        tokenizer: str,
        scan_results: Dict[str, ScanResult],
        sweep_results: List[SweepPoint],
        dataset_results: Dict[str, ScanResult],
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
        results = dataset_results if source == "dataset" else scan_results
        for name in metrics:
            if any(getattr(result, name, []) for result in results.values()):
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
        dataset_results: Dict[str, ScanResult],
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

        result = (dataset_results if source == "dataset" else scan_results).get(tokenizer)
        if result is None:
            return None

        raw_values = getattr(result, metric, [])
        values = self._coerce_numeric(list(raw_values))
        if not values:
            return None

        x_label = "sample" if source == "dataset" else "seed"
        return ChartData(values, values, None, x_label, source)

    def _show_no_data(self) -> None:
        """Display no data message in all charts."""
        no_data_msg = "\n  No data available.\n\n  Run a sweep to\n  generate metrics."

        for chart_type, chart_text in self.chart_texts.items():
            chart_text.config(state=tk.NORMAL)
            chart_text.delete("1.0", tk.END)
            chart_text.insert(tk.END, no_data_msg)
            chart_text.config(state=tk.DISABLED)

        for title_label in self.chart_titles.values():
            title_label.config(text="")

        self.stats_label.config(text="No data available\n\nRun a sweep to generate charts")

    def _draw_histogram(self, values: List[float], metric: str) -> None:
        """Draw an ASCII histogram."""
        chart_text = self.chart_texts.get("histogram")
        if chart_text is None:
            return

        chart_text.config(state=tk.NORMAL)
        chart_text.delete("1.0", tk.END)

        if not values:
            chart_text.config(state=tk.DISABLED)
            return

        # Calculate histogram bins
        min_val = min(values)
        max_val = max(values)

        # Handle edge case where all values are the same
        if min_val == max_val:
            max_val = min_val + 0.1

        num_bins = 8  # Reduced for smaller grid cells
        bin_width = (max_val - min_val) / num_bins
        bins = [0] * num_bins

        for v in values:
            bin_idx = int((v - min_val) / bin_width)
            bin_idx = min(bin_idx, num_bins - 1)  # Handle edge case
            bins[bin_idx] += 1

        max_count = max(bins) if bins else 1
        chart_width = 30  # Reduced for grid layout

        # Title
        chart_text.insert(tk.END, f" {metric.upper()} n={len(values)}\n\n", "title")

        # Draw bars
        for i, count in enumerate(bins):
            bar_len = int((count / max_count) * chart_width) if max_count > 0 else 0
            bin_start = min_val + i * bin_width

            label = f" {bin_start:5.2f}│"
            chart_text.insert(tk.END, label, "label")
            chart_text.insert(tk.END, "█" * bar_len, "bar")
            chart_text.insert(tk.END, f" {count}\n", "axis")

        # X-axis
        chart_text.insert(tk.END, f" {'─' * 6}┴{'─' * chart_width}→\n", "axis")

        chart_text.config(state=tk.DISABLED)

    def _draw_boxplot(self, values: List[float], metric: str) -> None:
        """Draw an ASCII boxplot."""
        chart_text = self.chart_texts.get("boxplot")
        if chart_text is None:
            return

        chart_text.config(state=tk.NORMAL)
        chart_text.delete("1.0", tk.END)

        if not values:
            chart_text.config(state=tk.DISABLED)
            return

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]
        median = statistics.median(sorted_vals)
        q1 = sorted_vals[n // 4] if n >= 4 else min_val
        q3 = sorted_vals[3 * n // 4] if n >= 4 else max_val
        mean = statistics.mean(values)

        chart_width = 40  # Reduced for grid layout

        # Normalize positions
        range_val = max_val - min_val if max_val != min_val else 1

        def pos(v: float) -> int:
            return int(((v - min_val) / range_val) * (chart_width - 1))

        # Title
        chart_text.insert(tk.END, f" {metric.upper()} n={len(values)}\n\n", "title")

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

        chart_text.insert(tk.END, " ", "axis")
        chart_text.insert(tk.END, "".join(line) + "\n", "bar")

        # Compact labels (two columns)
        chart_text.insert(tk.END, "\n", "axis")
        chart_text.insert(tk.END, f" Min:{min_val:7.3f}  Q1:{q1:7.3f}\n", "label")
        chart_text.insert(tk.END, f" Med:{median:7.3f}  Q3:{q3:7.3f}\n", "label")
        chart_text.insert(tk.END, f" Max:{max_val:7.3f}  μ:{mean:8.3f}\n", "label")

        chart_text.config(state=tk.DISABLED)

    def _draw_line(
        self,
        values: List[float],
        metric: str,
        *,
        x_label: str = "seed",
        x_values: List[float] | None = None,
    ) -> None:
        """Draw an ASCII line chart showing values over an index or parameter grid."""
        chart_text = self.chart_texts.get("line")
        if chart_text is None:
            return

        chart_text.config(state=tk.NORMAL)
        chart_text.delete("1.0", tk.END)

        if not values:
            chart_text.config(state=tk.DISABLED)
            return

        x_points = (
            list(x_values)
            if x_values is not None and len(x_values) == len(values)
            else list(range(len(values)))
        )

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        chart_height = 8  # Reduced for grid layout
        chart_width = min(35, len(values))  # Reduced for grid layout

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
        chart_text.insert(tk.END, f" {metric.upper()} vs {x_title}\n\n", "title")

        # Create grid
        grid = [[" "] * (len(sampled) + 7) for _ in range(chart_height)]

        # Plot points
        for x, v in enumerate(sampled):
            y = int(((v - min_val) / range_val) * (chart_height - 1))
            y = chart_height - 1 - y  # Flip Y axis
            if 0 <= y < chart_height:
                grid[y][x + 7] = "●"

        # Add Y axis labels
        for i in range(chart_height):
            val = max_val - (i / (chart_height - 1)) * range_val
            label = f"{val:5.2f}│"
            for j, c in enumerate(label):
                grid[i][j] = c

        # Draw grid
        for row in grid:
            chart_text.insert(tk.END, " ", "axis")
            for c in row:
                if c == "●":
                    chart_text.insert(tk.END, c, "bar")
                elif c in "│─":
                    chart_text.insert(tk.END, c, "axis")
                else:
                    chart_text.insert(tk.END, c, "label")
            chart_text.insert(tk.END, "\n")

        # X axis
        chart_text.insert(tk.END, f" {'─' * 6}┴{'─' * len(sampled)}→\n", "axis")
        if sampled_x:
            start_val, end_val = sampled_x[0], sampled_x[-1]
            try:
                chart_text.insert(
                    tk.END,
                    f" [{start_val:.2f} → {end_val:.2f}]\n",
                    "axis",
                )
            except Exception:
                pass

        chart_text.config(state=tk.DISABLED)

    def _update_stats(
        self, values: List[float], metric: str, source_label: str | None = None
    ) -> None:
        """Update statistics display."""
        if not values:
            self.stats_label.config(text="No data available")
            return

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        max_val = max(values)
        median = statistics.median(values)

        # Multi-line format for the stats panel
        stats_lines = [
            f"{metric.upper()} Statistics",
            "─────────────────────",
            f"Mean:   {mean:.4f} ± {std:.4f}",
            f"Median: {median:.4f}",
            f"Min:    {min_val:.4f}",
            f"Max:    {max_val:.4f}",
            f"Range:  {max_val - min_val:.4f}",
            f"Count:  {len(values)}",
        ]
        if source_label:
            stats_lines.append(f"Source: {source_label}")

        self.stats_label.config(text="\n".join(stats_lines))

    def refresh(self) -> None:
        """Refresh all charts with current data."""
        self._update_charts()
