"""Aggregation utilities for metrics visualization.

Provides functions for computing summary statistics and preparing data
for visualization.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence, Union

import numpy as np

from ..core.schema import Observation


def _get_attr(obs: Union[dict, Observation], key: str) -> Any:
    """Get attribute from observation (dict or Observation object)."""
    if isinstance(obs, dict):
        return obs[key]
    return getattr(obs, key)


def _get_metric(obs: Union[dict, Observation], metric_key: str) -> float:
    """Get metric value from observation."""
    if isinstance(obs, dict):
        return obs[metric_key]
    # For Observation objects, metrics are in the metrics dict
    # Strip "metric_" prefix if present
    clean_key = metric_key.replace("metric_", "")
    return obs.metrics[clean_key]


def aggregate_observations(
    observations: Iterable[Union[dict[str, Any], Observation]],
    group_by: Sequence[str],
    metrics: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate observations by grouping keys.

    Args:
        observations: Iterable of observation dicts or Observation objects
        group_by: Keys to group by (e.g., ["glitchling_id", "tokenizer_id"])
        metrics: Metric keys to aggregate (None = all metrics from Observation.metrics)

    Returns:
        List of dicts with group keys and aggregated metrics

    Example:
        >>> obs = [
        ...     {"glitchling_id": "g1", "tokenizer_id": "t1", "metric_ned.value": 0.5},
        ...     {"glitchling_id": "g1", "tokenizer_id": "t1", "metric_ned.value": 0.6},
        ... ]
        >>> result = aggregate_observations(obs, ["glitchling_id"], ["metric_ned.value"])
        >>> result[0]["metric_ned.value"]["median"]
        0.55
    """
    # Group observations
    groups: dict[tuple, list] = defaultdict(list)

    for obs in observations:
        key = tuple(_get_attr(obs, k) for k in group_by)
        groups[key].append(obs)

    # Aggregate each group
    results = []

    for group_key, group_obs in groups.items():
        group_result = dict(zip(group_by, group_key))
        group_result["count"] = len(group_obs)

        # Identify metrics to aggregate
        if metrics is None:
            # Find all metrics from first Observation
            sample = group_obs[0]
            if isinstance(sample, dict):
                metric_keys = [k for k in sample.keys() if k.startswith("metric_")]
            else:
                # For Observation objects, get from metrics dict
                metric_keys = [f"metric_{k}" for k in sample.metrics.keys()]
        else:
            metric_keys = list(metrics)

        # Compute stats for each metric
        for metric in metric_keys:
            try:
                values = [
                    _get_metric(obs, metric)
                    for obs in group_obs
                ]
                values = [v for v in values if v is not None and np.isfinite(v)]

                if not values:
                    continue

                values_arr = np.array(values, dtype=float)

                group_result[metric] = {
                    "mean": float(np.mean(values_arr)),
                    "median": float(np.median(values_arr)),
                    "std": float(np.std(values_arr)),
                    "min": float(np.min(values_arr)),
                    "max": float(np.max(values_arr)),
                    "q1": float(np.percentile(values_arr, 25)),
                    "q3": float(np.percentile(values_arr, 75)),
                    "iqr": float(np.percentile(values_arr, 75) - np.percentile(values_arr, 25)),
                    "n": len(values_arr),
                }
            except (KeyError, AttributeError):
                # Metric not found in this observation
                continue

        results.append(group_result)

    return results


