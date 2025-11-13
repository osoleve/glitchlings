"""Structural metrics: RORD (Reordering Score).

These metrics measure changes in token order and sequence structure.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..core.align import kendall_tau_distance, longest_common_subsequence


def reordering_score(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Reordering Score (RORD) using Kendall-tau distance.

    Measures how much the relative order of matched tokens has changed,
    independent of insertions/deletions/substitutions.

    Algorithm:
    1. Find LCS to identify matched tokens
    2. Extract their indices in both sequences
    3. Compute Kendall-tau distance on the index sequences

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 0 = order preserved, 1 = order reversed

    Examples:
        >>> reordering_score([0,1,2], [0,2,1], {})
        {"value": 0.333...}  # One inversion

        >>> reordering_score([0,1,2,3], [3,2,1,0], {})
        {"value": 1.0}  # Perfect reversal

        >>> reordering_score([0,1,2], [0,1,2,3], {})
        {"value": 0.0}  # Order preserved (insertion doesn't affect order)

    Note:
        - Handles duplicates via stable left-to-right matching
        - Returns 0 if < 2 tokens match (no pairs to compare)
    """
    # Find matched tokens via LCS
    lcs_len, lcs_indices_before = longest_common_subsequence(before, after)

    if lcs_len < 2:
        # Need at least 2 tokens to measure reordering
        return {"value": 0.0}

    # Build corresponding indices in `after`
    # Use greedy left-to-right matching on matched tokens
    lcs_indices_after: list[int] = []
    after_pos = 0
    for before_idx in lcs_indices_before:
        target_token = before[before_idx]
        # Find next occurrence of target_token in after[after_pos:]
        while after_pos < len(after):
            if after[after_pos] == target_token:
                lcs_indices_after.append(after_pos)
                after_pos += 1
                break
            after_pos += 1

    # Sanity check: should have same number of indices
    if len(lcs_indices_before) != len(lcs_indices_after):
        # Shouldn't happen with correct LCS, but handle gracefully
        return {"value": 0.0}

    # Compute Kendall-tau distance on index sequences
    _, tau_dist = kendall_tau_distance(lcs_indices_before, lcs_indices_after)

    return {"value": tau_dist}


__all__ = [
    "reordering_score",
]
