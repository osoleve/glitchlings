"""Analysis tools for comparing tokenizers and exploring parameter spaces.

This module provides three main analysis tools:

1. **SeedSweep**: Run an attack across many seeds to collect aggregate metrics
2. **GridSearch**: Search across parameter combinations to find optimal settings
3. **TokenizerComparison**: Compare token streams and metrics across multiple tokenizers

Design Philosophy
-----------------
These tools follow the functional purity architecture:
- Pure functions for computing statistics and formatting results
- Impure orchestration classes that coordinate Attack runs
- Dataclasses for structured, immutable result objects

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import TYPE_CHECKING, Any, Callable

from ..util.adapters import coerce_gaggle
from .core import Attack, AttackResult
from .encode import describe_tokenizer
from .tokenization import Tokenizer, resolve_tokenizer

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..zoo.core import Glitchling


# ---------------------------------------------------------------------------
# Pure Statistical Helpers
# ---------------------------------------------------------------------------


def compute_aggregate_stats(values: Sequence[float]) -> dict[str, float]:
    """Compute aggregate statistics for a sequence of metric values.

    Args:
        values: Sequence of float values to aggregate.

    Returns:
        Dictionary containing mean, std, min, max, and median.
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
    """Format aggregate statistics as a compact string.

    Args:
        stats: Dictionary of statistic name to value.
        precision: Decimal precision for formatting.

    Returns:
        Formatted string like "mean=0.1234 std=0.0123 min=0.0100 max=0.2000".
    """
    return " ".join(f"{key}={value:.{precision}f}" for key, value in stats.items())


# ---------------------------------------------------------------------------
# SeedSweep: Aggregate metrics across seeds
# ---------------------------------------------------------------------------


@dataclass
class SeedSweepResult:
    """Results from sweeping across multiple seeds.

    Attributes:
        seeds: List of seeds that were tested.
        text: The input text that was corrupted.
        tokenizer_info: Description of the tokenizer used.
        per_seed_results: Mapping from seed to AttackResult.
        per_seed_metrics: Mapping from seed to metrics dict.
        aggregate_stats: Aggregated statistics per metric.
    """

    seeds: list[int]
    text: str
    tokenizer_info: str
    per_seed_results: dict[int, AttackResult]
    per_seed_metrics: dict[int, dict[str, float]]
    aggregate_stats: dict[str, dict[str, float]]

    def summary(self, *, show_seeds: int = 5) -> str:
        """Generate a human-readable summary of the sweep results.

        Args:
            show_seeds: Maximum number of individual seed results to display.

        Returns:
            Formatted multi-line summary string.
        """
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
        """Convert results to a JSON-serializable dictionary."""
        return {
            "seeds": self.seeds,
            "text": self.text,
            "tokenizer": self.tokenizer_info,
            "per_seed_metrics": self.per_seed_metrics,
            "aggregate_stats": self.aggregate_stats,
        }


