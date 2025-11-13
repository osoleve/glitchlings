"""Config-driven visualization rendering.

Allows defining visualizations in YAML format for reproducible figure generation.

Example config:
    figures:
      - type: radar
        title: "Typogre Transformation Fingerprint"
        data_source: "results/run_abc123.parquet"
        filters:
          glitchling_id: "typogre"
        params:
          backend: "matplotlib"
          normalization: "percentile"
          output_path: "figures/typogre_radar.png"

      - type: heatmap
        title: "Edit Distance Across Tokenizers"
        data_source: "results/run_abc123.parquet"
        params:
          metric: "ned.value"
          backend: "plotly"
          output_path: "figures/ned_heatmap.html"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from ..core.schema import Observation
from .aggregate import aggregate_observations
from .embed import create_embedding_plot, create_metric_lens_comparison
from .heatmap import create_heatmap, create_multi_metric_heatmap
from .radar import create_multi_radar_chart, create_radar_chart
from .spark import create_length_sensitivity_plot, create_sparklines


class FigureConfig:
    """Configuration for a single figure.

    Attributes:
        figure_type: Type of figure ("radar", "heatmap", "embedding", "sparklines", "length_sensitivity")
        title: Figure title
        data_source: Path to Parquet file or list of observations
        filters: Dict of attribute filters (e.g., {"glitchling_id": "typogre"})
        params: Dict of type-specific parameters
    """

    def __init__(
        self,
        figure_type: str,
        title: str | None = None,
        data_source: str | Path | Sequence[Observation] | None = None,
        filters: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ):
        """Initialize figure config.

        Args:
            figure_type: Type of visualization
            title: Figure title
            data_source: Path to data or observations
            filters: Attribute filters for data
            params: Type-specific parameters
        """
        self.figure_type = figure_type
        self.title = title
        self.data_source = data_source
        self.filters = filters or {}
        self.params = params or {}

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> FigureConfig:
        """Create config from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            FigureConfig instance
        """
        return cls(
            figure_type=config_dict["type"],
            title=config_dict.get("title"),
            data_source=config_dict.get("data_source"),
            filters=config_dict.get("filters"),
            params=config_dict.get("params"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Configuration as dict
        """
        return {
            "type": self.figure_type,
            "title": self.title,
            "data_source": str(self.data_source) if self.data_source else None,
            "filters": self.filters,
            "params": self.params,
        }


def load_config_yaml(config_path: str | Path) -> list[FigureConfig]:
    """Load figure configurations from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        List of FigureConfig objects

    Raises:
        ImportError: If PyYAML not installed
        ValueError: If config is invalid

    Example:
        >>> configs = load_config_yaml("viz_config.yaml")
        >>> for config in configs:
        ...     render_figure(config, observations)
    """
    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML required for YAML config loading. "
            "Install with: pip install pyyaml"
        ) from e

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if "figures" not in data:
        raise ValueError("Config must contain 'figures' key")

    return [FigureConfig.from_dict(fig) for fig in data["figures"]]


