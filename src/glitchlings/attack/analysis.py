"""Analysis tools for comparing tokenizers and exploring parameter spaces.

This module provides three analysis tools following the functional purity
architecture:

1. **SeedSweep**: Run an attack across many seeds to collect aggregate metrics
2. **GridSearch**: Search across parameter combinations to find optimal settings
3. **TokenizerComparison**: Compare token streams and metrics across tokenizers

Module Structure
----------------
**Pure Functions** (no side effects):
- ``compute_aggregate_stats()``: Statistical aggregation
- ``format_stats_summary()``: String formatting
- ``extract_scalar_metrics()``: Metric extraction
- ``generate_param_combinations()``: Grid generation
- ``rank_grid_points()``: Sorting by metric

**Pure Data Classes** (immutable results):
- ``SeedSweepResult``, ``GridSearchResult``, ``TokenizerComparisonResult``
- ``GridSearchPoint``, ``TokenizerComparisonEntry``

**Impure Orchestrators** (coordinate execution):
- ``SeedSweep``, ``GridSearch``, ``TokenizerComparison``

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import TYPE_CHECKING, Any, Callable

from .core import Attack, AttackResult
from .core_execution import resolve_glitchlings
from .encode import describe_tokenizer
from .tokenization import Tokenizer, resolve_tokenizer

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..protocols import Corruptor


# ---------------------------------------------------------------------------
# Pure Statistical Helpers
# ---------------------------------------------------------------------------


def compute_aggregate_stats(values: Sequence[float]) -> dict[str, float]:
    """Compute aggregate statistics for a sequence of values (pure).

    Args:
        values: Sequence of float values to aggregate.

    Returns:
        Dictionary with mean, std, min, max, and median.
    """
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}

    values_list = list(values)
    mean = statistics.mean(values_list)
    std = statistics.stdev(values_list) if len(values_list) > 1 else 0.0
    minimum = min(values_list)
    maximum = max(values_list)
    median = statistics.median(values_list)

    return {
        "mean": mean,
        "std": std,
        "min": minimum,
        "max": maximum,
        "median": median,
    }


def format_stats_summary(stats: dict[str, float], precision: int = 4) -> str:
    """Format aggregate statistics as a compact string (pure).

    Args:
        stats: Dictionary of statistic name to value.
        precision: Decimal precision for formatting.

    Returns:
        Formatted string like "mean=0.1234 std=0.0123 min=0.0100 max=0.2000".
    """
    return " ".join(f"{key}={value:.{precision}f}" for key, value in stats.items())


def extract_scalar_metrics(
    metrics: dict[str, float | list[float]],
) -> dict[str, float]:
    """Extract scalar metric values from potentially batched metrics (pure).

    For list metrics, returns the first element. For scalar metrics,
    returns the value unchanged.

    Args:
        metrics: Dictionary of metric names to values.

    Returns:
        Dictionary with all values as scalars.
    """
    return {
        name: val if isinstance(val, float) else val[0] if val else 0.0
        for name, val in metrics.items()
    }


# ---------------------------------------------------------------------------
# Pure Grid Search Helpers
# ---------------------------------------------------------------------------


def generate_param_combinations(
    param_grid: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Generate all combinations of parameters from a grid (pure).

    Args:
        param_grid: Dictionary mapping parameter names to value lists.

    Returns:
        List of dictionaries, each representing one parameter combination.
    """
    if not param_grid:
        return [{}]

    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]

    combinations: list[dict[str, Any]] = []
    for values in product(*param_values):
        combo = dict(zip(param_names, values))
        combinations.append(combo)

    return combinations


def rank_grid_points(
    points: list["GridSearchPoint"],
    *,
    rank_by: str,
    minimize: bool = True,
) -> list["GridSearchPoint"]:
    """Sort grid points by a metric (pure).

    Args:
        points: List of grid search points to sort.
        rank_by: Metric name to rank by.
        minimize: If True, lower values rank first.

    Returns:
        Sorted list of points.
    """
    return sorted(
        points,
        key=lambda p: p.metrics.get(rank_by, float("inf") if minimize else float("-inf")),
        reverse=not minimize,
    )


