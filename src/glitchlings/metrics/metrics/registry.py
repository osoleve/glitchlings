"""Metric registration and discovery system.

This module provides the core abstraction for metrics:
- MetricFn: Protocol for metric functions
- MetricSpec: Metadata for a registered metric
- MetricRegistry: Central registry for metric discovery and execution

Design:
- Metrics are pure functions over token sequences
- Registry holds metadata and enables programmatic discovery
- Results are structured (dict of floats) for extensibility
- Context dict allows pluggable dependencies (e.g., LMs)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Protocol, Sequence

Token = int


class MetricFn(Protocol):
    """Protocol for metric computation functions.

    All metrics must accept:
    - before: Original token sequence
    - after: Transformed token sequence
    - context: Optional runtime dependencies (e.g., epsilon for smoothing)

    Returns:
    - Dict mapping metric keys to float values
    - Keys prefixed with metric ID (e.g., "ned.value", "ned.transpositions")

    Example:
        def my_metric(before, after, context):
            diff = len(after) - len(before)
            return {"length_delta": float(diff)}
    """

    def __call__(
        self, before: Sequence[Token], after: Sequence[Token], context: Mapping[str, Any]
    ) -> Mapping[str, float]:
        """Compute metric value(s)."""
        ...


@dataclass(frozen=True)
class MetricSpec:
    """Metadata for a registered metric.

    Attributes:
        id: Unique identifier (e.g., "ned", "jsdiv")
        name: Human-readable name (e.g., "Normalized Edit Distance")
        fn: The metric function
        semantics: Metadata about interpretation
            - "type": "distance" | "distribution" | "structure" | "complexity"
            - "higher_is_worse": bool (True for distances, False for similarities)
            - "symmetric": bool (d(x,y) == d(y,x))
            - "bounded": tuple[float, float] | None (min, max values)
        norm: Hints for normalization/visualization
            - "default_range": tuple[float, float] for axis scaling
            - "preferred_transform": "identity" | "log" | "sigmoid"
        requires: External dependencies (e.g., "lm", "gzip")

    Example:
        MetricSpec(
            id="ned",
            name="Normalized Edit Distance",
            fn=normalized_edit_distance,
            semantics={
                "type": "distance",
                "higher_is_worse": True,
                "symmetric": True,
                "bounded": (0.0, 1.0),
            },
        )
    """

    id: str
    name: str
    fn: MetricFn
    semantics: Mapping[str, Any] = field(default_factory=dict)
    norm: Mapping[str, Any] = field(default_factory=dict)
    requires: Iterable[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate spec."""
        if not self.id.isidentifier():
            raise ValueError(f"Metric ID must be valid identifier: {self.id!r}")
        if not self.name:
            raise ValueError("Metric name cannot be empty")


class MetricRegistry:
    """Central registry for metric discovery and execution.

    Manages metric registration and batch computation. Metrics are
    identified by unique IDs and can be queried programmatically.

    Example:
        >>> registry = MetricRegistry()
        >>> registry.register(ned_spec)
        >>> registry.register(jsdiv_spec)
        >>>
        >>> results = registry.compute_all([0,1,2], [0,2,1], {})
        >>> results["ned.value"]
        0.333...
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._specs: Dict[str, MetricSpec] = {}

    def register(self, spec: MetricSpec) -> None:
        """Register a metric.

        Args:
            spec: Metric specification

        Raises:
            ValueError: If metric ID already registered
        """
        if spec.id in self._specs:
            raise ValueError(f"Duplicate metric ID: {spec.id!r}")
        self._specs[spec.id] = spec

    def unregister(self, metric_id: str) -> None:
        """Remove a metric from the registry.

        Args:
            metric_id: ID of metric to remove

        Raises:
            KeyError: If metric not found
        """
        del self._specs[metric_id]

    def get(self, metric_id: str) -> MetricSpec | None:
        """Retrieve metric spec by ID.

        Args:
            metric_id: Metric identifier

        Returns:
            MetricSpec if found, None otherwise
        """
        return self._specs.get(metric_id)

    def list_metrics(self) -> Iterable[MetricSpec]:
        """List all registered metrics.

        Returns:
            Iterator over MetricSpec objects
        """
        return self._specs.values()

    def compute(
        self,
        metric_id: str,
        before: Sequence[Token],
        after: Sequence[Token],
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, float]:
        """Compute a single metric.

        Args:
            metric_id: ID of metric to compute
            before: Original token sequence
            after: Transformed token sequence
            context: Optional runtime dependencies

        Returns:
            Dict of metric values (keys include metric_id prefix)

        Raises:
            KeyError: If metric not found
            KeyError: If metric requires missing context keys
        """
        spec = self._specs.get(metric_id)
        if spec is None:
            raise KeyError(f"Metric not found: {metric_id!r}")

        ctx = context or {}

        # Validate dependencies
        for dep in spec.requires:
            if dep not in ctx:
                raise KeyError(
                    f"Metric {metric_id!r} requires context key {dep!r} "
                    f"(available: {list(ctx.keys())})"
                )

        # Compute metric
        raw_results = spec.fn(before, after, ctx)

        # Prefix keys with metric ID
        return {f"{metric_id}.{k}": v for k, v in raw_results.items()}

    def compute_all(
        self,
        before: Sequence[Token],
        after: Sequence[Token],
        context: Mapping[str, Any] | None = None,
    ) -> Dict[str, float]:
        """Compute all registered metrics.

        Args:
            before: Original token sequence
            after: Transformed token sequence
            context: Optional runtime dependencies

        Returns:
            Dict mapping "metric_id.key" to float values

        Note:
            Metrics requiring unavailable context keys are skipped
            with a warning (no exception raised).
        """
        ctx = context or {}
        results: Dict[str, float] = {}

        for spec in self._specs.values():
            try:
                metric_results = self.compute(spec.id, before, after, ctx)
                results.update(metric_results)
            except KeyError:
                # Skip metrics with missing dependencies
                # TODO: Add logging/warning
                pass

        return results

    def __len__(self) -> int:
        """Return number of registered metrics."""
        return len(self._specs)

    def __contains__(self, metric_id: str) -> bool:
        """Check if metric is registered."""
        return metric_id in self._specs

    def __repr__(self) -> str:
        """Return string representation."""
        return f"MetricRegistry(metrics={list(self._specs.keys())})"


__all__ = [
    "Token",
    "MetricFn",
    "MetricSpec",
    "MetricRegistry",
]
