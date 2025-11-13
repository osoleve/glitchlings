"""Edit-based metrics: NED, LCSR, PMR.

These metrics measure character-level and token-level edits between sequences.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..core.align import (
    damerau_levenshtein_distance,
    longest_common_subsequence,
    position_wise_match_rate,
)


def normalized_edit_distance(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Normalized Damerau-Levenshtein Edit Distance (NED).

    Measures minimal insertions, deletions, substitutions, and transpositions
    to transform `before` into `after`, normalized by max length.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 1 = completely different

    Examples:
        >>> normalized_edit_distance([0,1,2], [0,2,1], {})
        {"value": 0.333...}  # One transposition

    References:
        Damerau (1964), "A technique for computer detection..."
    """
    _, norm_dist = damerau_levenshtein_distance(before, after)
    return {"value": norm_dist}


def lcs_retention(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute LCS Retention Rate (LCSR).

    Measures what fraction of the original sequence order is preserved,
    based on the Longest Common Subsequence.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 1 = fully preserved

    Note:
        This metric is ASYMMETRIC (normalized by |before|, not |after|).
        For a symmetric version, use min(m,n) or max(m,n) normalization.

    Examples:
        >>> lcs_retention([0,1,2], [0,1,2,3], {})
        {"value": 1.0}  # All of original preserved

        >>> lcs_retention([0,1,2,3], [0,1,2], {})
        {"value": 0.75}  # 3 out of 4 preserved
    """
    m = len(before)
    if m == 0:
        return {"value": 0.0}  # Define as 0 when before is empty

    lcs_len, _ = longest_common_subsequence(before, after)
    retention = lcs_len / m

    return {"value": retention}


def position_match_rate(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Position-wise Match Rate (PMR).

    After LCS-based alignment, compute fraction of positions with identical tokens.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 1 = all positions match

    Note:
        Returns MATCH rate (not change rate). For change rate, use 1 - value.

    Examples:
        >>> position_match_rate([0,1,2], [0,9,2], {})
        {"value": 0.666...}  # 2 out of 3 match
    """
    rate = position_wise_match_rate(before, after, align_by_lcs=True)
    return {"value": rate}


__all__ = [
    "normalized_edit_distance",
    "lcs_retention",
    "position_match_rate",
]
