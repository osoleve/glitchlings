"""Chart rendering utilities for the Textual GUI.

Provides ASCII-style chart renderers as separate, focused classes.
"""

from __future__ import annotations

import statistics
from typing import Sequence

from rich.text import Text

from .theme import PALETTE

# Chart rendering constants
HISTOGRAM_BINS = 8
HISTOGRAM_CHART_WIDTH = 28
BOXPLOT_CHART_WIDTH = 40
LINE_CHART_HEIGHT = 8
LINE_CHART_MAX_WIDTH = 32


class HistogramRenderer:
    """Renders ASCII histogram charts."""

    def __init__(self, bins: int = HISTOGRAM_BINS, width: int = HISTOGRAM_CHART_WIDTH):
        self.bins = bins
        self.width = width

    def render(self, values: Sequence[float], metric_name: str = "") -> Text:
        """
        Render histogram as ASCII art.

        Args:
            values: Data points to histogram
            metric_name: Optional metric name for title

        Returns:
            Rich Text object with rendered histogram
        """
        output = Text()

        if not values:
            output.append("No data available", style=PALETTE["text_muted"])
            return output

        # Calculate histogram
        min_val = min(values)
        max_val = max(values)

        if min_val == max_val:
            output.append("All values are identical", style=PALETTE["text_muted"])
            return output

        bin_width = (max_val - min_val) / self.bins
        bins_count = [0] * self.bins

        for v in values:
            bin_idx = min(int((v - min_val) / bin_width), self.bins - 1)
            bins_count[bin_idx] += 1

        max_count = max(bins_count)

        # Render bars
        for i, count in enumerate(bins_count):
            bar_len = int((count / max_count) * self.width) if max_count > 0 else 0
            bin_start = min_val + i * bin_width
            bin_end = min_val + (i + 1) * bin_width

            output.append(f"{bin_start:.3f}-{bin_end:.3f} ", style=PALETTE["text_muted"])
            output.append("█" * bar_len, style=PALETTE["cyan"])
            output.append(f" {count}\n", style=PALETTE["text_muted"])

        return output


class BoxPlotRenderer:
    """Renders ASCII box plot charts."""

    def __init__(self, width: int = BOXPLOT_CHART_WIDTH):
        self.width = width

    def render(self, values: Sequence[float], metric_name: str = "") -> Text:
        """
        Render box plot as ASCII art.

        Args:
            values: Data points for box plot
            metric_name: Optional metric name for title

        Returns:
            Rich Text object with rendered box plot
        """
        output = Text()

        if not values:
            output.append("No data available", style=PALETTE["text_muted"])
            return output

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        q1 = sorted_vals[n // 4]
        q2 = sorted_vals[n // 2]
        q3 = sorted_vals[3 * n // 4]
        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]

        # Scale to chart width
        value_range = max_val - min_val
        if value_range == 0:
            output.append("All values are identical", style=PALETTE["text_muted"])
            return output

        def scale(v: float) -> int:
            return int(((v - min_val) / value_range) * self.width)

        min_pos = 0
        q1_pos = scale(q1)
        q2_pos = scale(q2)
        q3_pos = scale(q3)
        max_pos = self.width

        # Build box plot
        line = [" "] * (self.width + 1)

        # Whiskers
        for i in range(min_pos, q1_pos):
            line[i] = "─"
        for i in range(q3_pos, max_pos + 1):
            line[i] = "─"

        # Box
        for i in range(q1_pos, q3_pos + 1):
            line[i] = "█"

        # Median marker
        if q2_pos <= self.width:
            line[q2_pos] = "│"

        # End markers
        line[min_pos] = "├"
        if max_pos <= self.width:
            line[max_pos] = "┤"

        output.append("".join(line), style=PALETTE["cyan"])
        output.append("\n")

        # Labels
        output.append(f"min={min_val:.3f} q1={q1:.3f} ", style=PALETTE["text_muted"])
        output.append(f"median={q2:.3f} ", style=PALETTE["amber"])
        output.append(f"q3={q3:.3f} max={max_val:.3f}", style=PALETTE["text_muted"])

        return output


class LineChartRenderer:
    """Renders ASCII line charts."""

    def __init__(self, height: int = LINE_CHART_HEIGHT, max_width: int = LINE_CHART_MAX_WIDTH):
        self.height = height
        self.max_width = max_width

    def render(self, values: Sequence[float], metric_name: str = "") -> Text:
        """
        Render line chart as ASCII art.

        Args:
            values: Data points for line chart
            metric_name: Optional metric name for title

        Returns:
            Rich Text object with rendered line chart
        """
        output = Text()

        if not values:
            output.append("No data available", style=PALETTE["text_muted"])
            return output

        if len(values) < 2:
            output.append("Need at least 2 points for line chart", style=PALETTE["text_muted"])
            return output

        # Downsample if too many points
        if len(values) > self.max_width:
            step = len(values) / self.max_width
            sampled = [values[int(i * step)] for i in range(self.max_width)]
        else:
            sampled = list(values)

        min_val = min(sampled)
        max_val = max(sampled)
        value_range = max_val - min_val

        if value_range == 0:
            output.append("All values are identical", style=PALETTE["text_muted"])
            return output

        # Create grid
        grid = [[" " for _ in range(len(sampled))] for _ in range(self.height)]

        # Plot points
        for x, val in enumerate(sampled):
            y = self.height - 1 - int(((val - min_val) / value_range) * (self.height - 1))
            y = max(0, min(self.height - 1, y))
            grid[y][x] = "●"

        # Render grid
        for row in grid:
            output.append("".join(row), style=PALETTE["cyan"])
            output.append("\n")

        # Labels
        output.append(f"min={min_val:.3f} max={max_val:.3f} ", style=PALETTE["text_muted"])
        output.append(f"points={len(values)}", style=PALETTE["text_muted"])

        return output


class StatsRenderer:
    """Renders statistics display."""

    def render(self, values: Sequence[float], metric_name: str) -> Text:
        """
        Render statistics for a metric.

        Args:
            values: Data points
            metric_name: Name of the metric

        Returns:
            Rich Text object with formatted statistics
        """
        from ..metrics_utils import calculate_stats

        output = Text()

        if not values:
            output.append("No data available", style=PALETTE["text_muted"])
            return output

        mean, std = calculate_stats(values)
        min_val = min(values)
        max_val = max(values)
        median = statistics.median(values)

        output.append(f"{metric_name.upper()} Statistics\n", style=PALETTE["green_bright"])
        output.append("─────────────────────\n", style=PALETTE["border"])
        output.append(f"Mean:   {mean:.4f} ± {std:.4f}\n", style=PALETTE["amber"])
        output.append(f"Median: {median:.4f}\n", style=PALETTE["amber"])
        output.append(f"Min:    {min_val:.4f}\n", style=PALETTE["amber"])
        output.append(f"Max:    {max_val:.4f}\n", style=PALETTE["amber"])
        output.append(f"Range:  {max_val - min_val:.4f}\n", style=PALETTE["amber"])
        output.append(f"Count:  {len(values)}", style=PALETTE["text_muted"])

        return output