# ---------------------------------------------------------------------------
# SeedSweep: Result and Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class SeedSweepResult:
    """Results from sweeping across multiple seeds (pure data class).

    Attributes:
        seeds: List of seeds that were tested.
        text: The input text that was corrupted.
        tokenizer_info: Description of the tokenizer used.
        per_seed_results: Mapping from seed to AttackResult.
        per_seed_metrics: Mapping from seed to scalar metrics dict.
        aggregate_stats: Aggregated statistics per metric.
    """

    seeds: list[int]
    text: str
    tokenizer_info: str
    per_seed_results: dict[int, AttackResult]
    per_seed_metrics: dict[int, dict[str, float]]
    aggregate_stats: dict[str, dict[str, float]]

    def summary(self, *, show_seeds: int = 5) -> str:
        """Generate a human-readable summary (pure formatting)."""
        lines: list[str] = [
            f"SeedSweep Results ({len(self.seeds)} seeds)",
            f"Tokenizer: {self.tokenizer_info}",
            f"Input text: {self.text[:50]}{'...' if len(self.text) > 50 else ''}",
            "",
            "Aggregate Statistics:",
        ]

        for metric_name, stats in self.aggregate_stats.items():
            lines.append(f"  {metric_name}:")
            lines.append(f"    {format_stats_summary(stats)}")

        if show_seeds > 0:
            lines.append("")
            lines.append(f"Per-Seed Metrics (first {min(show_seeds, len(self.seeds))}):")
            for seed in self.seeds[:show_seeds]:
                metrics = self.per_seed_metrics[seed]
                metric_strs = [f"{k}={v:.4f}" for k, v in metrics.items()]
                lines.append(f"  seed={seed}: {', '.join(metric_strs)}")
            if len(self.seeds) > show_seeds:
                lines.append(f"  ... {len(self.seeds) - show_seeds} more seeds")

        return "\n".join(lines)

    def to_report(self) -> dict[str, object]:
        """Convert to JSON-serializable dictionary (pure)."""
        return {
            "seeds": self.seeds,
            "text": self.text,
            "tokenizer": self.tokenizer_info,
            "per_seed_metrics": self.per_seed_metrics,
            "aggregate_stats": self.aggregate_stats,
        }

    def filter_by_metric(
        self,
        metric_name: str,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> dict[int, AttackResult]:
        """Filter per-seed results by metric thresholds.

        Args:
            metric_name: Name of the metric to filter by.
            min_value: Minimum metric value (inclusive).
            max_value: Maximum metric value (inclusive).

        Returns:
            Dictionary mapping seeds to AttackResults that meet criteria.
        """
        results: dict[int, AttackResult] = {}
        for seed in self.seeds:
            metrics = self.per_seed_metrics.get(seed, {})
            value = metrics.get(metric_name)
            if value is None:
                continue
            if min_value is not None and value < min_value:
                continue
            if max_value is not None and value > max_value:
                continue
            results[seed] = self.per_seed_results[seed]
        return results

    def export_csv(
        self,
        filepath: str,
        *,
        metrics: Sequence[str] | None = None,
    ) -> None:
        """Export per-seed metrics to CSV.

        Args:
            filepath: Path to write the CSV file.
            metrics: Specific metrics to include (None = all).
        """
        import csv

        if not self.per_seed_metrics:
            return

        # Determine metrics to export
        first_metrics = next(iter(self.per_seed_metrics.values()))
        if metrics is None:
            metric_names = list(first_metrics.keys())
        else:
            metric_names = list(metrics)

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["seed"] + metric_names)
            for seed in self.seeds:
                seed_metrics = self.per_seed_metrics.get(seed, {})
                row = [seed] + [seed_metrics.get(m, "") for m in metric_names]
                writer.writerow(row)

    def to_dataframe(self) -> "Any":
        """Convert to pandas DataFrame (requires pandas).

        Returns:
            DataFrame with seeds as index and metrics as columns.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            ) from e

        return pd.DataFrame(self.per_seed_metrics).T


class SeedSweep:
    """Sweep across multiple seeds to collect aggregate metrics (impure).

    This orchestrator runs attacks across many seeds and computes
    aggregate statistics (mean, std, min, max, median) for each metric.

    Example:
        >>> from glitchlings import Typogre
        >>> sweep = SeedSweep(Typogre(rate=0.05), tokenizer='cl100k_base')
        >>> result = sweep.run("Hello world", seeds=range(100))
        >>> print(result.summary())
    """

    def __init__(
        self,
        glitchlings: "Corruptor | str | Sequence[str | Corruptor]",
        tokenizer: str | Tokenizer | None = None,
        metrics: Mapping[str, Callable[..., float | list[float]]] | None = None,
    ) -> None:
        """Initialize a SeedSweep analyzer.

        Args:
            glitchlings: Glitchling specification (same as Attack).
            tokenizer: Tokenizer name or instance.
            metrics: Optional custom metrics (defaults to Attack defaults).
        """
        self._glitchlings_spec = glitchlings
        self._tokenizer_spec = tokenizer
        self._metrics = metrics
        # Impure: resolve tokenizer once
        self._resolved_tokenizer = resolve_tokenizer(tokenizer)
        self._tokenizer_info = describe_tokenizer(self._resolved_tokenizer, tokenizer)

    def run(
        self,
        text: str,
        seeds: Iterable[int],
        *,
        progress_callback: Callable[[list[tuple[int, AttackResult]]], None] | None = None,
        early_stop: Callable[[int, AttackResult], bool] | None = None,
    ) -> SeedSweepResult:
        """Run the sweep across specified seeds (impure execution).

        Args:
            text: Input text to corrupt.
            seeds: Iterable of seed values to test.
            progress_callback: Optional callback receiving list of (seed, result)
                pairs collected so far.
            early_stop: Optional predicate receiving (seed, result). If it returns
                True, the sweep stops early.

        Returns:
            SeedSweepResult with per-seed and aggregate statistics.
        """
        seeds_list = list(seeds)
        per_seed_results: dict[int, AttackResult] = {}
        per_seed_metrics: dict[int, dict[str, float]] = {}
        completed: list[tuple[int, AttackResult]] = []

        # Impure: run attacks for each seed
        for seed in seeds_list:
            attack = Attack(
                self._glitchlings_spec,
                tokenizer=self._resolved_tokenizer,
                metrics=self._metrics,
                seed=seed,
            )
            result = attack.run(text)
            per_seed_results[seed] = result
            # Pure: extract scalar metrics
            per_seed_metrics[seed] = extract_scalar_metrics(result.metrics)

            # Track progress
            completed.append((seed, result))
            if progress_callback is not None:
                progress_callback(completed)

            # Check early stopping
            if early_stop is not None and early_stop(seed, result):
                break

        # Pure: compute aggregate statistics
        aggregate_stats: dict[str, dict[str, float]] = {}
        completed_seeds = [seed for seed, _ in completed]
        if per_seed_metrics:
            metric_names = list(next(iter(per_seed_metrics.values())).keys())
            for metric_name in metric_names:
                values = [per_seed_metrics[seed][metric_name] for seed in completed_seeds]
                aggregate_stats[metric_name] = compute_aggregate_stats(values)

        return SeedSweepResult(
            seeds=completed_seeds,
            text=text,
            tokenizer_info=self._tokenizer_info,
            per_seed_results=per_seed_results,
            per_seed_metrics=per_seed_metrics,
            aggregate_stats=aggregate_stats,
        )


# ---------------------------------------------------------------------------
# GridSearch: Result and Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class GridSearchPoint:
    """A single point in the parameter grid (pure data class).

    Attributes:
        params: Dictionary of parameter name to value for this point.
        result: The AttackResult from running with these parameters.
        metrics: Extracted scalar metrics for easy comparison.
    """

    params: dict[str, Any]
    result: AttackResult
    metrics: dict[str, float]


@dataclass
class GridSearchResult:
    """Results from a grid search (pure data class).

    Attributes:
        text: The input text that was corrupted.
        tokenizer_info: Description of the tokenizer used.
        param_grid: The parameter grid that was searched.
        points: All evaluated grid points with results.
        best_point: The point with the best metric value (if ranked).
        ranking_metric: Name of the metric used for ranking.
        ranking_minimize: Whether ranking minimized (True) or maximized.
    """

    text: str
    tokenizer_info: str
    param_grid: dict[str, list[Any]]
    points: list[GridSearchPoint]
    best_point: GridSearchPoint | None
    ranking_metric: str | None
    ranking_minimize: bool

    def summary(self, *, show_top: int = 10) -> str:
        """Generate a human-readable summary (pure formatting)."""
        lines: list[str] = [
            f"GridSearch Results ({len(self.points)} combinations)",
            f"Tokenizer: {self.tokenizer_info}",
            f"Input text: {self.text[:50]}{'...' if len(self.text) > 50 else ''}",
            "",
            "Parameter Grid:",
        ]

        for param_name, values in self.param_grid.items():
            values_str = ", ".join(str(v) for v in values[:5])
            if len(values) > 5:
                values_str += f", ... ({len(values)} total)"
            lines.append(f"  {param_name}: [{values_str}]")

        if self.best_point and self.ranking_metric:
            direction = "minimizing" if self.ranking_minimize else "maximizing"
            lines.append("")
            lines.append(f"Best ({direction} {self.ranking_metric}):")
            lines.append(f"  params: {self.best_point.params}")
            metric_val = self.best_point.metrics.get(self.ranking_metric, 0.0)
            lines.append(f"  {self.ranking_metric}: {metric_val:.4f}")

        if show_top > 0 and self.ranking_metric:
            lines.append("")
            lines.append(f"Top {min(show_top, len(self.points))} Results:")
            # Pure: use rank_grid_points helper
            sorted_points = rank_grid_points(
                self.points,
                rank_by=self.ranking_metric,
                minimize=self.ranking_minimize,
            )
            for i, point in enumerate(sorted_points[:show_top], 1):
                metric_val = point.metrics.get(self.ranking_metric, 0.0)
                lines.append(f"  {i}. {point.params} -> {self.ranking_metric}={metric_val:.4f}")

        return "\n".join(lines)

    def to_report(self) -> dict[str, object]:
        """Convert to JSON-serializable dictionary (pure)."""
        return {
            "text": self.text,
            "tokenizer": self.tokenizer_info,
            "param_grid": self.param_grid,
            "num_combinations": len(self.points),
            "ranking_metric": self.ranking_metric,
            "ranking_minimize": self.ranking_minimize,
            "best_params": self.best_point.params if self.best_point else None,
            "best_metrics": self.best_point.metrics if self.best_point else None,
            "all_points": [{"params": p.params, "metrics": p.metrics} for p in self.points],
        }

    def filter_by_metric(
        self,
        metric_name: str,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> list[GridSearchPoint]:
        """Filter grid points by metric thresholds.

        Args:
            metric_name: Name of the metric to filter by.
            min_value: Minimum metric value (inclusive).
            max_value: Maximum metric value (inclusive).

        Returns:
            List of GridSearchPoints that meet the criteria.
        """
        results: list[GridSearchPoint] = []
        for point in self.points:
            value = point.metrics.get(metric_name)
            if value is None:
                continue
            if min_value is not None and value < min_value:
                continue
            if max_value is not None and value > max_value:
                continue
            results.append(point)
        return results

    def filter_by_params(self, **param_filters: Any) -> list[GridSearchPoint]:
        """Filter grid points by parameter values.

        Args:
            **param_filters: Parameter name=value pairs to match.

        Returns:
            List of GridSearchPoints matching all filters.

        Example:
            >>> result.filter_by_params(rate=0.05)
        """
        results: list[GridSearchPoint] = []
        for point in self.points:
            match = all(point.params.get(name) == value for name, value in param_filters.items())
            if match:
                results.append(point)
        return results

    def export_csv(
        self,
        filepath: str,
        *,
        include_params: bool = True,
        metrics: Sequence[str] | None = None,
    ) -> None:
        """Export all grid points to CSV.

        Args:
            filepath: Path to write the CSV file.
            include_params: Whether to include parameter columns.
            metrics: Specific metrics to include (None = all).
        """
        import csv

        if not self.points:
            return

        # Determine columns
        param_names = list(self.param_grid.keys()) if include_params else []
        first_metrics = self.points[0].metrics
        if metrics is None:
            metric_names = list(first_metrics.keys())
        else:
            metric_names = list(metrics)

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(param_names + metric_names)
            for point in self.points:
                param_values = [point.params.get(p, "") for p in param_names]
                metric_values = [point.metrics.get(m, "") for m in metric_names]
                writer.writerow(param_values + metric_values)

    def to_dataframe(self) -> "Any":
        """Convert to pandas DataFrame (requires pandas).

        Returns:
            DataFrame with parameters and metrics as columns.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            ) from e

        rows = []
        for point in self.points:
            row = {**point.params, **point.metrics}
            rows.append(row)
        return pd.DataFrame(rows)


