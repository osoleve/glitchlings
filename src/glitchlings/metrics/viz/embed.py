"""Embedding visualization for exploring metric space.

Projects high-dimensional metric vectors into 2D using UMAP or t-SNE,
revealing clusters and patterns in glitchling behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..core.schema import Observation


def create_embedding_plot(
    observations: Sequence[Observation],
    metrics: Sequence[str] | None = None,
    metric_weights: dict[str, float] | None = None,
    method: str = "umap",
    color_by: str = "glitchling_id",
    title: str | None = None,
    backend: str = "plotly",
    output_path: str | Path | None = None,
    **embedding_kwargs: Any,
) -> Any:
    """Create 2D embedding visualization of metric space.

    Args:
        observations: Sequence of observations to embed
        metrics: Metric IDs to include (None = all metrics)
        metric_weights: Optional weights for metrics (e.g., {"ned.value": 2.0})
        method: Embedding method ("umap" or "tsne")
        color_by: Observation attribute for coloring points
        title: Chart title
        backend: Visualization backend ("matplotlib" or "plotly")
        output_path: Path to save figure
        **embedding_kwargs: Additional kwargs for UMAP/t-SNE
            - n_neighbors (UMAP): default 15
            - min_dist (UMAP): default 0.1
            - perplexity (t-SNE): default 30
            - random_state: default 42

    Returns:
        Figure object (matplotlib.Figure or plotly.Figure)

    Example:
        >>> # Basic embedding colored by glitchling
        >>> fig = create_embedding_plot(
        ...     observations,
        ...     method="umap",
        ...     color_by="glitchling_id",
        ...     title="Glitchling Behavior Space"
        ... )
        >>>
        >>> # Focus on edit distance metrics
        >>> fig = create_embedding_plot(
        ...     observations,
        ...     metrics=["ned.value", "lcsr.value", "pmr.value"],
        ...     metric_weights={"ned.value": 2.0},  # Emphasize NED
        ...     method="umap",
        ...     n_neighbors=10,  # Tighter clusters
        ... )
    """
    # Extract metric vectors
    metric_matrix, metric_names, valid_obs = _prepare_metric_matrix(
        observations, metrics, metric_weights
    )

    if len(valid_obs) < 2:
        raise ValueError("Need at least 2 observations for embedding")

    # Compute embedding
    embedding = _compute_embedding(metric_matrix, method, embedding_kwargs)

    # Extract color labels
    color_labels = [str(getattr(obs, color_by, "unknown")) for obs in valid_obs]

    # Plot
    if backend == "matplotlib":
        return _plot_embedding_matplotlib(
            embedding,
            color_labels,
            valid_obs,
            color_by,
            title or f"{method.upper()} Embedding of Metric Space",
            output_path,
        )
    elif backend == "plotly":
        return _plot_embedding_plotly(
            embedding,
            color_labels,
            valid_obs,
            color_by,
            metric_names,
            title or f"{method.upper()} Embedding of Metric Space",
            output_path,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _prepare_metric_matrix(
    observations: Sequence[Observation],
    metrics: Sequence[str] | None,
    metric_weights: dict[str, float] | None,
) -> tuple[np.ndarray, list[str], list[Observation]]:
    """Extract metric matrix from observations.

    Returns:
        Tuple of (metric_matrix, metric_names, valid_observations)
    """
    # Get all metric names if not specified
    if metrics is None:
        all_metrics = set()
        for obs in observations:
            all_metrics.update(obs.metrics.keys())
        metrics = sorted(all_metrics)

    # Filter observations with all required metrics
    valid_obs = []
    rows = []

    for obs in observations:
        # Check if observation has all required metrics
        if all(m in obs.metrics for m in metrics):
            row = [obs.metrics[m] for m in metrics]

            # Apply weights if provided
            if metric_weights:
                row = [
                    val * metric_weights.get(m, 1.0)
                    for val, m in zip(row, metrics)
                ]

            rows.append(row)
            valid_obs.append(obs)

    if not rows:
        raise ValueError("No observations contain all required metrics")

    metric_matrix = np.array(rows)

    # Remove any NaN or inf values
    if np.any(~np.isfinite(metric_matrix)):
        raise ValueError("Metric matrix contains NaN or inf values")

    return metric_matrix, list(metrics), valid_obs


def _compute_embedding(
    metric_matrix: np.ndarray,
    method: str,
    kwargs: dict[str, Any],
) -> np.ndarray:
    """Compute 2D embedding using UMAP or t-SNE.

    Args:
        metric_matrix: (n_observations, n_metrics) array
        method: "umap" or "tsne"
        kwargs: Embedding parameters

    Returns:
        (n_observations, 2) array of 2D coordinates
    """
    if method == "umap":
        try:
            import umap
        except ImportError as e:
            raise ImportError(
                "umap-learn required for UMAP embeddings. "
                "Install with: pip install umap-learn"
            ) from e

        # Default UMAP parameters
        n_neighbors = kwargs.get("n_neighbors", 15)
        min_dist = kwargs.get("min_dist", 0.1)
        random_state = kwargs.get("random_state", 42)

        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=2,
            random_state=random_state,
            metric="euclidean",
        )

        embedding = reducer.fit_transform(metric_matrix)

    elif method == "tsne":
        try:
            from sklearn.manifold import TSNE
        except ImportError as e:
            raise ImportError(
                "scikit-learn required for t-SNE embeddings. "
                "Install with: pip install scikit-learn"
            ) from e

        # Default t-SNE parameters
        perplexity = kwargs.get("perplexity", 30)
        random_state = kwargs.get("random_state", 42)

        # Adjust perplexity if too few samples
        n_samples = metric_matrix.shape[0]
        perplexity = min(perplexity, (n_samples - 1) // 3)

        reducer = TSNE(
            n_components=2,
            perplexity=perplexity,
            random_state=random_state,
            metric="euclidean",
        )

        embedding = reducer.fit_transform(metric_matrix)

    else:
        raise ValueError(f"Unknown method: {method}. Use 'umap' or 'tsne'")

    return embedding


def _plot_embedding_matplotlib(
    embedding: np.ndarray,
    color_labels: list[str],
    observations: list[Observation],
    color_by: str,
    title: str,
    output_path: str | Path | None,
):
    """Plot embedding using matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    # Get unique labels and assign colors
    unique_labels = sorted(set(color_labels))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
    label_to_color = dict(zip(unique_labels, colors))

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot each group
    for label in unique_labels:
        mask = np.array([lbl == label for lbl in color_labels])
        ax.scatter(
            embedding[mask, 0],
            embedding[mask, 1],
            c=[label_to_color[label]],
            label=label,
            alpha=0.7,
            s=50,
            edgecolors="white",
            linewidth=0.5,
        )

    ax.set_xlabel("Dimension 1", fontsize=11)
    ax.set_ylabel("Dimension 2", fontsize=11)
    ax.set_title(title, fontsize=13, pad=15)
    ax.legend(title=color_by.replace("_", " ").title(), bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _plot_embedding_plotly(
    embedding: np.ndarray,
    color_labels: list[str],
    observations: list[Observation],
    color_by: str,
    metric_names: list[str],
    title: str,
    output_path: str | Path | None,
):
    """Plot embedding using plotly with interactive hover."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError("plotly required") from e

    # Build hover text with observation details
    hover_texts = []
    for obs in observations:
        lines = [
            f"<b>{color_by}:</b> {getattr(obs, color_by, 'N/A')}",
            f"<b>Input ID:</b> {obs.input_id}",
            f"<b>Tokenizer:</b> {obs.tokenizer_id}",
            "<br><b>Metrics:</b>",
        ]
        for metric in metric_names[:5]:  # Show first 5 metrics
            value = obs.metrics.get(metric, np.nan)
            metric_short = metric.replace("metric_", "").replace(".value", "")
            lines.append(f"  {metric_short}: {value:.3f}")
        if len(metric_names) > 5:
            lines.append(f"  ... ({len(metric_names) - 5} more)")
        hover_texts.append("<br>".join(lines))

    # Create scatter plot
    fig = go.Figure()

    # Plot each group
    unique_labels = sorted(set(color_labels))
    for label in unique_labels:
        mask = np.array([lbl == label for lbl in color_labels])
        indices = np.where(mask)[0]

        fig.add_trace(
            go.Scatter(
                x=embedding[mask, 0],
                y=embedding[mask, 1],
                mode="markers",
                name=label,
                text=[hover_texts[i] for i in indices],
                hovertemplate="%{text}<extra></extra>",
                marker=dict(size=8, opacity=0.7, line=dict(width=0.5, color="white")),
            )
        )

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title="Dimension 1",
        yaxis_title="Dimension 2",
        width=900,
        height=700,
        hovermode="closest",
        legend_title=color_by.replace("_", " ").title(),
    )

    if output_path:
        fig.write_html(str(output_path))

    return fig


def create_metric_lens_comparison(
    observations: Sequence[Observation],
    metric_lenses: dict[str, Sequence[str]],
    method: str = "umap",
    color_by: str = "glitchling_id",
    title: str | None = None,
    backend: str = "plotly",
    output_path: str | Path | None = None,
) -> Any:
    """Create side-by-side embeddings with different metric lenses.

    A "metric lens" is a selection of metrics that emphasizes different
    aspects of glitchling behavior. This function creates multiple embeddings,
    each focusing on a different lens.

    Args:
        observations: Sequence of observations
        metric_lenses: Dict mapping lens name to list of metric IDs
            Example: {
                "Edit Distance": ["ned.value", "lcsr.value"],
                "Distribution": ["jsdiv.value", "cosdist.value"],
                "Structure": ["rord.value", "spi.value"],
            }
        method: Embedding method
        color_by: Observation attribute for coloring
        title: Overall title
        backend: Visualization backend
        output_path: Path to save figure

    Returns:
        Figure object

    Example:
        >>> lenses = {
        ...     "Edit-focused": ["ned.value", "lcsr.value", "pmr.value"],
        ...     "Distribution-focused": ["jsdiv.value", "cosdist.value"],
        ...     "Structure-focused": ["rord.value", "spi.value", "msi.value"],
        ... }
        >>> fig = create_metric_lens_comparison(
        ...     observations,
        ...     metric_lenses=lenses,
        ...     title="Different Views of Glitchling Space"
        ... )
    """
    if backend == "matplotlib":
        return _create_lens_comparison_matplotlib(
            observations, metric_lenses, method, color_by, title, output_path
        )
    elif backend == "plotly":
        return _create_lens_comparison_plotly(
            observations, metric_lenses, method, color_by, title, output_path
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _create_lens_comparison_matplotlib(
    observations: Sequence[Observation],
    metric_lenses: dict[str, Sequence[str]],
    method: str,
    color_by: str,
    title: str | None,
    output_path: str | Path | None,
):
    """Create lens comparison using matplotlib subplots."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e

    n_lenses = len(metric_lenses)
    n_cols = min(3, n_lenses)
    n_rows = (n_lenses + n_cols - 1) // n_cols

    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows), squeeze=False
    )

    for idx, (lens_name, metrics) in enumerate(metric_lenses.items()):
        row_idx = idx // n_cols
        col_idx = idx % n_cols
        ax = axes[row_idx, col_idx]

        try:
            # Compute embedding for this lens
            metric_matrix, _, valid_obs = _prepare_metric_matrix(
                observations, metrics, None
            )
            embedding = _compute_embedding(metric_matrix, method, {"random_state": 42})

            # Extract colors
            color_labels = [str(getattr(obs, color_by, "unknown")) for obs in valid_obs]
            unique_labels = sorted(set(color_labels))
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
            label_to_color = dict(zip(unique_labels, colors))

            # Plot
            for label in unique_labels:
                mask = np.array([lbl == label for lbl in color_labels])
                ax.scatter(
                    embedding[mask, 0],
                    embedding[mask, 1],
                    c=[label_to_color[label]],
                    label=label,
                    alpha=0.7,
                    s=40,
                    edgecolors="white",
                    linewidth=0.5,
                )

            ax.set_title(lens_name, fontsize=11, fontweight="bold")
            ax.set_xlabel("Dim 1", fontsize=9)
            ax.set_ylabel("Dim 2", fontsize=9)
            ax.grid(True, alpha=0.3)

            if idx == 0:
                ax.legend(fontsize=8, loc="best")

        except (ValueError, ImportError) as e:
            ax.text(0.5, 0.5, f"Error: {str(e)}", ha="center", va="center", wrap=True)
            ax.set_title(lens_name, fontsize=11)

    # Hide unused subplots
    for idx in range(n_lenses, n_rows * n_cols):
        row_idx = idx // n_cols
        col_idx = idx % n_cols
        axes[row_idx, col_idx].axis("off")

    if title:
        fig.suptitle(title, fontsize=14, y=0.995)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig


def _create_lens_comparison_plotly(
    observations: Sequence[Observation],
    metric_lenses: dict[str, Sequence[str]],
    method: str,
    color_by: str,
    title: str | None,
    output_path: str | Path | None,
):
    """Create lens comparison using plotly subplots."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as e:
        raise ImportError("plotly required") from e

    n_lenses = len(metric_lenses)
    n_cols = min(3, n_lenses)
    n_rows = (n_lenses + n_cols - 1) // n_cols

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=list(metric_lenses.keys()),
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    for idx, (lens_name, metrics) in enumerate(metric_lenses.items()):
        row_idx = idx // n_cols + 1
        col_idx = idx % n_cols + 1

        try:
            # Compute embedding
            metric_matrix, _, valid_obs = _prepare_metric_matrix(
                observations, metrics, None
            )
            embedding = _compute_embedding(metric_matrix, method, {"random_state": 42})

            # Extract colors
            color_labels = [str(getattr(obs, color_by, "unknown")) for obs in valid_obs]
            unique_labels = sorted(set(color_labels))

            # Add traces
            for label in unique_labels:
                mask = np.array([lbl == label for lbl in color_labels])
                fig.add_trace(
                    go.Scatter(
                        x=embedding[mask, 0],
                        y=embedding[mask, 1],
                        mode="markers",
                        name=label,
                        legendgroup=label,
                        showlegend=(idx == 0),  # Only show legend for first subplot
                        marker=dict(size=6, opacity=0.7),
                        hovertemplate=f"{label}<extra></extra>",
                    ),
                    row=row_idx,
                    col=col_idx,
                )

        except (ValueError, ImportError):
            # Skip this lens if it fails
            pass

    fig.update_layout(
        title=title or "Metric Lens Comparison",
        height=400 * n_rows,
        width=400 * n_cols,
    )

    if output_path:
        fig.write_html(str(output_path))

    return fig


__all__ = [
    "create_embedding_plot",
    "create_metric_lens_comparison",
]
