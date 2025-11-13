"""Radar chart visualization for transformation fingerprints.

Radar charts (aka spider charts) visualize a glitchling's effect across
multiple orthogonal metrics, creating a "fingerprint" of its behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .aggregate import normalize_metrics


def create_radar_chart(
    glitchling_metrics: dict[str, float],
    metric_labels: Sequence[str] | None = None,
    normalization: str = "percentile",
    reference_stats: dict[str, dict[str, float]] | None = None,
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
) -> Any:
    """Create a radar chart showing glitchling transformation fingerprint.

    Args:
        glitchling_metrics: Dict of metric values for one glitchling
        metric_labels: Custom labels for metrics (defaults to metric IDs)
        normalization: Normalization method ("percentile", "minmax", "none")
        reference_stats: Reference statistics for normalization
        title: Chart title
        backend: Visualization backend ("matplotlib" or "plotly")
        output_path: Path to save figure (None = show only)

    Returns:
        Figure object (matplotlib.Figure or plotly.Figure)

    Example:
        >>> metrics = {
        ...     "ned.value": 0.3,
        ...     "jsdiv.value": 0.2,
        ...     "rord.value": 0.5,
        ...     "spi.value": 0.1,
        ... }
        >>> fig = create_radar_chart(metrics, title="Typogre Fingerprint")
    """
    if backend == "matplotlib":
        return _create_radar_matplotlib(
            glitchling_metrics,
            metric_labels,
            normalization,
            reference_stats,
            title,
            output_path,
        )
    elif backend == "plotly":
        return _create_radar_plotly(
            glitchling_metrics,
            metric_labels,
            normalization,
            reference_stats,
            title,
            output_path,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_radar_matplotlib(
    glitchling_metrics: dict[str, float],
    metric_labels: Sequence[str] | None,
    normalization: str,
    reference_stats: dict[str, dict[str, float]] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create radar chart using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "matplotlib required for radar charts. "
            "Install with: pip install matplotlib"
        ) from e

    # Normalize metrics
    normalized = normalize_metrics(glitchling_metrics, normalization, reference_stats)

    # Prepare data
    metrics = list(normalized.keys())
    values = [normalized[m] for m in metrics]

    if metric_labels is None:
        # Clean up metric names for display
        labels = [m.replace("metric_", "").replace(".value", "") for m in metrics]
    else:
        labels = list(metric_labels)

    # Number of metrics
    n = len(metrics)

    # Compute angle for each axis
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()

    # Close the plot
    values += values[:1]
    angles += angles[:1]
    labels_closed = labels + [labels[0]]

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))

    # Plot data
    ax.plot(angles, values, "o-", linewidth=2, label="Glitchling")
    ax.fill(angles, values, alpha=0.25)

    # Fix axis to go from 0 to 1
    ax.set_ylim(0, 1)

    # Set labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10)

    # Add grid
    ax.grid(True)

    # Set title
    if title:
        ax.set_title(title, size=14, pad=20)

    # Adjust layout
    plt.tight_layout()

    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_radar_plotly(
    glitchling_metrics: dict[str, float],
    metric_labels: Sequence[str] | None,
    normalization: str,
    reference_stats: dict[str, dict[str, float]] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create interactive radar chart using plotly."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError(
            "plotly required for interactive radar charts. "
            "Install with: pip install plotly"
        ) from e

    # Normalize metrics
    normalized = normalize_metrics(glitchling_metrics, normalization, reference_stats)

    # Prepare data
    metrics = list(normalized.keys())
    values = [normalized[m] for m in metrics]

    if metric_labels is None:
        labels = [m.replace("metric_", "").replace(".value", "") for m in metrics]
    else:
        labels = list(metric_labels)

    # Create figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            name="Glitchling",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=title or "Transformation Fingerprint",
    )

    # Save or show
    if output_path:
        fig.write_html(str(output_path))

    return fig


def create_multi_radar_chart(
    glitchling_data: dict[str, dict[str, float]],
    metric_labels: Sequence[str] | None = None,
    normalization: str = "percentile",
    reference_stats: dict[str, dict[str, float]] | None = None,
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
) -> Any:
    """Create radar chart comparing multiple glitchlings.

    Args:
        glitchling_data: Dict mapping glitchling_id to metric dict
        metric_labels: Custom labels for metrics
        normalization: Normalization method
        reference_stats: Reference statistics
        title: Chart title
        backend: Visualization backend
        output_path: Path to save figure

    Returns:
        Figure object

    Example:
        >>> data = {
        ...     "typogre": {"ned.value": 0.3, "jsdiv.value": 0.2},
        ...     "ekkokin": {"ned.value": 0.1, "jsdiv.value": 0.4},
        ... }
        >>> fig = create_multi_radar_chart(data, title="Glitchling Comparison")
    """
    if backend == "matplotlib":
        return _create_multi_radar_matplotlib(
            glitchling_data,
            metric_labels,
            normalization,
            reference_stats,
            title,
            output_path,
        )
    elif backend == "plotly":
        return _create_multi_radar_plotly(
            glitchling_data,
            metric_labels,
            normalization,
            reference_stats,
            title,
            output_path,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_multi_radar_matplotlib(
    glitchling_data: dict[str, dict[str, float]],
    metric_labels: Sequence[str] | None,
    normalization: str,
    reference_stats: dict[str, dict[str, float]] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create multi-glitchling radar chart using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    # Normalize all glitchlings
    normalized_data = {
        g_id: normalize_metrics(metrics, normalization, reference_stats)
        for g_id, metrics in glitchling_data.items()
    }

    # Get common metrics
    first_glitchling = list(glitchling_data.values())[0]
    metrics = list(first_glitchling.keys())

    if metric_labels is None:
        labels = [m.replace("metric_", "").replace(".value", "") for m in metrics]
    else:
        labels = list(metric_labels)

    # Number of metrics
    n = len(metrics)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))

    # Plot each glitchling
    colors = plt.cm.tab10(np.linspace(0, 1, len(glitchling_data)))

    for idx, (g_id, normalized) in enumerate(normalized_data.items()):
        values = [normalized.get(m, 0) for m in metrics]
        values += values[:1]

        ax.plot(angles, values, "o-", linewidth=2, label=g_id, color=colors[idx])
        ax.fill(angles, values, alpha=0.1, color=colors[idx])

    # Set limits
    ax.set_ylim(0, 1)

    # Set labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10)

    # Add grid and legend
    ax.grid(True)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    # Set title
    if title:
        ax.set_title(title, size=14, pad=20)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_multi_radar_plotly(
    glitchling_data: dict[str, dict[str, float]],
    metric_labels: Sequence[str] | None,
    normalization: str,
    reference_stats: dict[str, dict[str, float]] | None,
    title: str | None,
    output_path: str | Path | None,
):
    """Create interactive multi-glitchling radar chart using plotly."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError("plotly required") from e

    # Normalize all glitchlings
    normalized_data = {
        g_id: normalize_metrics(metrics, normalization, reference_stats)
        for g_id, metrics in glitchling_data.items()
    }

    # Get common metrics
    first_glitchling = list(glitchling_data.values())[0]
    metrics = list(first_glitchling.keys())

    if metric_labels is None:
        labels = [m.replace("metric_", "").replace(".value", "") for m in metrics]
    else:
        labels = list(metric_labels)

    # Create figure
    fig = go.Figure()

    for g_id, normalized in normalized_data.items():
        values = [normalized.get(m, 0) for m in metrics]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=labels,
                fill="toself",
                name=g_id,
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=title or "Glitchling Comparison",
    )

    if output_path:
        fig.write_html(str(output_path))

    return fig


__all__ = [
    "create_radar_chart",
    "create_multi_radar_chart",
]