class GridSearch:
    """Search across parameter combinations (impure orchestrator).

    This tool performs a grid search over parameter ranges, evaluating
    the attack at each combination and ranking by a specified metric.

    Example:
        >>> from glitchlings import Typogre
        >>> grid = GridSearch(
        ...     Typogre,
        ...     param_grid={"rate": [0.01, 0.05, 0.1, 0.2]},
        ...     tokenizer='cl100k_base'
        ... )
        >>> result = grid.run("Hello world", rank_by="normalized_edit_distance")
        >>> print(result.summary())
    """

    def __init__(
        self,
        glitchling_class: type["Corruptor"],
        param_grid: dict[str, list[Any]],
        *,
        tokenizer: str | Tokenizer | None = None,
        base_params: dict[str, Any] | None = None,
        seed: int | None = None,
        metrics: Mapping[str, Callable[..., float | list[float]]] | None = None,
    ) -> None:
        """Initialize a GridSearch analyzer.

        Args:
            glitchling_class: The Glitchling class to instantiate.
            param_grid: Dictionary mapping param names to value lists.
            tokenizer: Tokenizer name or instance.
            base_params: Default parameters (grid params override).
            seed: Seed for reproducibility.
            metrics: Optional custom metrics.
        """
        self._glitchling_class = glitchling_class
        self._param_grid = param_grid
        self._base_params = base_params or {}
        self._seed = seed
        self._metrics = metrics
        # Impure: resolve tokenizer once
        self._resolved_tokenizer = resolve_tokenizer(tokenizer)
        self._tokenizer_info = describe_tokenizer(self._resolved_tokenizer, tokenizer)

    def run(
        self,
        text: str,
        *,
        rank_by: str | None = "normalized_edit_distance",
        minimize: bool = True,
        progress_callback: Callable[[list[GridSearchPoint]], None] | None = None,
        early_stop: Callable[[GridSearchPoint], bool] | None = None,
    ) -> GridSearchResult:
        """Run grid search over all combinations (impure execution).

        Args:
            text: Input text to corrupt.
            rank_by: Metric name to rank by (None for no ranking).
            minimize: If True, lower metric values are better.
            progress_callback: Optional callback receiving list of evaluated
                GridSearchPoints so far.
            early_stop: Optional predicate receiving a GridSearchPoint. If it
                returns True, the search stops early.

        Returns:
            GridSearchResult with all points and best one.
        """
        # Pure: generate combinations
        combinations = generate_param_combinations(self._param_grid)
        points: list[GridSearchPoint] = []

        # Impure: run attacks for each combination
        for combo in combinations:
            params = {**self._base_params, **combo}
            glitchling = self._glitchling_class(**params)

            attack = Attack(
                glitchling,
                tokenizer=self._resolved_tokenizer,
                metrics=self._metrics,
                seed=self._seed,
            )
            result = attack.run(text)

            # Pure: extract scalar metrics
            metrics_dict = extract_scalar_metrics(result.metrics)

            point = GridSearchPoint(
                params=combo,
                result=result,
                metrics=metrics_dict,
            )
            points.append(point)

            # Callback with progress
            if progress_callback is not None:
                progress_callback(points)

            # Check early stopping
            if early_stop is not None and early_stop(point):
                break

        # Pure: find best point
        best_point: GridSearchPoint | None = None
        if rank_by and points:
            sorted_points = rank_grid_points(points, rank_by=rank_by, minimize=minimize)
            best_point = sorted_points[0]

        return GridSearchResult(
            text=text,
            tokenizer_info=self._tokenizer_info,
            param_grid=self._param_grid,
            points=points,
            best_point=best_point,
            ranking_metric=rank_by,
            ranking_minimize=minimize,
        )


