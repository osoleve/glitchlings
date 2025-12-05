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
    from ..zoo.core import Glitchling


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
        glitchlings: "Glitchling | str | Iterable[str | Glitchling]",
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
    ) -> SeedSweepResult:
        """Run the sweep across specified seeds (impure execution).

        Args:
            text: Input text to corrupt.
            seeds: Iterable of seed values to test.

        Returns:
            SeedSweepResult with per-seed and aggregate statistics.
        """
        seeds_list = list(seeds)
        per_seed_results: dict[int, AttackResult] = {}
        per_seed_metrics: dict[int, dict[str, float]] = {}

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

        # Pure: compute aggregate statistics
        aggregate_stats: dict[str, dict[str, float]] = {}
        if per_seed_metrics:
            metric_names = list(next(iter(per_seed_metrics.values())).keys())
            for metric_name in metric_names:
                values = [per_seed_metrics[seed][metric_name] for seed in seeds_list]
                aggregate_stats[metric_name] = compute_aggregate_stats(values)

        return SeedSweepResult(
            seeds=seeds_list,
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
            "all_points": [
                {"params": p.params, "metrics": p.metrics} for p in self.points
            ],
        }


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
        glitchling_class: type["Glitchling"],
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
    ) -> GridSearchResult:
        """Run grid search over all combinations (impure execution).

        Args:
            text: Input text to corrupt.
            rank_by: Metric name to rank by (None for no ranking).
            minimize: If True, lower metric values are better.

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

            points.append(GridSearchPoint(
                params=combo,
                result=result,
                metrics=metrics_dict,
            ))

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
            return result.output_tokens[0], result.output_token_ids[0]  # type: ignore
        return result.output_tokens, result.output_token_ids  # type: ignore
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
        glitchlings: "Glitchling | str | Iterable[str | Glitchling]",
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

            entries.append(TokenizerComparisonEntry(
                tokenizer_name=tokenizer_name,
                result=result,
                tokens=tokens,
                token_ids=token_ids,
                metrics=metrics_dict,
            ))

        return TokenizerComparisonResult(
            text=text,
            corrupted_text=corrupted_text,
            entries=entries,
        )


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
]
