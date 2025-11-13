"""Tests for visualization module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from glitchlings.metrics.core.schema import Observation
from glitchlings.metrics.viz import (
    aggregate_observations,
    compute_percentile_ranks,
    normalize_metrics,
    pivot_for_heatmap,
)


@pytest.fixture
def sample_observations():
    """Create sample observations for testing."""
    observations = []

    glitchlings = ["typogre", "ekkokin"]
    tokenizers = ["gpt2", "bert"]

    for g_idx, glitchling in enumerate(glitchlings):
        for t_idx, tokenizer in enumerate(tokenizers):
            for i in range(10):
                obs = Observation(
                    run_id="test-run",
                    observation_id=f"obs_{g_idx}_{t_idx}_{i}",
                    input_id=f"input_{i}",
                    input_type="test",
                    glitchling_id=glitchling,
                    tokenizer_id=tokenizer,
                    tokens_before=list(range(10 + i)),
                    tokens_after=list(range(10 + i)),
                    m=10 + i,
                    n=10 + i,
                    metrics={
                        "ned.value": 0.1 + (g_idx * 0.2) + (i * 0.01),
                        "lcsr.value": 0.8 - (t_idx * 0.2) - (i * 0.01),
                        "jsdiv.value": 0.3 + (g_idx + t_idx) * 0.1,
                    },
                )
                observations.append(obs)

    return observations


def test_aggregate_observations(sample_observations):
    """Test observation aggregation."""
    result = aggregate_observations(
        sample_observations,
        group_by=["glitchling_id"],
        metrics=["ned.value", "lcsr.value"],
    )

    assert len(result) == 2  # Two glitchlings

    for group in result:
        assert "glitchling_id" in group
        assert "metric_ned.value" in group
        assert "metric_lcsr.value" in group

        # Check statistics
        ned_stats = group["metric_ned.value"]
        assert "mean" in ned_stats
        assert "median" in ned_stats
        assert "std" in ned_stats
        assert "q1" in ned_stats
        assert "q3" in ned_stats

        # Check reasonable values
        assert 0 <= ned_stats["mean"] <= 1
        assert 0 <= ned_stats["median"] <= 1


def test_compute_percentile_ranks(sample_observations):
    """Test percentile rank computation."""
    result = compute_percentile_ranks(
        sample_observations,
        metrics=["ned.value", "lcsr.value"],
    )

    assert len(result) == len(sample_observations)

    for obs_data in result:
        assert "metric_ned.value" in obs_data
        assert "metric_lcsr.value" in obs_data

        # Percentiles should be in [0, 100]
        assert 0 <= obs_data["metric_ned.value"] <= 100
        assert 0 <= obs_data["metric_lcsr.value"] <= 100


def test_normalize_metrics():
    """Test metric normalization."""
    metrics = {"ned.value": 0.5, "lcsr.value": 0.7}

    # Test minmax normalization
    normalized = normalize_metrics(metrics, normalization="minmax")
    assert all(0 <= v <= 1 for v in normalized.values())

    # Test percentile normalization with reference
    reference_stats = {
        "ned.value": {"min": 0.0, "max": 1.0, "mean": 0.5, "std": 0.2},
        "lcsr.value": {"min": 0.0, "max": 1.0, "mean": 0.6, "std": 0.15},
    }

    normalized_perc = normalize_metrics(
        metrics,
        normalization="percentile",
        reference_stats=reference_stats,
    )
    assert all(0 <= v <= 1 for v in normalized_perc.values())

    # Test none normalization (identity)
    normalized_none = normalize_metrics(metrics, normalization="none")
    assert normalized_none == metrics


def test_pivot_for_heatmap(sample_observations):
    """Test pivoting data for heatmap."""
    result = pivot_for_heatmap(
        sample_observations,
        row_key="glitchling_id",
        col_key="tokenizer_id",
        metric="ned.value",
        aggregation="median",
    )

    assert "values" in result
    assert "row_labels" in result
    assert "col_labels" in result

    values = result["values"]
    row_labels = result["row_labels"]
    col_labels = result["col_labels"]

    # Check dimensions
    assert values.shape == (len(row_labels), len(col_labels))

    # Check labels
    assert set(row_labels) == {"typogre", "ekkokin"}
    assert set(col_labels) == {"gpt2", "bert"}

    # Check values are reasonable
    assert np.all((values >= 0) & (values <= 1))


def test_pivot_different_aggregations(sample_observations):
    """Test different aggregation methods."""
    for agg_method in ["mean", "median", "max", "min"]:
        result = pivot_for_heatmap(
            sample_observations,
            row_key="glitchling_id",
            col_key="tokenizer_id",
            metric="ned.value",
            aggregation=agg_method,
        )

        assert result["values"].shape[0] == 2  # Two glitchlings
        assert result["values"].shape[1] == 2  # Two tokenizers


# Visualization function tests (require matplotlib/plotly)

@pytest.mark.skipif(
    not _has_matplotlib(),
    reason="matplotlib not installed",
)
def test_create_radar_chart(sample_observations):
    """Test radar chart creation."""
    from glitchlings.metrics.viz import create_radar_chart

    # Aggregate metrics for one glitchling
    typogre_obs = [obs for obs in sample_observations if obs.glitchling_id == "typogre"]
    agg = aggregate_observations(typogre_obs, group_by=["glitchling_id"])

    metrics = {
        k.replace("metric_", ""): v["mean"]
        for k, v in agg[0].items()
        if k.startswith("metric_")
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "radar.png"
        fig = create_radar_chart(
            metrics,
            backend="matplotlib",
            output_path=output_path,
        )

        assert fig is not None
        assert output_path.exists()


@pytest.mark.skipif(
    not _has_matplotlib(),
    reason="matplotlib not installed",
)
def test_create_heatmap(sample_observations):
    """Test heatmap creation."""
    from glitchlings.metrics.viz import create_heatmap

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "heatmap.png"
        fig = create_heatmap(
            sample_observations,
            metric="ned.value",
            backend="matplotlib",
            output_path=output_path,
        )

        assert fig is not None
        assert output_path.exists()


@pytest.mark.skipif(
    not _has_matplotlib(),
    reason="matplotlib not installed",
)
def test_create_sparklines(sample_observations):
    """Test sparklines creation."""
    from glitchlings.metrics.viz import create_sparklines

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "sparklines.png"
        fig = create_sparklines(
            sample_observations,
            metrics=["ned.value", "lcsr.value"],
            group_by="glitchling_id",
            length_bins=5,
            backend="matplotlib",
            output_path=output_path,
        )

        assert fig is not None
        assert output_path.exists()


def test_config_load_and_render():
    """Test config loading and rendering."""
    from glitchlings.metrics.viz import FigureConfig, render_figure

    # Create config
    config = FigureConfig(
        figure_type="radar",
        title="Test Radar",
        params={"backend": "matplotlib"},
    )

    # Create minimal observations
    observations = [
        Observation(
            run_id="test",
            observation_id=f"obs_{i}",
            input_id=f"input_{i}",
            input_type="test",
            glitchling_id="test_glitch",
            tokenizer_id="test_tok",
            tokens_before=[1, 2, 3],
            tokens_after=[1, 2, 3],
            m=3,
            n=3,
            metrics={"ned.value": 0.5, "lcsr.value": 0.8},
        )
        for i in range(5)
    ]

    # Test config dict conversion
    config_dict = config.to_dict()
    assert config_dict["type"] == "radar"
    assert config_dict["title"] == "Test Radar"

    # Test config from dict
    loaded_config = FigureConfig.from_dict(config_dict)
    assert loaded_config.figure_type == "radar"
    assert loaded_config.title == "Test Radar"


def _has_matplotlib():
    """Check if matplotlib is installed."""
    try:
        import matplotlib
        return True
    except ImportError:
        return False


def _has_plotly():
    """Check if plotly is installed."""
    try:
        import plotly
        return True
    except ImportError:
        return False


def _has_umap():
    """Check if umap-learn is installed."""
    try:
        import umap
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