# ---------------------------------------------------------------------------
# TokenizerComparison: Result and Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class TokenizerComparisonEntry:
    """Results for a single tokenizer in a comparison (pure data class).

    Attributes:
        tokenizer_name: Identifier/description of the tokenizer.
        result: Full AttackResult for this tokenizer.
        tokens: Output token strings after corruption.
        token_ids: Output token IDs after corruption.
        metrics: Extracted scalar metrics.
    """

    tokenizer_name: str
    result: AttackResult
    tokens: list[str]
    token_ids: list[int]
    metrics: dict[str, float]


@dataclass
class TokenizerComparisonResult:
    """Results from comparing multiple tokenizers (pure data class).

    Attributes:
        text: Original input text.
        corrupted_text: Text after corruption (same for all tokenizers).
        entries: Comparison entries for each tokenizer.
        metric_comparison: Metrics side-by-side for all tokenizers.
    """

    text: str
    corrupted_text: str
    entries: list[TokenizerComparisonEntry]
    metric_comparison: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Build metric comparison table (pure computation)."""
        if not self.metric_comparison and self.entries:
            all_metric_names: set[str] = set()
            for entry in self.entries:
                all_metric_names.update(entry.metrics.keys())

            for metric_name in sorted(all_metric_names):
                self.metric_comparison[metric_name] = {
                    entry.tokenizer_name: entry.metrics.get(metric_name, 0.0)
                    for entry in self.entries
                }

    def summary(self, *, show_tokens: int = 10) -> str:
        """Generate a human-readable comparison summary (pure formatting)."""
        lines: list[str] = [
            f"TokenizerComparison Results ({len(self.entries)} tokenizers)",
            f"Input: {self.text[:60]}{'...' if len(self.text) > 60 else ''}",
            f"Output: {self.corrupted_text[:60]}{'...' if len(self.corrupted_text) > 60 else ''}",
            "",
            "Metrics Comparison:",
        ]

        # Build metric comparison table
        tokenizer_names = [e.tokenizer_name for e in self.entries]
        header = "  " + " | ".join(f"{name[:15]:>15}" for name in ["metric"] + tokenizer_names)
        lines.append(header)
        lines.append("  " + "-" * len(header))

        for metric_name, values in self.metric_comparison.items():
            row_values = [f"{values.get(name, 0.0):>15.4f}" for name in tokenizer_names]
            lines.append(f"  {metric_name[:15]:>15} | " + " | ".join(row_values))

        # Token counts
        lines.append("")
        lines.append("Token Counts:")
        for entry in self.entries:
            input_count = len(entry.result.input_tokens)
            output_count = len(entry.tokens)
            delta = output_count - input_count
            lines.append(f"  {entry.tokenizer_name}: {input_count} -> {output_count} ({delta:+d})")

        # Token streams
        if show_tokens > 0:
            lines.append("")
            lines.append("Output Token Streams:")
            for entry in self.entries:
                lines.append(f"  {entry.tokenizer_name}:")
                display_tokens = entry.tokens[:show_tokens]
                tokens_str = ", ".join(f"'{t}'" for t in display_tokens)
                if len(entry.tokens) > show_tokens:
                    tokens_str += f", ... ({len(entry.tokens)} total)"
                lines.append(f"    [{tokens_str}]")

        return "\n".join(lines)

    def to_report(self, *, include_token_ids: bool = True) -> dict[str, object]:
        """Convert to JSON-serializable dictionary (pure)."""
        entries_data = []
        for entry in self.entries:
            entry_data: dict[str, object] = {
                "tokenizer": entry.tokenizer_name,
                "tokens": entry.tokens,
                "metrics": entry.metrics,
                "input_token_count": len(entry.result.input_tokens),
                "output_token_count": len(entry.tokens),
            }
            if include_token_ids:
                entry_data["token_ids"] = entry.token_ids
            entries_data.append(entry_data)

        return {
            "text": self.text,
            "corrupted_text": self.corrupted_text,
            "entries": entries_data,
            "metric_comparison": self.metric_comparison,
        }


def _extract_output_tokens(
    result: AttackResult,
) -> tuple[list[str], list[int]]:
    """Extract output tokens from an AttackResult (pure helper).

    Args:
        result: AttackResult to extract from.

    Returns:
        Tuple of (tokens, token_ids).
    """
    if isinstance(result.output_tokens, list) and result.output_tokens:
        if isinstance(result.output_tokens[0], list):
            # Batched - take first
            return result.output_tokens[0], result.output_token_ids[0]  # type: ignore[return-value]
        return result.output_tokens, result.output_token_ids  # type: ignore[return-value]
    return [], []


class TokenizerComparison:
    """Compare token streams and metrics across tokenizers (impure).

    This tool runs the same attack with multiple tokenizers to compare
    how different tokenization schemes affect token streams and metrics.

    Example:
        >>> from glitchlings import Typogre
        >>> compare = TokenizerComparison(
        ...     Typogre(rate=0.05),
        ...     tokenizers=['cl100k_base', 'o200k_base', 'gpt2']
        ... )
        >>> result = compare.run("Hello world")
        >>> print(result.summary())
    """

    def __init__(
        self,
        glitchlings: "Corruptor | str | Sequence[str | Corruptor]",
        tokenizers: Sequence[str | Tokenizer],
        *,
        seed: int | None = None,
        metrics: Mapping[str, Callable[..., float | list[float]]] | None = None,
    ) -> None:
        """Initialize a TokenizerComparison analyzer.

        Args:
            glitchlings: Glitchling specification (same as Attack).
            tokenizers: List of tokenizer names/instances to compare.
            seed: Seed for reproducibility (same for all tokenizers).
            metrics: Optional custom metrics.

        Raises:
            ValueError: If fewer than 1 tokenizer is provided.
        """
        if not tokenizers:
            raise ValueError("At least one tokenizer must be provided for comparison.")

        self._glitchlings_spec = glitchlings
        self._tokenizer_specs = list(tokenizers)
        self._seed = seed
        self._metrics = metrics

        # Impure: pre-resolve tokenizers
        self._resolved_tokenizers: list[tuple[str, Tokenizer]] = []
        for spec in self._tokenizer_specs:
            resolved = resolve_tokenizer(spec)
            info = describe_tokenizer(resolved, spec)
            self._resolved_tokenizers.append((info, resolved))

    def run(self, text: str) -> TokenizerComparisonResult:
        """Run comparison across all tokenizers (impure execution).

        Args:
            text: Input text to corrupt.

        Returns:
            TokenizerComparisonResult with entries for each tokenizer.
        """
        entries: list[TokenizerComparisonEntry] = []
        corrupted_text: str = ""

        # Impure: create gaggle for consistent corruption across tokenizers
        gaggle = resolve_glitchlings(
            self._glitchlings_spec,
            seed=self._seed,
            transcript_target=None,
        )
        corrupted_result = gaggle.corrupt(text)
        if isinstance(corrupted_result, str):
            corrupted_text = corrupted_result
        else:
            # For transcripts, join content for display
            corrupted_text = " ".join(
                turn.get("content", "") for turn in corrupted_result if isinstance(turn, dict)
            )

        # Impure: run attack with each tokenizer
        for tokenizer_name, tokenizer in self._resolved_tokenizers:
            attack = Attack(
                gaggle.clone(),  # Clone to reset RNG state
                tokenizer=tokenizer,
                metrics=self._metrics,
                seed=self._seed,
            )
            result = attack.run(text)

            # Pure: extract tokens and metrics
            tokens, token_ids = _extract_output_tokens(result)
            metrics_dict = extract_scalar_metrics(result.metrics)

            entries.append(
                TokenizerComparisonEntry(
                    tokenizer_name=tokenizer_name,
                    result=result,
                    tokens=tokens,
                    token_ids=token_ids,
                    metrics=metrics_dict,
                )
            )

        return TokenizerComparisonResult(
            text=text,
            corrupted_text=corrupted_text,
            entries=entries,
        )


# ---------------------------------------------------------------------------
# GlitchlingComparison: Compare Multiple Glitchlings
# ---------------------------------------------------------------------------


@dataclass
class GlitchlingComparisonEntry:
    """Results for a single glitchling in a comparison (pure data class).

    Attributes:
        name: Identifier for the glitchling.
        glitchling: The glitchling instance used.
        result: Full AttackResult for this glitchling.
        metrics: Extracted scalar metrics.
    """

    name: str
    glitchling: "Corruptor"
    result: AttackResult
    metrics: dict[str, float]


@dataclass
class GlitchlingComparisonResult:
    """Results from comparing multiple glitchlings (pure data class).

    Attributes:
        text: The input text that was corrupted.
        tokenizer_info: Description of the tokenizer used.
        entries: List of results per glitchling.
    """

    text: str
    tokenizer_info: str
    entries: list[GlitchlingComparisonEntry]

    @property
    def metric_comparison(self) -> dict[str, dict[str, float]]:
        """Get metrics organized by metric name -> glitchling name -> value."""
        if not self.entries:
            return {}

        metric_names = list(self.entries[0].metrics.keys())
        comparison: dict[str, dict[str, float]] = {}
        for metric_name in metric_names:
            comparison[metric_name] = {
                entry.name: entry.metrics.get(metric_name, 0.0) for entry in self.entries
            }
        return comparison

    def rank_by(
        self,
        metric_name: str,
        *,
        minimize: bool = True,
    ) -> list[GlitchlingComparisonEntry]:
        """Rank glitchlings by a specific metric.

        Args:
            metric_name: Metric to rank by.
            minimize: If True, lower is better.

        Returns:
            Entries sorted by the metric.
        """
        return sorted(
            self.entries,
            key=lambda e: e.metrics.get(metric_name, float("inf")),
            reverse=not minimize,
        )

    def summary(self, *, show_corrupted: bool = True) -> str:
        """Generate a human-readable summary (pure formatting)."""
        lines: list[str] = [
            "╭─ Glitchling Comparison ─────────────────────────────────╮",
            f"│ Tokenizer: {self.tokenizer_info:<45} │",
            f"│ Input: {self.text[:47]:<47} │"
            if len(self.text) <= 47
            else f"│ Input: {self.text[:44]}... │",
            "├──────────────────────────────────────────────────────────┤",
        ]

        # Metric comparison table
        if self.entries:
            metric_names = list(self.entries[0].metrics.keys())

            # Header
            header = "│ Glitchling"
            for name in metric_names:
                short_name = name[:10] if len(name) > 10 else name
                header += f" │ {short_name:>10}"
            header += " │"
            lines.append(header)
            lines.append("├" + "─" * 58 + "┤")

            # Rows
            for entry in self.entries:
                row = f"│ {entry.name:<10}"
                for metric_name in metric_names:
                    val = entry.metrics.get(metric_name, 0.0)
                    row += f" │ {val:>10.4f}"
                row += " │"
                lines.append(row)

        if show_corrupted and self.entries:
            lines.append("├──────────────────────────────────────────────────────────┤")
            lines.append("│ Corrupted Outputs:                                       │")
            for entry in self.entries:
                corrupted = str(entry.result.corrupted)
                if len(corrupted) > 45:
                    corrupted = corrupted[:42] + "..."
                lines.append(f"│   {entry.name}: {corrupted:<43} │")

        lines.append("╰──────────────────────────────────────────────────────────╯")
        return "\n".join(lines)

    def to_report(self) -> dict[str, object]:
        """Convert to JSON-serializable dictionary (pure)."""
        return {
            "text": self.text,
            "tokenizer": self.tokenizer_info,
            "entries": [
                {
                    "name": e.name,
                    "corrupted": e.result.corrupted,
                    "metrics": e.metrics,
                }
                for e in self.entries
            ],
            "metric_comparison": self.metric_comparison,
        }

    def to_dataframe(self) -> "Any":
        """Convert to pandas DataFrame (requires pandas).

        Returns:
            DataFrame with glitchling names as index and metrics as columns.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            ) from e

        data = {entry.name: entry.metrics for entry in self.entries}
        return pd.DataFrame(data).T


