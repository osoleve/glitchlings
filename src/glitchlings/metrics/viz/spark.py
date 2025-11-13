"""Sparkline visualization for metric trends by sequence length.

Sparklines show how metrics vary with input length, revealing
length-dependent sensitivities in glitchlings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..core.schema import Observation


def create_sparklines(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    group_by: str = "glitchling_id",
    length_bins: int | Sequence[int] | None = None,
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
) -> Any:
    """Create sparkline grid showing metric trends by length.

    Each row is a group (e.g., glitchling), each column is a metric.
    Sparklines show how the metric changes with input sequence length.

    Args:
        observations: Sequence of observations
        metrics: Metric IDs to display
        group_by: Observation attribute for rows (default: glitchling_id)
        length_bins: Number of bins or custom bin edges for length
        title: Overall figure title
        backend: Visualization backend ("matplotlib" or "plotly")
        output_path: Path to save figure

    Returns:
        Figure object

    Example:
        >>> fig = create_sparklines(
        ...     observations,
        ...     metrics=["ned.value", "lcsr.value", "jsdiv.value"],
        ...     group_by="glitchling_id",
        ...     length_bins=10,
        ...     title="Metric Trends by Input Length"
        ... )
    """
    if backend == "matplotlib":
        return _create_sparklines_matplotlib(
            observations, metrics, group_by, length_bins, title, output_path
        )
    elif backend == "plotly":
        return _create_sparklines_plotly(
            observations, metrics, group_by, length_bins, title, output_path
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _bin_observations_by_length(
    observations: Sequence[Observation],
    bins: int | Sequence[int] | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin observations by sequence length.

    Args:
        observations: Sequence of observations
        bins: Number of bins or custom bin edges

    Returns:
        Tuple of (bin_centers, bin_assignments)
    """
    lengths = np.array([obs.m for obs in observations])

    if bins is None:
        bins = 10

    if isinstance(bins, int):
        # Create equal-width bins
        bin_edges = np.linspace(lengths.min(), lengths.max() + 1, bins + 1)
    else:
        bin_edges = np.array(bins)

    # Assign observations to bins
    bin_assignments = np.digitize(lengths, bin_edges) - 1
    bin_assignments = np.clip(bin_assignments, 0, len(bin_edges) - 2)

    # Compute bin centers
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    return bin_centers, bin_assignments