def load_config_json(config_path: str | Path) -> list[FigureConfig]:
    """Load figure configurations from JSON file.

    Args:
        config_path: Path to JSON config file

    Returns:
        List of FigureConfig objects
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = json.load(f)

    if "figures" not in data:
        raise ValueError("Config must contain 'figures' key")

    return [FigureConfig.from_dict(fig) for fig in data["figures"]]


def load_observations_from_parquet(
    parquet_path: str | Path, filters: dict[str, Any] | None = None
) -> list[Observation]:
    """Load observations from Parquet file with optional filtering.

    Args:
        parquet_path: Path to Parquet file
        filters: Dict of attribute filters

    Returns:
        List of Observation objects

    Raises:
        ImportError: If pandas/pyarrow not installed
    """
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError(
            "pandas required for Parquet loading. "
            "Install with: pip install 'glitchlings[metrics]'"
        ) from e

    # Load Parquet
    df = pd.read_parquet(parquet_path)

    # Apply filters
    if filters:
        for key, value in filters.items():
            if key in df.columns:
                if isinstance(value, list):
                    df = df[df[key].isin(value)]
                else:
                    df = df[df[key] == value]

    # Convert to Observation objects
    observations = []
    for _, row in df.iterrows():
        # Extract metrics (columns starting with "metric_")
        metrics = {
            col.replace("metric_", ""): row[col]
            for col in df.columns
            if col.startswith("metric_")
        }

        # Extract context (columns starting with "context_")
        context = {
            col.replace("context_", ""): row[col]
            for col in df.columns
            if col.startswith("context_")
        }

        # Create observation
        obs = Observation(
            run_id=row.get("run_id", "unknown"),
            observation_id=row.get("observation_id", "unknown"),
            input_id=row.get("input_id", "unknown"),
            input_type=row.get("input_type", "default"),
            glitchling_id=row.get("glitchling_id", "unknown"),
            tokenizer_id=row.get("tokenizer_id", "unknown"),
            gaggle_id=row.get("gaggle_id"),
            tokens_before=[],  # Not stored in Parquet by default
            tokens_after=[],
            m=int(row.get("m", 0)),
            n=int(row.get("n", 0)),
            metrics=metrics,
            tokens_before_hash=row.get("tokens_before_hash"),
            tokens_after_hash=row.get("tokens_after_hash"),
            text_before=row.get("text_before"),
            text_after=row.get("text_after"),
            context=context,
        )
        observations.append(obs)

    return observations


def render_figure(
    config: FigureConfig,
    observations: Sequence[Observation] | None = None,
) -> Any:
    """Render a figure from configuration.

    Args:
        config: Figure configuration
        observations: Observations to visualize (if not loading from data_source)

    Returns:
        Figure object

    Raises:
        ValueError: If figure type is unknown or data is missing

    Example:
        >>> config = FigureConfig(
        ...     figure_type="radar",
        ...     title="My Glitchling",
        ...     filters={"glitchling_id": "typogre"},
        ...     params={"backend": "matplotlib"}
        ... )
        >>> fig = render_figure(config, observations)
    """
    # Load data if needed
    if observations is None:
        if config.data_source is None:
            raise ValueError("Must provide either observations or data_source")

        # Load from Parquet
        observations = load_observations_from_parquet(
            config.data_source, config.filters
        )
    else:
        # Apply filters to provided observations
        if config.filters:
            observations = _apply_filters(observations, config.filters)

    if not observations:
        raise ValueError("No observations remain after filtering")

    # Render based on type
    if config.figure_type == "radar":
        return _render_radar(observations, config.title, config.params)
    elif config.figure_type == "heatmap":
        return _render_heatmap(observations, config.title, config.params)
    elif config.figure_type == "embedding":
        return _render_embedding(observations, config.title, config.params)
    elif config.figure_type == "sparklines":
        return _render_sparklines(observations, config.title, config.params)
    elif config.figure_type == "length_sensitivity":
        return _render_length_sensitivity(observations, config.title, config.params)
    elif config.figure_type == "multi_metric_heatmap":
        return _render_multi_metric_heatmap(observations, config.title, config.params)
    elif config.figure_type == "metric_lens":
        return _render_metric_lens(observations, config.title, config.params)
    else:
        raise ValueError(f"Unknown figure type: {config.figure_type}")


def _apply_filters(
    observations: Sequence[Observation], filters: dict[str, Any]
) -> list[Observation]:
    """Apply filters to observations."""
    filtered = []
    for obs in observations:
        match = True
        for key, value in filters.items():
            obs_value = getattr(obs, key, None)
            if isinstance(value, list):
                if obs_value not in value:
                    match = False
                    break
            else:
                if obs_value != value:
                    match = False
                    break
        if match:
            filtered.append(obs)
    return filtered


def _render_radar(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render radar chart."""
    # Check if single or multi-glitchling
    glitchling_ids = list(set(obs.glitchling_id for obs in observations))

    if len(glitchling_ids) == 1:
        # Single radar
        # Aggregate metrics for this glitchling
        agg = aggregate_observations(observations, group_by=["glitchling_id"])
        if agg:
            glitchling_metrics = {
                k.replace("metric_", ""): v["mean"]
                for k, v in agg[0].items()
                if k.startswith("metric_")
            }
            return create_radar_chart(glitchling_metrics, title=title, **params)
    else:
        # Multi-glitchling radar
        glitchling_data = {}
        for g_id in glitchling_ids:
            g_obs = [obs for obs in observations if obs.glitchling_id == g_id]
            agg = aggregate_observations(g_obs, group_by=["glitchling_id"])
            if agg:
                glitchling_data[g_id] = {
                    k.replace("metric_", ""): v["mean"]
                    for k, v in agg[0].items()
                    if k.startswith("metric_")
                }
        return create_multi_radar_chart(glitchling_data, title=title, **params)

    raise ValueError("Could not aggregate metrics for radar chart")


def _render_heatmap(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render heatmap."""
    return create_heatmap(observations, title=title, **params)


def _render_embedding(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render embedding plot."""
    return create_embedding_plot(observations, title=title, **params)


def _render_sparklines(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render sparklines."""
    return create_sparklines(observations, title=title, **params)


def _render_length_sensitivity(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render length sensitivity plot."""
    return create_length_sensitivity_plot(observations, title=title, **params)


def _render_multi_metric_heatmap(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render multi-metric heatmap."""
    return create_multi_metric_heatmap(observations, title=title, **params)


def _render_metric_lens(
    observations: Sequence[Observation], title: str | None, params: dict[str, Any]
) -> Any:
    """Render metric lens comparison."""
    return create_metric_lens_comparison(observations, title=title, **params)


def render_config_file(
    config_path: str | Path,
    observations: Sequence[Observation] | None = None,
) -> list[Any]:
    """Render all figures from a config file.

    Args:
        config_path: Path to YAML or JSON config file
        observations: Optional observations (if not loading from data_source)

    Returns:
        List of figure objects

    Example:
        >>> # Render all figures defined in config
        >>> figures = render_config_file("viz_config.yaml")
        >>> # Figures are saved according to output_path in config
    """
    config_path = Path(config_path)

    # Load config based on extension
    if config_path.suffix in [".yaml", ".yml"]:
        configs = load_config_yaml(config_path)
    elif config_path.suffix == ".json":
        configs = load_config_json(config_path)
    else:
        raise ValueError(
            f"Unknown config format: {config_path.suffix}. Use .yaml or .json"
        )

    # Render each figure
    figures = []
    for config in configs:
        try:
            fig = render_figure(config, observations)
            figures.append(fig)
            print(f"✓ Rendered {config.figure_type}: {config.title or '(untitled)'}")
        except Exception as e:
            print(f"✗ Failed to render {config.figure_type}: {e}")

    return figures


__all__ = [
    "FigureConfig",
    "load_config_yaml",
    "load_config_json",
    "load_observations_from_parquet",
    "render_figure",
    "render_config_file",
]