def compare_glitchlings(
    text: str,
    glitchlings: Sequence[tuple[str, "Corruptor"]],
    *,
    tokenizer: str | Tokenizer | None = None,
    metrics: Mapping[str, Callable[..., float | list[float]]] | None = None,
    seed: int | None = None,
) -> GlitchlingComparisonResult:
    """Compare multiple glitchlings on the same text with the same tokenizer.

    Holds the tokenizer fixed and varies the glitchlings - useful for finding
    which corruption strategy has the most impact for a specific tokenizer.

    Example:
        >>> from glitchlings import Typogre, Mim1c, Ekkokin
        >>> result = compare_glitchlings(
        ...     "Hello world",
        ...     [
        ...         ("typogre", Typogre(rate=0.05)),
        ...         ("mim1c", Mim1c(rate=0.05)),
        ...         ("ekkokin", Ekkokin(rate=0.05)),
        ...     ],
        ...     tokenizer="o200k_base",
        ... )
        >>> print(result.summary())
        >>> best = result.rank_by("normalized_edit_distance", minimize=False)[0]
        >>> print(f"Most disruptive: {best.name}")

    Args:
        text: Input text to corrupt.
        glitchlings: List of (name, glitchling) pairs to compare.
        tokenizer: Tokenizer to use (same for all glitchlings).
        metrics: Custom metrics (defaults to Attack defaults).
        seed: Seed for reproducibility.

    Returns:
        GlitchlingComparisonResult with all entries.
    """
    resolved_tokenizer = resolve_tokenizer(tokenizer)
    tokenizer_info = describe_tokenizer(resolved_tokenizer, tokenizer)

    entries: list[GlitchlingComparisonEntry] = []
    for name, glitchling in glitchlings:
        attack = Attack(
            glitchling,
            tokenizer=resolved_tokenizer,
            metrics=metrics,
            seed=seed,
        )
        result = attack.run(text)
        metrics_dict = extract_scalar_metrics(result.metrics)

        entries.append(
            GlitchlingComparisonEntry(
                name=name,
                glitchling=glitchling,
                result=result,
                metrics=metrics_dict,
            )
        )

    return GlitchlingComparisonResult(
        text=text,
        tokenizer_info=tokenizer_info,
        entries=entries,
    )


