"""Utility functions for metrics calculation and formatting."""

import statistics
from typing import Sequence


def calculate_stats(values: Sequence[float | int]) -> tuple[float, float]:
    """
    Calculate mean and standard deviation for a sequence of values.

    Args:
        values: Sequence of numeric values

    Returns:
        Tuple of (mean, std). If only one value, std is 0.0.
        If no values, returns (0.0, 0.0).
    """
    if not values:
        return 0.0, 0.0

    numbers = [float(v) for v in values]
    mean = statistics.mean(numbers)
    std = statistics.stdev(numbers) if len(numbers) > 1 else 0.0

    return mean, std


def format_metric(mean: float, std: float | None = None, decimals: int = 4) -> str:
    """
    Format a metric value with optional standard deviation.

    Args:
        mean: The mean value
        std: Optional standard deviation. If None, only mean is formatted.
        decimals: Number of decimal places

    Returns:
        Formatted string like "1.2345" or "1.2345 ± 0.1234"
    """
    if std is None or std == 0.0:
        return f"{mean:.{decimals}f}"
    return f"{mean:.{decimals}f} ± {std:.{decimals}f}"


def format_token_delta(mean: float, std: float | None = None, decimals: int = 1) -> str:
    """
    Format token delta metric with appropriate sign prefix.

    Args:
        mean: The mean token delta value
        std: Optional standard deviation
        decimals: Number of decimal places

    Returns:
        Formatted string like "+5.2" or "+5.2 ± 1.3"
    """
    sign = "+" if mean > 0 else ""
    if std is None or std == 0.0:
        return f"{sign}{mean:.{decimals}f}"
    return f"{sign}{mean:.{decimals}f} ± {std:.{decimals}f}"


def format_stats_display(values: Sequence[float | int], decimals: int = 3) -> str:
    """
    Format statistics for display (convenience wrapper for calculate_stats + format_metric).

    Args:
        values: Sequence of numeric values
        decimals: Number of decimal places

    Returns:
        Formatted string like "1.234 +/- 0.123" or "-" if no values
    """
    if not values:
        return "-"

    mean, std = calculate_stats(values)

    if len(values) == 1:
        return f"{mean:.{decimals}f}"

    return f"{mean:.{decimals}f} +/- {std:.{decimals}f}"
