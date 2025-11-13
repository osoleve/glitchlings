"""Heatmap visualization for glitchling × tokenizer metric grids.

Heatmaps show how different glitchlings perform across tokenizers,
revealing tokenizer-specific sensitivities and cross-cutting patterns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from ..core.schema import Observation
from .aggregate import pivot_for_heatmap


def create_heatmap(
    observations: Sequence[Observation],
    metric: str,
    row_key: str = "glitchling_id",
    col_key: str = "tokenizer_id",
    aggregation: str = "median",
    show_iqr: bool = False,
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
    cmap: str = "YlOrRd",
    annotate: bool = True,
) -> Any:
    """Create heatmap showing metric values across two dimensions.

    Args:
        observations: Sequence of observations to visualize
        metric: Metric ID to display (e.g., "ned.value")
        row_key: Observation field for rows (default: glitchling_id)
        col_key: Observation field for columns (default: tokenizer_id)
        aggregation: Aggregation method ("mean", "median", "max")
        show_iqr: Show IQR uncertainty glyphs in cells (matplotlib only)
        title: Chart title
        backend: Visualization backend ("matplotlib" or "plotly")
        output_path: Path to save figure (None = show only)
        cmap: Colormap name (matplotlib) or scale (plotly)
        annotate: Show numeric values in cells

    Returns:
        Figure object (matplotlib.Figure or plotly.Figure)

    Example:
        >>> observations = [...]  # From batch processing
        >>> fig = create_heatmap(
        ...     observations,
        ...     metric="ned.value",
        ...     row_key="glitchling_id",
        ...     col_key="tokenizer_id",
        ...     aggregation="median",
        ...     title="Edit Distance by Glitchling × Tokenizer"
        ... )
    """
    if backend == "matplotlib":
        return _create_heatmap_matplotlib(
            observations,
            metric,
            row_key,
            col_key,
            aggregation,
            show_iqr,
            title,
            output_path,
            cmap,
            annotate,
        )
    elif backend == "plotly":
        return _create_heatmap_plotly(
            observations,
            metric,
            row_key,
            col_key,
            aggregation,
            title,
            output_path,
            cmap,
            annotate,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_heatmap_matplotlib(
    observations: Sequence[Observation],
    metric: str,
    row_key: str,
    col_key: str,
    aggregation: str,
    show_iqr: bool,
    title: str | None,
    output_path: str | Path | None,
    cmap: str,
    annotate: bool,
):
    """Create heatmap using matplotlib/seaborn."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "matplotlib required for heatmaps. Install with: pip install matplotlib"
        ) from e

    # Try to use seaborn if available (better defaults)
    try:
        import seaborn as sns

        use_seaborn = True
    except ImportError:
        use_seaborn = False

    # Pivot to 2D matrix
    heatmap_data = pivot_for_heatmap(observations, row_key, col_key, metric, aggregation)

    if heatmap_data["values"].size == 0:
        raise ValueError("No data to plot after aggregation")

    values = heatmap_data["values"]
    row_labels = heatmap_data["row_labels"]
    col_labels = heatmap_data["col_labels"]

    # Create figure
    fig, ax = plt.subplots(figsize=(max(8, len(col_labels) * 1.2), max(6, len(row_labels) * 0.8)))

    if use_seaborn:
        # Use seaborn for prettier heatmaps
        sns.heatmap(
            values,
            annot=annotate,
            fmt=".3f" if annotate else "",
            cmap=cmap,
            xticklabels=col_labels,
            yticklabels=row_labels,
            cbar_kws={"label": metric},
            ax=ax,
            vmin=0,
            vmax=1,
        )
    else:
        # Manual matplotlib heatmap
        im = ax.imshow(values, cmap=cmap, aspect="auto", vmin=0, vmax=1)

        # Set ticks
        ax.set_xticks(range(len(col_labels)))
        ax.set_yticks(range(len(row_labels)))
        ax.set_xticklabels(col_labels, rotation=45, ha="right")
        ax.set_yticklabels(row_labels)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(metric)

        # Annotate cells
        if annotate:
            for i in range(len(row_labels)):
                for j in range(len(col_labels)):
                    value = values[i, j]
                    if not np.isnan(value):
                        ax.text(
                            j,
                            i,
                            f"{value:.3f}",
                            ha="center",
                            va="center",
                            color="black" if value > 0.5 else "white",
                            fontsize=9,
                        )

    # Add IQR glyphs if requested
    if show_iqr and not use_seaborn:
        _add_iqr_glyphs(ax, observations, row_key, col_key, metric, row_labels, col_labels)

    # Labels
    ax.set_xlabel(col_key.replace("_", " ").title())
    ax.set_ylabel(row_key.replace("_", " ").title())

    if title:
        ax.set_title(title, pad=20)

    plt.tight_layout()

    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _add_iqr_glyphs(ax, observations, row_key, col_key, metric, row_labels, col_labels):
    """Add IQR uncertainty glyphs to heatmap cells."""
    import numpy as np

    # Compute IQR for each cell
    for i, row_val in enumerate(row_labels):
        for j, col_val in enumerate(col_labels):
            # Filter observations for this cell
            cell_obs = [
                obs
                for obs in observations
                if getattr(obs, row_key) == row_val and getattr(obs, col_key) == col_val
            ]

            if len(cell_obs) < 2:
                continue

            # Extract metric values
            values = [obs.metrics.get(metric, np.nan) for obs in cell_obs]
            values = [v for v in values if not np.isnan(v)]

            if len(values) < 2:
                continue

            # Compute IQR
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1

            # Draw error bars if IQR is significant
            if iqr > 0.05:  # Only show if uncertainty > 5%
                # Draw small vertical line indicating uncertainty
                ax.plot(
                    [j, j],
                    [i - 0.15, i + 0.15],
                    color="black",
                    linewidth=1.5,
                    alpha=0.6,
                )