def compute_percentile_ranks(
    observations: Iterable[dict[str, Any]], metrics: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Compute percentile ranks for metrics across all observations.

    Args:
        observations: Iterable of observation dicts
        metrics: Metric keys to rank

    Returns:
        Dict mapping observation_id to {metric: percentile_rank}

    Note:
        Percentile ranks are in [0, 100], useful for radar chart normalization.

    Example:
        >>> obs = [
        ...     {"observation_id": "o1", "metric_ned.value": 0.1},
        ...     {"observation_id": "o2", "metric_ned.value": 0.5},
        ...     {"observation_id": "o3", "metric_ned.value": 0.9},
        ... ]
        >>> ranks = compute_percentile_ranks(obs, ["metric_ned.value"])
        >>> ranks["o2"]["metric_ned.value"]  # Middle value = 50th percentile
        50.0
    """
    obs_list = list(observations)

    # Collect all values per metric
    metric_values: dict[str, list[float]] = {m: [] for m in metrics}

    for obs in obs_list:
        for metric in metrics:
            val = obs.get(metric)
            if val is not None:
                metric_values[metric].append(val)

    # Compute percentile ranks
    ranks = {}

    for obs in obs_list:
        obs_id = obs.get("observation_id", obs.get("input_id", "unknown"))
        obs_ranks = {}

        for metric in metrics:
            val = obs.get(metric)
            if val is None:
                continue

            # Compute percentile rank
            all_vals = metric_values[metric]
            if len(all_vals) > 0:
                percentile = (np.searchsorted(np.sort(all_vals), val) / len(all_vals)) * 100
                obs_ranks[metric] = float(percentile)

        ranks[obs_id] = obs_ranks

    return ranks


def normalize_metrics(
    values: dict[str, float],
    normalization: str = "minmax",
    reference_stats: dict[str, dict[str, float]] | None = None,
) -> dict[str, float]:
    """Normalize metric values for visualization.

    Args:
        values: Dict of metric values
        normalization: Method ("minmax", "zscore", "percentile", "none")
        reference_stats: Reference statistics for normalization

    Returns:
        Dict of normalized values in [0, 1] (for minmax/percentile)

    Example:
        >>> values = {"metric_ned.value": 0.5, "metric_lcsr.value": 0.8}
        >>> stats = {
        ...     "metric_ned.value": {"min": 0.0, "max": 1.0},
        ...     "metric_lcsr.value": {"min": 0.0, "max": 1.0}
        ... }
        >>> normalize_metrics(values, "minmax", stats)
        {"metric_ned.value": 0.5, "metric_lcsr.value": 0.8}
    """
    if normalization == "none":
        return values.copy()

    normalized = {}

    for metric, value in values.items():
        if normalization == "minmax":
            if reference_stats and metric in reference_stats:
                min_val = reference_stats[metric].get("min", 0.0)
                max_val = reference_stats[metric].get("max", 1.0)
                range_val = max_val - min_val

                if range_val > 0:
                    normalized[metric] = (value - min_val) / range_val
                else:
                    normalized[metric] = 0.5  # Constant metric
            else:
                # Assume already in [0, 1]
                normalized[metric] = value

        elif normalization == "zscore":
            if reference_stats and metric in reference_stats:
                mean = reference_stats[metric].get("mean", 0.0)
                std = reference_stats[metric].get("std", 1.0)

                if std > 0:
                    z = (value - mean) / std
                    # Map to [0, 1] using sigmoid
                    normalized[metric] = 1 / (1 + np.exp(-z))
                else:
                    normalized[metric] = 0.5
            else:
                normalized[metric] = value

        elif normalization == "percentile":
            # Requires pre-computed percentile ranks
            normalized[metric] = value / 100.0  # Assume value is percentile

        else:
            raise ValueError(f"Unknown normalization method: {normalization}")

    return normalized


def pivot_for_heatmap(
    observations: Iterable[Union[dict[str, Any], Observation]],
    row_key: str,
    col_key: str,
    metric: str,
    aggregation: str = "median",
) -> dict[str, Any]:
    """Pivot observations into a 2D array for heatmap visualization.

    Args:
        observations: Iterable of observation dicts or Observation objects
        row_key: Key for rows (e.g., "glitchling_id")
        col_key: Key for columns (e.g., "tokenizer_id")
        metric: Metric to visualize
        aggregation: Aggregation method ("median", "mean", "max", etc.)

    Returns:
        Dict with "row_labels", "col_labels", and "values" (2D numpy array)

    Example:
        >>> obs = [
        ...     {"glitchling_id": "g1", "tokenizer_id": "t1", "metric_ned.value": 0.5},
        ...     {"glitchling_id": "g1", "tokenizer_id": "t2", "metric_ned.value": 0.6},
        ... ]
        >>> result = pivot_for_heatmap(
        ...     obs, "glitchling_id", "tokenizer_id", "metric_ned.value"
        ... )
        >>> result["values"].shape
        (1, 2)
    """
    # Group by (row, col)
    grouped = aggregate_observations(observations, [row_key, col_key], [metric])

    # Extract unique row/col labels
    rows = sorted({result[row_key] for result in grouped})
    cols = sorted({result[col_key] for result in grouped})

    # Build matrix
    matrix = np.full((len(rows), len(cols)), np.nan)

    for result in grouped:
        row_val = result[row_key]
        col_val = result[col_key]
        if metric in result:
            row_idx = rows.index(row_val)
            col_idx = cols.index(col_val)
            matrix[row_idx, col_idx] = result[metric].get(aggregation, np.nan)

    return {
        "row_labels": rows,
        "col_labels": cols,
        "values": matrix,
    }


__all__ = [
    "aggregate_observations",
    "compute_percentile_ranks",
    "normalize_metrics",
    "pivot_for_heatmap",
]