class SeedSweep:
    """Sweep across multiple seeds to collect aggregate metrics.

    This tool runs the same attack configuration across many different seeds
    and computes aggregate statistics (mean, std, min, max, median) for each
    metric. This helps understand the variance in corruption behavior.

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
        self._resolved_tokenizer = resolve_tokenizer(tokenizer)
        self._tokenizer_info = describe_tokenizer(self._resolved_tokenizer, tokenizer)

    def run(
        self,
        text: str,
        seeds: Iterable[int],
    ) -> SeedSweepResult:
        """Run the sweep across the specified seeds.

        Args:
            text: Input text to corrupt.
            seeds: Iterable of seed values to test.

        Returns:
            SeedSweepResult containing per-seed and aggregate statistics.
        """
        seeds_list = list(seeds)
        per_seed_results: dict[int, AttackResult] = {}
        per_seed_metrics: dict[int, dict[str, float]] = {}

        for seed in seeds_list:
            attack = Attack(
                self._glitchlings_spec,
                tokenizer=self._resolved_tokenizer,
                metrics=self._metrics,
                seed=seed,
            )
            result = attack.run(text)
            per_seed_results[seed] = result
            # Extract scalar metrics (for single-string input)
            per_seed_metrics[seed] = {
                name: val if isinstance(val, float) else val[0] if val else 0.0
                for name, val in result.metrics.items()
            }

        # Compute aggregate statistics per metric
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
# GridSearch: Search parameter combinations
# ---------------------------------------------------------------------------


@dataclass
class GridSearchPoint:
    """A single point in the parameter grid with its results.

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
    """Results from a grid search across parameter combinations.

    Attributes:
        text: The input text that was corrupted.
        tokenizer_info: Description of the tokenizer used.
        param_grid: The parameter grid that was searched.
        points: All evaluated grid points with results.
        best_point: The point with the best metric value (if ranked).
        ranking_metric: Name of the metric used for ranking.
        ranking_minimize: Whether the ranking minimized (True) or maximized (False).
    """

    text: str
    tokenizer_info: str
    param_grid: dict[str, list[Any]]
    points: list[GridSearchPoint]
    best_point: GridSearchPoint | None
    ranking_metric: str | None
    ranking_minimize: bool

    def summary(self, *, show_top: int = 10) -> str:
        """Generate a human-readable summary of the grid search results.

        Args:
            show_top: Number of top results to display.

        Returns:
            Formatted multi-line summary string.
        """
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
            lines.append(f"  {self.ranking_metric}: {self.best_point.metrics.get(self.ranking_metric, 'N/A'):.4f}")

        if show_top > 0 and self.ranking_metric:
            lines.append("")
            lines.append(f"Top {min(show_top, len(self.points))} Results:")
            sorted_points = sorted(
                self.points,
                key=lambda p: p.metrics.get(self.ranking_metric, float("inf")),
                reverse=not self.ranking_minimize,
            )
            for i, point in enumerate(sorted_points[:show_top], 1):
                metric_val = point.metrics.get(self.ranking_metric, 0.0)
                lines.append(f"  {i}. {point.params} -> {self.ranking_metric}={metric_val:.4f}")

        return "\n".join(lines)

    def to_report(self) -> dict[str, object]:
        """Convert results to a JSON-serializable dictionary."""
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
    """Search across parameter combinations to find optimal settings.

    This tool performs a grid search over specified parameter ranges,
    evaluating the attack at each combination and ranking by a specified
    metric.

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
            param_grid: Dictionary mapping parameter names to lists of values to try.
            tokenizer: Tokenizer name or instance.
            base_params: Default parameters to use (grid params override these).
            seed: Seed for reproducibility.
            metrics: Optional custom metrics.
        """
        self._glitchling_class = glitchling_class
        self._param_grid = param_grid
        self._base_params = base_params or {}
        self._seed = seed
        self._metrics = metrics
        self._resolved_tokenizer = resolve_tokenizer(tokenizer)
        self._tokenizer_info = describe_tokenizer(self._resolved_tokenizer, tokenizer)

    def _generate_param_combinations(self) -> list[dict[str, Any]]:
        """Generate all combinations of parameters from the grid."""
        if not self._param_grid:
            return [{}]

        param_names = list(self._param_grid.keys())
        param_values = [self._param_grid[name] for name in param_names]

        combinations: list[dict[str, Any]] = []
        for values in product(*param_values):
            combo = dict(zip(param_names, values))
            combinations.append(combo)

        return combinations

    def run(
        self,
        text: str,
        *,
        rank_by: str | None = "normalized_edit_distance",
        minimize: bool = True,
    ) -> GridSearchResult:
        """Run the grid search over all parameter combinations.

        Args:
            text: Input text to corrupt.
            rank_by: Metric name to rank results by. None for no ranking.
            minimize: If True, lower metric values are better.

        Returns:
            GridSearchResult containing all evaluated points and the best one.
        """
        combinations = self._generate_param_combinations()
        points: list[GridSearchPoint] = []

        for combo in combinations:
            # Merge base params with grid params
            params = {**self._base_params, **combo}
            glitchling = self._glitchling_class(**params)

            attack = Attack(
                glitchling,
                tokenizer=self._resolved_tokenizer,
                metrics=self._metrics,
                seed=self._seed,
            )
            result = attack.run(text)

            # Extract scalar metrics
            metrics_dict: dict[str, float] = {
                name: val if isinstance(val, float) else val[0] if val else 0.0
                for name, val in result.metrics.items()
            }

            points.append(GridSearchPoint(
                params=combo,
                result=result,
                metrics=metrics_dict,
            ))

        # Find best point if ranking requested
        best_point: GridSearchPoint | None = None
        if rank_by and points:
            sorted_points = sorted(
                points,
                key=lambda p: p.metrics.get(rank_by, float("inf") if minimize else float("-inf")),
                reverse=not minimize,
            )
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
# TokenizerComparison: Compare across multiple tokenizers
# ---------------------------------------------------------------------------


