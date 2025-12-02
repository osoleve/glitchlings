"""Charts panel for the Textual GUI.

Provides ASCII-style charts for metrics visualization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Label,
    Select,
    Static,
)

from .chart_renderers import (
    HISTOGRAM_BINS,
    HISTOGRAM_CHART_WIDTH,
    BOXPLOT_CHART_WIDTH,
    LINE_CHART_HEIGHT,
    LINE_CHART_MAX_WIDTH,
    HistogramRenderer,
    BoxPlotRenderer,
    LineChartRenderer,
    StatsRenderer,
)
from .state import ScanResult
from .sweep_panel import SweepPoint
from .theme import PALETTE, substitute_vars

_RAW_CSS = """
ChartsPanel {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

ChartsPanel .charts-content {
    height: 100%;
    padding: 0;
    overflow: hidden;
}

ChartsPanel .section-panel {
    background: var(--glitch-panel);
    border: solid var(--glitch-border);
    margin-bottom: 1;
}

ChartsPanel .section-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

ChartsPanel .section-title {
    color: var(--glitch-accent);
    text-style: bold;
    width: auto;
}

ChartsPanel .controls-row {
    height: 3;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

ChartsPanel .control-label {
    width: auto;
    margin-right: 1;
    color: var(--glitch-muted);
}

ChartsPanel Select {
    width: 18;
    margin-right: 1;
}

ChartsPanel .refresh-btn {
    width: auto;
    min-width: 8;
    dock: right;
    background: var(--glitch-surface);
    color: var(--glitch-muted);
    border: none;
}

ChartsPanel .refresh-btn:hover {
    color: var(--glitch-bright);
}

ChartsPanel .charts-grid {
    height: 1fr;
    min-height: 16;
    layout: grid;
    grid-size: 2 2;
    grid-gutter: 1;
    padding: 1;
    overflow: hidden;
}

ChartsPanel .chart-cell {
    height: 100%;
    min-height: 10;
    background: var(--glitch-bg);
    border: solid var(--glitch-border);
    overflow: hidden;
}

ChartsPanel .chart-header {
    height: 2;
    padding: 0 1;
    background: var(--glitch-surface);
    border-bottom: solid var(--glitch-border);
}

ChartsPanel .chart-title {
    color: var(--glitch-accent);
    text-style: bold;
}

ChartsPanel .chart-subtitle {
    color: var(--glitch-muted);
    dock: right;
}

ChartsPanel .chart-content {
    height: 1fr;
    padding: 0 1;
    overflow-y: auto;
    overflow-x: hidden;
}

ChartsPanel .chart-display {
    width: 100%;
}

ChartsPanel .stats-cell .chart-content {
    padding: 0 1;
}

ChartsPanel .no-data {
    color: var(--glitch-muted);
    text-align: center;
    padding: 1;
}
"""
CSS = substitute_vars(_RAW_CSS)


@dataclass
class ChartData:
    """Container for chart series and metadata."""

    trend_values: list[float]
    distribution_values: list[float]
    x_values: list[float] | None
    x_label: str
    source_label: str


class ChartsPanel(Container):  # type: ignore[misc]
    """Panel for visualizing metrics and distributions."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
    ]

    DEFAULT_CSS = CSS

    class DataRequested(Message):  # type: ignore[misc]
        """Request chart data from the application."""

        pass

    class DataUpdated(Message):  # type: ignore[misc]
        """Notify that chart data has been updated."""

        def __init__(
            self,
            scan_results: dict[str, ScanResult] | None = None,
            sweep_results: list[SweepPoint] | None = None,
            dataset_results: dict[str, ScanResult] | None = None,
        ) -> None:
            super().__init__()
            self.scan_results = scan_results or {}
            self.sweep_results = sweep_results or []
            self.dataset_results = dataset_results or {}

    def __init__(
        self,
        get_scan_results: Callable[[], dict[str, ScanResult]] | None = None,
        get_sweep_results: Callable[[], list[SweepPoint]] | None = None,
        get_dataset_results: Callable[[], dict[str, ScanResult]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._get_scan_results = get_scan_results
        self._get_sweep_results = get_sweep_results
        self._get_dataset_results = get_dataset_results

        self._source = "sweep"
        self._metric = "jsd"
        self._tokenizer = ""
        self._updating = False  # Prevent recursive updates

        # Chart display widgets
        self._histogram_display: Static | None = None
        self._boxplot_display: Static | None = None
        self._line_display: Static | None = None
        self._stats_display: Static | None = None

        # Subtitle labels
        self._histogram_subtitle: Label | None = None
        self._boxplot_subtitle: Label | None = None
        self._line_subtitle: Label | None = None
        self._stats_subtitle: Label | None = None

        # Select widgets
        self._source_select: Select[str] | None = None
        self._metric_select: Select[str] | None = None
        self._tokenizer_select: Select[str] | None = None

        # Chart renderers
        self._histogram_renderer = HistogramRenderer()
        self._boxplot_renderer = BoxPlotRenderer()
        self._line_renderer = LineChartRenderer()
        self._stats_renderer = StatsRenderer()

    def compose(self) -> ComposeResult:
        with Vertical(classes="charts-content"):
            # Controls row
            with Horizontal(classes="controls-row"):
                yield Label("Source:", classes="control-label")
                yield Select(
                    [],
                    id="source-select",
                    allow_blank=False,
                )
                yield Label("Metric:", classes="control-label")
                yield Select(
                    [
                        ("JSD", "jsd"),
                        ("NED", "ned"),
                        ("SR", "sr"),
                        ("Token Δ", "token_delta"),
                    ],
                    id="metric-select",
                    value="jsd",
                )
                yield Label("Tokenizer:", classes="control-label")
                yield Select(
                    [],
                    id="tokenizer-select",
                    allow_blank=True,
                )
                yield Button("↻ Refresh", id="refresh-btn", classes="refresh-btn")

            # Charts grid (2x2)
            with Container(classes="charts-grid"):
                # Histogram (top-left)
                with Container(classes="chart-cell", id="histogram-cell"):
                    with Horizontal(classes="chart-header"):
                        yield Label("▁ HISTOGRAM", classes="chart-title")
                        yield Label("", id="histogram-subtitle", classes="chart-subtitle")
                    with Vertical(classes="chart-content"):
                        yield Static("", id="histogram-display", classes="chart-display")

                # Boxplot (top-right)
                with Container(classes="chart-cell", id="boxplot-cell"):
                    with Horizontal(classes="chart-header"):
                        yield Label("▁ BOXPLOT", classes="chart-title")
                        yield Label("", id="boxplot-subtitle", classes="chart-subtitle")
                    with Vertical(classes="chart-content"):
                        yield Static("", id="boxplot-display", classes="chart-display")

                # Line chart (bottom-left)
                with Container(classes="chart-cell", id="line-cell"):
                    with Horizontal(classes="chart-header"):
                        yield Label("▁ LINE CHART", classes="chart-title")
                        yield Label("", id="line-subtitle", classes="chart-subtitle")
                    with Vertical(classes="chart-content"):
                        yield Static("", id="line-display", classes="chart-display")

                # Stats (bottom-right)
                with Container(classes="chart-cell stats-cell", id="stats-cell"):
                    with Horizontal(classes="chart-header"):
                        yield Label("▁ STATISTICS", classes="chart-title")
                        yield Label("", id="stats-subtitle", classes="chart-subtitle")
                    with Vertical(classes="chart-content"):
                        yield Static("", id="stats-display", classes="chart-display")

    def on_mount(self) -> None:
        """Initialize after mount."""
        # Get widget references
        self._source_select = self.query_one("#source-select", Select)
        self._metric_select = self.query_one("#metric-select", Select)
        self._tokenizer_select = self.query_one("#tokenizer-select", Select)

        self._histogram_display = self.query_one("#histogram-display", Static)
        self._boxplot_display = self.query_one("#boxplot-display", Static)
        self._line_display = self.query_one("#line-display", Static)
        self._stats_display = self.query_one("#stats-display", Static)

        self._histogram_subtitle = self.query_one("#histogram-subtitle", Label)
        self._boxplot_subtitle = self.query_one("#boxplot-subtitle", Label)
        self._line_subtitle = self.query_one("#line-subtitle", Label)
        self._stats_subtitle = self.query_one("#stats-subtitle", Label)

        # Initial update
        self._update_charts()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        # Skip if we're programmatically updating
        if self._updating:
            return

        select_id = event.select.id
        value = event.value

        # Skip if value is blank/None
        if value is None or value == Select.BLANK:
            return

        # Update internal state and redraw
        if select_id == "source-select":
            self._source = str(value)
            # When source changes, refresh dropdowns and redraw
            self._refresh_dropdowns_only()
        elif select_id == "metric-select":
            self._metric = str(value)
            self._draw_charts_only()
        elif select_id == "tokenizer-select":
            self._tokenizer = str(value)
            self._draw_charts_only()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            self._update_charts()

    def action_refresh(self) -> None:
        """Refresh charts."""
        self._update_charts()

    def update_data(
        self,
        scan_results: dict[str, ScanResult] | None = None,
        sweep_results: list[SweepPoint] | None = None,
        dataset_results: dict[str, ScanResult] | None = None,
    ) -> None:
        """Update chart data externally."""
        self._update_charts(
            scan_results=scan_results,
            sweep_results=sweep_results,
            dataset_results=dataset_results,
        )

    def _update_charts(
        self,
        scan_results: dict[str, ScanResult] | None = None,
        sweep_results: list[SweepPoint] | None = None,
        dataset_results: dict[str, ScanResult] | None = None,
    ) -> None:
        """Update all charts with current data."""
        # Prevent recursive updates from select change events
        self._updating = True
        try:
            # Get data from callbacks if not provided
            if scan_results is None:
                scan_results = self._get_scan_results() if self._get_scan_results else {}
            if sweep_results is None:
                sweep_results = self._get_sweep_results() if self._get_sweep_results else []
            if dataset_results is None:
                dataset_results = self._get_dataset_results() if self._get_dataset_results else {}

            # Update source dropdown
            if not self._update_source_dropdown(sweep_results, dataset_results):
                self._show_no_data()
                return

            # Update tokenizer dropdown
            if not self._update_tokenizer_dropdown(scan_results, sweep_results, dataset_results):
                self._show_no_data()
                return

            # Update metric dropdown
            self._update_metric_dropdown(scan_results, sweep_results, dataset_results)

            # Build and render charts
            data = self._build_chart_data(
                self._source,
                self._tokenizer,
                self._metric,
                scan_results,
                sweep_results,
                dataset_results,
            )

            if data is None:
                self._show_no_data()
                return

            self._render_charts(data)
        finally:
            self._updating = False

    def _refresh_dropdowns_only(self) -> None:
        """Refresh tokenizer and metric dropdowns for current source, then redraw charts."""
        scan_results = self._get_scan_results() if self._get_scan_results else {}
        sweep_results = self._get_sweep_results() if self._get_sweep_results else []
        dataset_results = self._get_dataset_results() if self._get_dataset_results else {}

        self._updating = True
        try:
            self._update_tokenizer_dropdown(scan_results, sweep_results, dataset_results)
            self._update_metric_dropdown(scan_results, sweep_results, dataset_results)

            # Build and render charts with current selections
            data = self._build_chart_data(
                self._source,
                self._tokenizer,
                self._metric,
                scan_results,
                sweep_results,
                dataset_results,
            )

            if data is None:
                self._show_no_data()
                return

            self._render_charts(data)
        finally:
            self._updating = False

    def _draw_charts_only(self) -> None:
        """Draw charts without updating dropdowns."""
        scan_results = self._get_scan_results() if self._get_scan_results else {}
        sweep_results = self._get_sweep_results() if self._get_sweep_results else []
        dataset_results = self._get_dataset_results() if self._get_dataset_results else {}

        data = self._build_chart_data(
            self._source,
            self._tokenizer,
            self._metric,
            scan_results,
            sweep_results,
            dataset_results,
        )

        if data is None:
            self._show_no_data()
            return

        self._render_charts(data)

    def _get_tokenizers_for_source(
        self,
        source: str,
        scan_results: dict[str, ScanResult],
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> list[str]:
        """Get available tokenizers for the selected source."""
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
        scan_results: dict[str, ScanResult],
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> list[str]:
        """Get available metrics for the selected source and tokenizer."""
        if source == "sweep":
            metric_set: set[str] = set()
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
            for result in results.values():
                # Handle both ScanResult objects and dict[str, str] from app metrics
                if isinstance(result, dict):
                    if result.get(name) is not None:
                        available.append(name)
                        break
                else:
                    if getattr(result, name, []):
                        available.append(name)
                        break
        return available or metrics

    def _coerce_numeric(self, values: list[Any]) -> list[float]:
        """Convert values to floats, skipping non-numeric."""
        numbers: list[float] = []
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
        scan_results: dict[str, ScanResult],
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> ChartData | None:
        """Build chart data from the selected source."""
        if source == "sweep":
            trend_values: list[float] = []
            distribution_values: list[float] = []
            x_values: list[float] = []
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

        # Handle both ScanResult objects and dict[str, str] from app metrics
        if isinstance(result, dict):
            # Scan results from app.metrics are dict[str, str] with single values
            raw_value = result.get(metric)
            if raw_value is None:
                return None
            try:
                values = [float(raw_value)]
            except (TypeError, ValueError):
                return None
        else:
            # ScanResult dataclass with list attributes
            raw_values = getattr(result, metric, [])
            values = self._coerce_numeric(list(raw_values))

        if not values:
            return None

        x_label = "sample" if source == "dataset" else "seed"
        return ChartData(values, values, None, x_label, source)

    def _update_source_dropdown(
        self,
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> bool:
        """Update source dropdown. Returns False if no sources available."""
        sources: list[tuple[str, str]] = []
        if sweep_results:
            sources.append(("Sweep", "sweep"))
        if dataset_results:
            sources.append(("Dataset", "dataset"))

        source_values = [s[1] for s in sources]

        if self._source_select:
            if self._source not in source_values:
                self._source = source_values[0] if source_values else "sweep"
            self._source_select.set_options(sources)
            if source_values:
                self._source_select.value = self._source

        return bool(sources)

    def _update_tokenizer_dropdown(
        self,
        scan_results: dict[str, ScanResult],
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> bool:
        """Update tokenizer dropdown. Returns False if no tokenizers available."""
        tokenizers = self._get_tokenizers_for_source(
            self._source, scan_results, sweep_results, dataset_results
        )

        if self._tokenizer_select:
            if self._tokenizer not in tokenizers:
                self._tokenizer = tokenizers[0] if tokenizers else ""
            self._tokenizer_select.set_options([(t, t) for t in tokenizers])
            if tokenizers:
                self._tokenizer_select.value = self._tokenizer

        return bool(self._tokenizer)

    def _update_metric_dropdown(
        self,
        scan_results: dict[str, ScanResult],
        sweep_results: list[SweepPoint],
        dataset_results: dict[str, ScanResult],
    ) -> None:
        """Update metric dropdown."""
        metrics = self._get_metrics_for_source(
            self._source, self._tokenizer, scan_results, sweep_results, dataset_results
        )

        if self._metric_select:
            if self._metric not in metrics:
                self._metric = metrics[0] if metrics else "jsd"
            self._metric_select.set_options([(m.upper(), m) for m in metrics])
            if metrics:
                self._metric_select.value = self._metric

    def _render_charts(self, data: ChartData) -> None:
        """Render all charts with the given data."""
        subtitle = f"{self._metric.upper()} · {self._tokenizer}"

        # Update subtitles
        if self._histogram_subtitle:
            self._histogram_subtitle.update(subtitle)
        if self._boxplot_subtitle:
            self._boxplot_subtitle.update(subtitle)
        if self._line_subtitle:
            self._line_subtitle.update(subtitle)
        if self._stats_subtitle:
            self._stats_subtitle.update(subtitle)

        # Draw charts
        self._draw_histogram(data.distribution_values, self._metric)
        self._draw_boxplot(data.distribution_values, self._metric)
        self._draw_line(
            data.trend_values,
            self._metric,
            x_label=data.x_label,
            x_values=data.x_values,
        )
        self._update_stats(
            data.distribution_values or data.trend_values,
            self._metric,
            data.source_label,
        )

    def _show_no_data(self) -> None:
        """Display no data message in all charts."""
        no_data = Text("No data available\n\nRun a sweep to generate charts")
        no_data.stylize(f"italic {PALETTE['text_muted']}")

        if self._histogram_display:
            self._histogram_display.update(no_data)
        if self._boxplot_display:
            self._boxplot_display.update(no_data)
        if self._line_display:
            self._line_display.update(no_data)
        if self._stats_display:
            self._stats_display.update(no_data)

        # Clear subtitles
        if self._histogram_subtitle:
            self._histogram_subtitle.update("")
        if self._boxplot_subtitle:
            self._boxplot_subtitle.update("")
        if self._line_subtitle:
            self._line_subtitle.update("")
        if self._stats_subtitle:
            self._stats_subtitle.update("")

    def _draw_histogram(self, values: list[float], metric: str) -> None:
        """Draw an ASCII histogram."""
        if self._histogram_display is None:
            return

        if not values:
            self._histogram_display.update("")
            return

        # Build output with header
        output = Text()
        output.append(f" {metric.upper()} n={len(values)}\n\n", style=PALETTE["green_bright"])

        # Use renderer for the chart
        chart_output = self._histogram_renderer.render(values, metric)

        # Adjust formatting to match existing style
        for line in chart_output.plain.split("\n"):
            if line.strip():
                output.append(f" {line}\n", style=PALETTE["cyan"])

        output.append(f" {'─' * 6}┴{'─' * HISTOGRAM_CHART_WIDTH}→\n", style=PALETTE["green_dim"])

        self._histogram_display.update(output)

    def _draw_boxplot(self, values: list[float], metric: str) -> None:
        """Draw an ASCII boxplot."""
        if self._boxplot_display is None:
            return

        if not values:
            self._boxplot_display.update("")
            return

        # Build output with header
        output = Text()
        output.append(f" {metric.upper()} n={len(values)}\n\n", style=PALETTE["green_bright"])

        # Use renderer for the chart
        chart_output = self._boxplot_renderer.render(values, metric)

        # Add spacing and use chart output
        output.append(" ")
        output.extend(chart_output)
        output.append("\n")

        self._boxplot_display.update(output)

    def _draw_line(
        self,
        values: list[float],
        metric: str,
        *,
        x_label: str = "seed",
        x_values: list[float] | None = None,
    ) -> None:
        """Draw an ASCII line chart."""
        if self._line_display is None:
            return

        if not values:
            self._line_display.update("")
            return

        x_points = (
            list(x_values)
            if x_values is not None and len(x_values) == len(values)
            else list(range(len(values)))
        )

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        chart_height = LINE_CHART_HEIGHT
        chart_width = min(LINE_CHART_MAX_WIDTH, len(values))

        # Sample values if too many
        if len(values) > chart_width:
            step = len(values) / chart_width
            indices = [int(i * step) for i in range(chart_width)]
            sampled = [values[idx] for idx in indices]
            sampled_x = [x_points[idx] for idx in indices]
        else:
            sampled = values
            sampled_x = x_points

        # Build output
        output = Text()
        x_title = x_label.replace("_", " ").title() if x_label else "Index"
        output.append(f" {metric.upper()} vs {x_title}\n\n", style=PALETTE["green_bright"])

        # Create grid
        grid = [[" "] * (len(sampled) + 7) for _ in range(chart_height)]

        # Plot points
        for x, v in enumerate(sampled):
            y = int(((v - min_val) / range_val) * (chart_height - 1))
            y = chart_height - 1 - y
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
            output.append(" ", style=PALETTE["green_dim"])
            for c in row:
                if c == "●":
                    output.append(c, style=PALETTE["cyan"])
                elif c in "│─":
                    output.append(c, style=PALETTE["green_dim"])
                else:
                    output.append(c, style=PALETTE["amber"])
            output.append("\n")

        # X axis
        output.append(f" {'─' * 6}┴{'─' * len(sampled)}→\n", style=PALETTE["green_dim"])
        if sampled_x:
            start_val, end_val = sampled_x[0], sampled_x[-1]
            try:
                output.append(
                    f" [{start_val:.2f} → {end_val:.2f}]\n",
                    style=PALETTE["green_dim"],
                )
            except (TypeError, ValueError):
                pass

        self._line_display.update(output)

    def _update_stats(
        self,
        values: list[float],
        metric: str,
        source_label: str | None = None,
    ) -> None:
        """Update statistics display."""
        if self._stats_display is None:
            return

        if not values:
            self._stats_display.update("No data available")
            return

        # Use renderer for statistics
        output = self._stats_renderer.render(values, metric)

        # Add source label if provided
        if source_label:
            output.append(f"\nSource: {source_label}", style=PALETTE["text_muted"])

        self._stats_display.update(output)

    def refresh_charts(self) -> None:
        """Refresh all charts with current data."""
        self._update_charts()
