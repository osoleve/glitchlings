"""Default metric registry with core metrics.

This module provides a pre-configured registry with all core metrics
for convenient usage.
"""

from __future__ import annotations

from .complexity import compression_delta
from .distro import cosine_distance, entropy_delta, jensen_shannon_divergence
from .edit import lcs_retention, normalized_edit_distance, position_match_rate
from .registry import MetricRegistry, MetricSpec
from .sets import jaccard_bag_distance, jaccard_set_distance, length_ratio
from .structure import (
    boundary_hit_rate,
    merge_split_index,
    reordering_score,
    span_perturbation_index,
)


def create_default_registry() -> MetricRegistry:
    """Create a registry with all 14 core metrics pre-registered.

    Returns:
        MetricRegistry with core metrics:

        Edit & Overlap (3):
        - ned: Normalized Edit Distance (Damerau-Levenshtein)
        - lcsr: LCS Retention Rate
        - pmr: Position Match Rate

        Set-based (2):
        - jsdset: Jaccard Set Distance
        - jsdbag: Jaccard Multiset Distance

        Distributional (3):
        - cosdist: Cosine Distance on Frequencies
        - jsdiv: Jensen-Shannon Divergence
        - h_delta: Entropy Delta

        Structural (4):
        - rord: Reordering Score (Kendall-tau)
        - spi: Span Perturbation Index
        - msi: Merge-Split Index
        - bhr: Boundary Hit Rate

        Complexity & Length (2):
        - c_delta: Compression Delta
        - lr: Length Ratio

    Example:
        >>> from glitchlings.metrics.metrics.defaults import create_default_registry
        >>> registry = create_default_registry()
        >>> len(registry)
        14
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

    # Distributional metrics
    registry.register(
        MetricSpec(
            id="cosdist",
            name="Cosine Distance on Token Frequencies",
            fn=cosine_distance,
            semantics={
                "type": "distribution",
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
            id="jsdiv",
            name="Jensen-Shannon Divergence",
            fn=jensen_shannon_divergence,
            semantics={
                "type": "distribution",
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
            id="h_delta",
            name="Entropy Delta",
            fn=entropy_delta,
            semantics={
                "type": "distribution",
                "higher_is_worse": None,  # Can be positive or negative
                "symmetric": False,
                "bounded": None,  # Can be negative
            },
            norm={
                "default_range": (-3.0, 3.0),  # Typical range for visualization
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

    registry.register(
        MetricSpec(
            id="spi",
            name="Span Perturbation Index",
            fn=span_perturbation_index,
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

    registry.register(
        MetricSpec(
            id="msi",
            name="Merge-Split Index",
            fn=merge_split_index,
            semantics={
                "type": "structure",
                "higher_is_worse": None,  # Context-dependent
                "symmetric": False,
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
            id="bhr",
            name="Boundary Hit Rate",
            fn=boundary_hit_rate,
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
            requires=["boundary_tokens"],  # Requires context
        )
    )

    # Complexity & Length metrics
    registry.register(
        MetricSpec(
            id="c_delta",
            name="Compression Delta",
            fn=compression_delta,
            semantics={
                "type": "complexity",
                "higher_is_worse": None,  # Context-dependent
                "symmetric": False,
                "bounded": None,  # Can be negative
            },
            norm={
                "default_range": (-1.0, 1.0),  # Typical range for visualization
                "preferred_transform": "identity",
            },
        )
    )

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
