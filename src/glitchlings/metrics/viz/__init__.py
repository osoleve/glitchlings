"""Visualization module for glitchling metrics.

Provides:
- Radar charts (transformation fingerprints)
- Heatmaps (glitchling × tokenizer grids)
- Embeddings (UMAP/t-SNE projections)
- Sparklines (metric trends by length)
- Config-driven rendering

Install visualization dependencies with:
    pip install glitchlings[metrics-viz]
"""

from .aggregate import (
    aggregate_observations,
    compute_percentile_ranks,
    normalize_metrics,
    pivot_for_heatmap,
)
from .config import (
    FigureConfig,
    load_config_json,
    load_config_yaml,
    render_config_file,
    render_figure,
)
from .embed import create_embedding_plot, create_metric_lens_comparison
from .heatmap import create_heatmap, create_multi_metric_heatmap
from .radar import create_multi_radar_chart, create_radar_chart
from .spark import create_length_sensitivity_plot, create_sparklines

__all__ = [
    # Aggregation utilities
    "aggregate_observations",
    "compute_percentile_ranks",
    "normalize_metrics",
    "pivot_for_heatmap",
    # Radar charts
    "create_radar_chart",
    "create_multi_radar_chart",
    # Heatmaps
    "create_heatmap",
    "create_multi_metric_heatmap",
    # Embeddings
    "create_embedding_plot",
    "create_metric_lens_comparison",
    # Sparklines
    "create_sparklines",
    "create_length_sensitivity_plot",
    # Config-driven rendering
    "FigureConfig",
    "render_figure",
    "render_config_file",
    "load_config_yaml",
    "load_config_json",
]