def _create_heatmap_plotly(
    observations: Sequence[Observation],
    metric: str,
    row_key: str,
    col_key: str,
    aggregation: str,
    title: str | None,
    output_path: str | Path | None,
    cmap: str,
    annotate: bool,
):
    """Create interactive heatmap using plotly."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError(
            "plotly required for interactive heatmaps. Install with: pip install plotly"
        ) from e

    # Pivot to 2D matrix
    heatmap_data = pivot_for_heatmap(observations, row_key, col_key, metric, aggregation)

    if heatmap_data["values"].size == 0:
        raise ValueError("No data to plot after aggregation")

    values = heatmap_data["values"]
    row_labels = heatmap_data["row_labels"]
    col_labels = heatmap_data["col_labels"]

    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            x=col_labels,
            y=row_labels,
            colorscale=cmap if cmap != "YlOrRd" else "YlOrRd",
            colorbar=dict(title=metric),
            text=values if annotate else None,
            texttemplate="%{text:.3f}" if annotate else None,
            textfont={"size": 10},
            hovertemplate=(
                f"{row_key}: %{{y}}<br>{col_key}: %{{x}}<br>{metric}: %{{z:.3f}}<extra></extra>"
            ),
            zmin=0,
            zmax=1,
        )
    )

    # Layout
    fig.update_layout(
        title=title or f"{metric} by {row_key} × {col_key}",
        xaxis_title=col_key.replace("_", " ").title(),
        yaxis_title=row_key.replace("_", " ").title(),
        width=max(600, len(col_labels) * 80),
        height=max(400, len(row_labels) * 60),
    )

    # Save or show
    if output_path:
        fig.write_html(str(output_path))

    return fig


def create_multi_metric_heatmap(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    row_key: str = "glitchling_id",
    col_key: str = "tokenizer_id",
    aggregation: str = "median",
    title: str | None = None,
    backend: str = "matplotlib",
    output_path: str | Path | None = None,
) -> Any:
    """Create a grid of heatmaps, one per metric.

    Args:
        observations: Sequence of observations
        metrics: List of metric IDs to display
        row_key: Observation field for rows
        col_key: Observation field for columns
        aggregation: Aggregation method
        title: Overall figure title
        backend: Visualization backend
        output_path: Path to save figure

    Returns:
        Figure object

    Example:
        >>> fig = create_multi_metric_heatmap(
        ...     observations,
        ...     metrics=["ned.value", "lcsr.value", "jsdiv.value"],
        ...     title="Key Metrics Across Glitchlings"
        ... )
    """
    if backend == "matplotlib":
        return _create_multi_heatmap_matplotlib(
            observations, metrics, row_key, col_key, aggregation, title, output_path
        )
    elif backend == "plotly":
        return _create_multi_heatmap_plotly(
            observations, metrics, row_key, col_key, aggregation, title, output_path
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_multi_heatmap_matplotlib(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    row_key: str,
    col_key: str,
    aggregation: str,
    title: str | None,
    output_path: str | Path | None,
):
    """Create multi-metric heatmap grid using matplotlib."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    try:
        import seaborn as sns

        use_seaborn = True
    except ImportError:
        use_seaborn = False

    n_metrics = len(metrics)
    n_cols = min(3, n_metrics)
    n_rows = (n_metrics + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows), squeeze=False)

    for idx, metric in enumerate(metrics):
        row_idx = idx // n_cols
        col_idx = idx % n_cols
        ax = axes[row_idx, col_idx]

        # Pivot data
        heatmap_data = pivot_for_heatmap(observations, row_key, col_key, metric, aggregation)

        if heatmap_data["values"].size == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            ax.set_title(metric)
            continue

        values = heatmap_data["values"]
        row_labels = heatmap_data["row_labels"]
        col_labels = heatmap_data["col_labels"]

        # Plot
        if use_seaborn:
            sns.heatmap(
                values,
                annot=True,
                fmt=".2f",
                cmap="YlOrRd",
                xticklabels=col_labels,
                yticklabels=row_labels,
                cbar_kws={"label": metric},
                ax=ax,
                vmin=0,
                vmax=1,
            )
        else:
            im = ax.imshow(values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
            ax.set_xticks(range(len(col_labels)))
            ax.set_yticks(range(len(row_labels)))
            ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels(row_labels, fontsize=8)
            plt.colorbar(im, ax=ax, label=metric)

            # Annotate
            for i in range(len(row_labels)):
                for j in range(len(col_labels)):
                    value = values[i, j]
                    if not np.isnan(value):
                        ax.text(
                            j,
                            i,
                            f"{value:.2f}",
                            ha="center",
                            va="center",
                            color="black" if value > 0.5 else "white",
                            fontsize=7,
                        )

        ax.set_title(metric.replace("metric_", "").replace(".value", ""), fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")

    # Hide unused subplots
    for idx in range(n_metrics, n_rows * n_cols):
        row_idx = idx // n_cols
        col_idx = idx % n_cols
        axes[row_idx, col_idx].axis("off")

    # Overall title
    if title:
        fig.suptitle(title, fontsize=14, y=0.995)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_multi_heatmap_plotly(
    observations: Sequence[Observation],
    metrics: Sequence[str],
    row_key: str,
    col_key: str,
    aggregation: str,
    title: str | None,
    output_path: str | Path | None,
):
    """Create multi-metric heatmap grid using plotly subplots."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as e:
        raise ImportError("plotly required") from e

    n_metrics = len(metrics)
    n_cols = min(3, n_metrics)
    n_rows = (n_metrics + n_cols - 1) // n_cols

    # Create subplots
    subplot_titles = [m.replace("metric_", "").replace(".value", "") for m in metrics]
    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
    )

    for idx, metric in enumerate(metrics):
        row_idx = idx // n_cols + 1
        col_idx = idx % n_cols + 1

        # Pivot data
        heatmap_data = pivot_for_heatmap(observations, row_key, col_key, metric, aggregation)

        if heatmap_data["values"].size == 0:
            continue

        values = heatmap_data["values"]
        row_labels = heatmap_data["row_labels"]
        col_labels = heatmap_data["col_labels"]

        # Add heatmap
        fig.add_trace(
            go.Heatmap(
                z=values,
                x=col_labels,
                y=row_labels,
                colorscale="YlOrRd",
                showscale=True,
                text=values,
                texttemplate="%{text:.2f}",
                textfont={"size": 9},
                hovertemplate=f"{metric}: %{{z:.3f}}<extra></extra>",
                zmin=0,
                zmax=1,
            ),
            row=row_idx,
            col=col_idx,
        )

    # Layout
    fig.update_layout(
        title=title or f"Metrics by {row_key} × {col_key}",
        height=400 * n_rows,
        width=400 * n_cols,
    )

    if output_path:
        fig.write_html(str(output_path))

    return fig


__all__ = [
    "create_heatmap",
    "create_multi_metric_heatmap",
]
