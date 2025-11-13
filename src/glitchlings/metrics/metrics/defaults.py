"""Default metric registry with core metrics.

This module provides a pre-configured registry with all core metrics
for convenient usage.
"""

from __future__ import annotations

from .edit import lcs_retention, normalized_edit_distance, position_match_rate
from .registry import MetricRegistry, MetricSpec
from .sets import jaccard_bag_distance, jaccard_set_distance, length_ratio
from .structure import reordering_score


def create_default_registry() -> MetricRegistry:
    """Create a registry with all core metrics pre-registered.

    Returns:
        MetricRegistry with core metrics:
        - ned: Normalized Edit Distance
        - lcsr: LCS Retention Rate
        - pmr: Position Match Rate
        - jsdset: Jaccard Set Distance
        - jsdbag: Jaccard Bag (Multiset) Distance
        - rord: Reordering Score
        - lr: Length Ratio

    Example:
        >>> from glitchlings.metrics.metrics.defaults import create_default_registry
        >>> registry = create_default_registry()
        >>> len(registry)
        7
        >>> results = registry.compute_all([0,1,2], [0,2,1], {})
        >>> results["ned.value"]
        0.333...
    """
    registry = MetricRegistry()

    # Edit & overlap metrics
    registry.register(
        MetricSpec(
            id="ned",
            name="Normalized Edit Distance (Damerau-Levenshtein)",
            fn=normalized_edit_distance,
            semantics={
                "type": "distance",
                "higher_is_worse": True,
                "symmetric": True,
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    registry.register(
        MetricSpec(
            id="lcsr",
            name="LCS Retention Rate",
            fn=lcs_retention,
            semantics={
                "type": "distance",
                "higher_is_worse": False,  # Higher retention = better
                "symmetric": False,  # Normalized by |before|
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    registry.register(
        MetricSpec(
            id="pmr",
            name="Position-wise Match Rate",
            fn=position_match_rate,
            semantics={
                "type": "distance",
                "higher_is_worse": False,  # Higher match rate = better
                "symmetric": False,  # Depends on alignment direction
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    # Set-based metrics
    registry.register(
        MetricSpec(
            id="jsdset",
            name="Jaccard Set Distance",
            fn=jaccard_set_distance,
            semantics={
                "type": "distance",
                "higher_is_worse": True,
                "symmetric": True,
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    registry.register(
        MetricSpec(
            id="jsdbag",
            name="Jaccard Multiset (Bag) Distance",
            fn=jaccard_bag_distance,
            semantics={
                "type": "distance",
                "higher_is_worse": True,
                "symmetric": True,
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    # Structural metrics
    registry.register(
        MetricSpec(
            id="rord",
            name="Reordering Score (Kendall-tau)",
            fn=reordering_score,
            semantics={
                "type": "structure",
                "higher_is_worse": True,
                "symmetric": False,
                "bounded": (0.0, 1.0),
            },
            norm={
                "default_range": (0.0, 1.0),
                "preferred_transform": "identity",
            },
        )
    )

    # Length metrics
    registry.register(
        MetricSpec(
            id="lr",
            name="Length Ratio",
            fn=length_ratio,
            semantics={
                "type": "complexity",
                "higher_is_worse": None,  # Not a distance; just a ratio
                "symmetric": False,
                "bounded": None,  # Can be > 1
            },
            norm={
                "default_range": (0.5, 2.0),  # Typical range for visualization
                "preferred_transform": "log",  # Log scale for ratios
            },
        )
    )

    return registry


__all__ = [
    "create_default_registry",
]