@dataclass
class TokenizerComparisonEntry:
    """Results for a single tokenizer in a comparison.

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
    """Results from comparing multiple tokenizers.

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
        """Build the metric comparison table after initialization."""
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
        """Generate a human-readable comparison summary.

        Args:
            show_tokens: Maximum tokens to display per tokenizer.

        Returns:
            Formatted multi-line summary string.
        """
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
        """Convert results to a JSON-serializable dictionary.

        Args:
            include_token_ids: Whether to include token ID arrays.

        Returns:
            Dictionary suitable for JSON serialization.
        """
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


class TokenizerComparison:
    """Compare token streams and metrics across multiple tokenizers.

    This tool runs the same attack with multiple tokenizers to see how
    different tokenization schemes affect the resulting token streams
    and corruption metrics.

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
            tokenizers: List of tokenizer names or instances to compare.
            seed: Seed for reproducibility (same seed used for all tokenizers).
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

        # Pre-resolve tokenizers
        self._resolved_tokenizers: list[tuple[str, Tokenizer]] = []
        for spec in self._tokenizer_specs:
            resolved = resolve_tokenizer(spec)
            info = describe_tokenizer(resolved, spec)
            self._resolved_tokenizers.append((info, resolved))

    def run(self, text: str) -> TokenizerComparisonResult:
        """Run the comparison across all tokenizers.

        Args:
            text: Input text to corrupt.

        Returns:
            TokenizerComparisonResult containing entries for each tokenizer.
        """
        entries: list[TokenizerComparisonEntry] = []
        corrupted_text: str = ""

        # Create a single gaggle to ensure same corruption for all tokenizers
        gaggle = coerce_gaggle(
            self._glitchlings_spec,
            seed=self._seed,
            apply_seed_to_existing=True,
        )
        corrupted_result = gaggle.corrupt(text)
        if isinstance(corrupted_result, str):
            corrupted_text = corrupted_result
        else:
            # For transcripts, join content for display
            corrupted_text = " ".join(
                turn.get("content", "") for turn in corrupted_result if isinstance(turn, dict)
            )

        for tokenizer_name, tokenizer in self._resolved_tokenizers:
            attack = Attack(
                gaggle.clone(),  # Clone to reset RNG state
                tokenizer=tokenizer,
                metrics=self._metrics,
                seed=self._seed,
            )
            result = attack.run(text)

            # Extract tokens and metrics
            tokens: list[str]
            token_ids: list[int]
            if isinstance(result.output_tokens, list) and result.output_tokens:
                if isinstance(result.output_tokens[0], list):
                    # Batched - take first
                    tokens = result.output_tokens[0]  # type: ignore
                    token_ids = result.output_token_ids[0]  # type: ignore
                else:
                    tokens = result.output_tokens  # type: ignore
                    token_ids = result.output_token_ids  # type: ignore
            else:
                tokens = []
                token_ids = []

            metrics_dict: dict[str, float] = {
                name: val if isinstance(val, float) else val[0] if val else 0.0
                for name, val in result.metrics.items()
            }

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
    # Pure helpers
    "compute_aggregate_stats",
    "format_stats_summary",
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
