"""Set-based metrics: Jaccard distance (set and multiset variants).

These metrics measure vocabulary overlap without considering order.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


def jaccard_set_distance(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Jaccard distance on token sets (ignoring multiplicity).

    Measures lexical repertoire changes without considering token counts or order.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 0 = identical sets, 1 = disjoint sets

    Formula:
        J = |A ∩ B| / |A ∪ B|
        distance = 1 - J

    Examples:
        >>> jaccard_set_distance([0,1,2], [0,2,1], {})
        {"value": 0.0}  # Same set

        >>> jaccard_set_distance([0,1,2], [0,1,2,3], {})
        {"value": 0.25}  # 3 common, 4 total; dist=1-3/4

        >>> jaccard_set_distance([0,1,2], [3,4,5], {})
        {"value": 1.0}  # Disjoint
    """
    set_before = set(before)
    set_after = set(after)

    if not set_before and not set_after:
        return {"value": 0.0}  # Both empty: identity

    intersection = len(set_before & set_after)
    union = len(set_before | set_after)

    if union == 0:
        return {"value": 0.0}  # Shouldn't happen, but handle gracefully

    jaccard = intersection / union
    distance = 1.0 - jaccard

    return {"value": distance}


def jaccard_bag_distance(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Jaccard distance on token multisets (considering multiplicity).

    Measures content turnover while accounting for token frequencies.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 0 = identical bags, 1 = disjoint bags

    Formula:
        J_multiset = Σ min(count_A(t), count_B(t)) / Σ max(count_A(t), count_B(t))
        distance = 1 - J_multiset

    Examples:
        >>> jaccard_bag_distance([0,0,1], [0,1,1], {})
        {"value": 0.333...}  # min=2, max=3; dist=1-2/3

        >>> jaccard_bag_distance([0,1,2], [0,1,2], {})
        {"value": 0.0}  # Identical
    """
    counts_before = Counter(before)
    counts_after = Counter(after)

    if not counts_before and not counts_after:
        return {"value": 0.0}  # Both empty

    all_tokens = set(counts_before.keys()) | set(counts_after.keys())

    min_sum = sum(min(counts_before[t], counts_after[t]) for t in all_tokens)
    max_sum = sum(max(counts_before[t], counts_after[t]) for t in all_tokens)

    if max_sum == 0:
        return {"value": 0.0}  # Shouldn't happen

    jaccard = min_sum / max_sum
    distance = 1.0 - jaccard

    return {"value": distance}


def length_ratio(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute length ratio and absolute length change.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {
            "ratio": n/m (can be > 1),
            "delta": |1 - n/m| (absolute change from 1.0)
        }

    Examples:
        >>> length_ratio([0,1,2], [0,1,2,3], {})
        {"ratio": 1.333..., "delta": 0.333...}

        >>> length_ratio([0,1,2], [0,1,2], {})
        {"ratio": 1.0, "delta": 0.0}
    """
    m = len(before)
    n = len(after)

    if m == 0 and n == 0:
        return {"ratio": 1.0, "delta": 0.0}  # Define 0/0 as 1.0

    if m == 0:
        # Undefined, but we'll say infinite expansion
        # For practical purposes, cap at some large value
        return {"ratio": float("inf"), "delta": float("inf")}

    ratio = n / m
    delta = abs(1.0 - ratio)

    return {"ratio": ratio, "delta": delta}


__all__ = [
    "jaccard_set_distance",
    "jaccard_bag_distance",
    "length_ratio",
]