def compare_tokenizers(
    text: str,
    glitchling: "Corruptor | str | Sequence[str | Corruptor]",
    tokenizers: Sequence[str | Tokenizer],
    *,
    metrics: Mapping[str, Callable[..., float | list[float]]] | None = None,
    seed: int | None = None,
) -> "TokenizerComparisonResult":
    """Compare multiple tokenizers on the same corrupted text.

    Holds the glitchling fixed and varies the tokenizers - useful for finding
    which tokenizer is most affected by a specific corruption strategy.

    Example:
        >>> from glitchlings import Typogre
        >>> result = compare_tokenizers(
        ...     "Hello world",
        ...     Typogre(rate=0.1),
        ...     tokenizers=["o200k_base", "cl100k_base"],
        ... )
        >>> print(result.summary())

    Args:
        text: Input text to corrupt.
        glitchling: Glitchling to apply (same corruption for all tokenizers).
        tokenizers: List of tokenizer names/instances to compare.
        metrics: Custom metrics (defaults to Attack defaults).
        seed: Seed for reproducibility.

    Returns:
        TokenizerComparisonResult with all entries.
    """
    comparison = TokenizerComparison(
        glitchling,
        tokenizers=tokenizers,
        metrics=metrics,
        seed=seed,
    )
    return comparison.run(text)


__all__ = [
    # Pure statistical helpers
    "compute_aggregate_stats",
    "format_stats_summary",
    "extract_scalar_metrics",
    # Pure grid helpers
    "generate_param_combinations",
    "rank_grid_points",
    # SeedSweep
    "SeedSweep",
    "SeedSweepResult",
    # GridSearch
    "GridSearch",
    "GridSearchResult",
    "GridSearchPoint",
    # TokenizerComparison
    "TokenizerComparison",
    "TokenizerComparisonResult",
    "TokenizerComparisonEntry",
    # Comparison functions
    "compare_glitchlings",
    "compare_tokenizers",
    "GlitchlingComparisonResult",
    "GlitchlingComparisonEntry",
]