def _aggregate_by_length_bins(
    observations: Sequence[Observation],
    metric: str,
    group_value: str,
    group_by: str,
    bin_centers: np.ndarray,
    bin_assignments: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate metric values by length bins for one group.

    Returns:
        Tuple of (x_values, y_values) for sparkline
    """
    # Filter observations for this group
    group_obs_indices = [
        i for i, obs in enumerate(observations) if str(getattr(obs, group_by)) == group_value
    ]

    if not group_obs_indices:
        return np.array([]), np.array([])

    # Aggregate by bin
    n_bins = len(bin_centers)
    bin_values = [[] for _ in range(n_bins)]

    for i in group_obs_indices:
        obs = observations[i]
        bin_idx = bin_assignments[i]
        if metric in obs.metrics:
            bin_values[bin_idx].append(obs.metrics[metric])

    # Compute median for each bin
    x_vals = []
    y_vals = []
    for bin_idx, values in enumerate(bin_values):
        if values:
            x_vals.append(bin_centers[bin_idx])
            y_vals.append(np.median(values))

    return np.array(x_vals), np.array(y_vals)


def _create_sparklines_matplotlib(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    group_by: str,
    length_bins: int | Sequence[int] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create sparklines using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    # Get unique groups
    groups = sorted(set(str(getattr(obs, group_by)) for obs in observations))

    # Bin observations by length
    bin_centers, bin_assignments = _bin_observations_by_length(observations, length_bins)

    n_groups = len(groups)
    n_metrics = len(metrics)

    # Create grid of sparklines
    fig, axes = plt.subplots(
        n_groups,
        n_metrics,
        figsize=(n_metrics * 3, n_groups * 1.5),
        squeeze=False,
    )

    # Plot sparklines
    for row_idx, group in enumerate(groups):
        for col_idx, metric in enumerate(metrics):
            ax = axes[row_idx, col_idx]

            # Get data for this group and metric
            x_vals, y_vals = _aggregate_by_length_bins(
                observations, metric, group, group_by, bin_centers, bin_assignments
            )

            if len(x_vals) > 0:
                # Plot sparkline
                ax.plot(x_vals, y_vals, linewidth=2, color="steelblue")
                ax.fill_between(x_vals, y_vals, alpha=0.3, color="steelblue")

                # Minimal styling
                ax.set_ylim(0, 1)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

                # Only show axes on edges
                if row_idx == n_groups - 1:
                    ax.set_xlabel("Length", fontsize=8)
                else:
                    ax.set_xticklabels([])

                if col_idx == 0:
                    ax.set_ylabel(group, fontsize=8, rotation=0, ha="right", va="center")
                else:
                    ax.set_yticklabels([])

                # Column headers
                if row_idx == 0:
                    metric_short = metric.replace("metric_", "").replace(".value", "")
                    ax.set_title(metric_short, fontsize=9, fontweight="bold")

                # Light grid
                ax.grid(True, alpha=0.2, linewidth=0.5)
            else:
                # No data
                ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=8)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")

    if title:
        fig.suptitle(title, fontsize=12, y=0.995)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_sparklines_plotly(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    group_by: str,
    length_bins: int | Sequence[int] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create interactive sparklines using plotly."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as e:
        raise ImportError("plotly required") from e

    # Get unique groups
    groups = sorted(set(str(getattr(obs, group_by)) for obs in observations))

    # Bin observations by length
    bin_centers, bin_assignments = _bin_observations_by_length(observations, length_bins)

    n_groups = len(groups)
    n_metrics = len(metrics)

    # Create subplot grid
    subplot_titles = [
        f"{metric.replace('metric_', '').replace('.value', '')}" if row_idx == 0 else ""
        for row_idx in range(n_groups)
        for metric in metrics
    ]

    fig = make_subplots(
        rows=n_groups,
        cols=n_metrics,
        subplot_titles=subplot_titles[:n_metrics],  # Only top row
        vertical_spacing=0.05,
        horizontal_spacing=0.05,
        row_titles=[f"<b>{g}</b>" for g in groups],
    )

    # Plot sparklines
    for row_idx, group in enumerate(groups):
        for col_idx, metric in enumerate(metrics):
            # Get data
            x_vals, y_vals = _aggregate_by_length_bins(
                observations, metric, group, group_by, bin_centers, bin_assignments
            )

            if len(x_vals) > 0:
                # Add line
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines",
                        line=dict(color="steelblue", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(70, 130, 180, 0.3)",
                        showlegend=False,
                        hovertemplate=f"Length: %{{x:.0f}}<br>{metric}: %{{y:.3f}}<extra></extra>",
                    ),
                    row=row_idx + 1,
                    col=col_idx + 1,
                )

                # Update axes
                fig.update_yaxes(range=[0, 1], row=row_idx + 1, col=col_idx + 1)

    # Layout
    fig.update_layout(
        title=title or "Metric Trends by Length",
        height=150 * n_groups,
        width=300 * n_metrics,
        showlegend=False,
    )

    # Update all x-axes
    fig.update_xaxes(title_text="Length", row=n_groups)

    if output_path:
        fig.write_html(str(output_path))

    return fig


def create_length_sensitivity_plot(
    observations: Sequence[Observation],
    metric: str,
    group_by: str = "glitchling_id",
    length_bins: int | None = None,
    show_confidence: bool = True,
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
) -> Any:
    """Create detailed length sensitivity plot for one metric.

    Shows metric trends with confidence intervals (IQR or std) for each group.

    Args:
        observations: Sequence of observations
        metric: Metric ID to display
        group_by: Observation attribute for grouping
        length_bins: Number of length bins
        show_confidence: Show IQR bands
        title: Chart title
        backend: Visualization backend
        output_path: Path to save figure

    Returns:
        Figure object

    Example:
        >>> fig = create_length_sensitivity_plot(
        ...     observations,
        ...     metric="ned.value",
        ...     group_by="glitchling_id",
        ...     show_confidence=True,
        ...     title="Edit Distance Sensitivity to Input Length"
        ... )
    """
    if backend == "matplotlib":
        return _create_length_sensitivity_matplotlib(
            observations,
            metric,
            group_by,
            length_bins,
            show_confidence,
            title,
            output_path,
        )
    elif backend == "plotly":
        return _create_length_sensitivity_plotly(
            observations,
            metric,
            group_by,
            length_bins,
            show_confidence,
            title,
            output_path,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_length_sensitivity_matplotlib(
    observations: Sequence[Observation],
    metric: str,
    group_by: str,
    length_bins: int | None,
    show_confidence: bool,
    title: str | None,
    output_path: str | Path | None,
):
    """Create length sensitivity plot using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    # Get unique groups
    groups = sorted(set(str(getattr(obs, group_by)) for obs in observations))

    # Bin observations
    bin_centers, bin_assignments = _bin_observations_by_length(observations, length_bins)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = plt.cm.tab10(np.linspace(0, 1, len(groups)))

    for group_idx, group in enumerate(groups):
        # Filter observations for this group
        group_obs = [
            (i, obs)
            for i, obs in enumerate(observations)
            if str(getattr(obs, group_by)) == group and metric in obs.metrics
        ]

        if not group_obs:
            continue

        # Aggregate by bin
        n_bins = len(bin_centers)
        bin_data = [[] for _ in range(n_bins)]

        for i, obs in group_obs:
            bin_idx = bin_assignments[i]
            bin_data[bin_idx].append(obs.metrics[metric])

        # Compute statistics
        x_vals = []
        medians = []
        q1_vals = []
        q3_vals = []

        for bin_idx, values in enumerate(bin_data):
            if len(values) >= 2:
                x_vals.append(bin_centers[bin_idx])
                medians.append(np.median(values))
                q1_vals.append(np.percentile(values, 25))
                q3_vals.append(np.percentile(values, 75))

        if x_vals:
            x_vals = np.array(x_vals)
            medians = np.array(medians)
            q1_vals = np.array(q1_vals)
            q3_vals = np.array(q3_vals)

            # Plot median line
            ax.plot(
                x_vals,
                medians,
                linewidth=2.5,
                label=group,
                color=colors[group_idx],
                marker="o",
                markersize=5,
            )

            # Plot confidence band
            if show_confidence:
                ax.fill_between(
                    x_vals,
                    q1_vals,
                    q3_vals,
                    alpha=0.2,
                    color=colors[group_idx],
                )

    ax.set_xlabel("Input Length (tokens)", fontsize=11)
    ax.set_ylabel(metric.replace("metric_", "").replace(".value", ""), fontsize=11)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.legend(title=group_by.replace("_", " ").title())

    if title:
        ax.set_title(title, fontsize=13, pad=15)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_length_sensitivity_plotly(
    observations: Sequence[Observation],
    metric: str,
    group_by: str,
    length_bins: int | None,
    show_confidence: bool,
    title: str | None,
    output_path: str | Path | None,
):
    """Create length sensitivity plot using plotly."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError("plotly required") from e

    # Get unique groups
    groups = sorted(set(str(getattr(obs, group_by)) for obs in observations))

    # Bin observations
    bin_centers, bin_assignments = _bin_observations_by_length(observations, length_bins)

    fig = go.Figure()

    for group in groups:
        # Filter observations for this group
        group_obs = [
            (i, obs)
            for i, obs in enumerate(observations)
            if str(getattr(obs, group_by)) == group and metric in obs.metrics
        ]

        if not group_obs:
            continue

        # Aggregate by bin
        n_bins = len(bin_centers)
        bin_data = [[] for _ in range(n_bins)]

        for i, obs in group_obs:
            bin_idx = bin_assignments[i]
            bin_data[bin_idx].append(obs.metrics[metric])

        # Compute statistics
        x_vals = []
        medians = []
        q1_vals = []
        q3_vals = []

        for bin_idx, values in enumerate(bin_data):
            if len(values) >= 2:
                x_vals.append(bin_centers[bin_idx])
                medians.append(np.median(values))
                q1_vals.append(np.percentile(values, 25))
                q3_vals.append(np.percentile(values, 75))

        if x_vals:
            # Add median line
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=medians,
                    mode="lines+markers",
                    name=group,
                    line=dict(width=2.5),
                    marker=dict(size=6),
                    hovertemplate=(
                        f"{group}<br>Length: %{{x:.0f}}<br>{metric}: %{{y:.3f}}<extra></extra>"
                    ),
                )
            )

            # Add confidence band
            if show_confidence:
                fig.add_trace(
                    go.Scatter(
                        x=x_vals.tolist() + x_vals.tolist()[::-1],
                        y=q3_vals.tolist() + q1_vals.tolist()[::-1],
                        fill="toself",
                        fillcolor=fig.data[-1].line.color,
                        opacity=0.2,
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

    # Layout
    fig.update_layout(
        title=title or f"{metric} vs Input Length",
        xaxis_title="Input Length (tokens)",
        yaxis_title=metric.replace("metric_", "").replace(".value", ""),
        yaxis=dict(range=[0, 1]),
        width=900,
        height=600,
        hovermode="closest",
        legend_title=group_by.replace("_", " ").title(),
    )

    if output_path:
        fig.write_html(str(output_path))

    return fig


__all__ = [
    "create_sparklines",
    "create_length_sensitivity_plot",
]
