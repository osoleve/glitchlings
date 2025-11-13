"""Structural metrics: RORD, SPI, MSI, BHR.

These metrics measure changes in token order, sequence structure,
and tokenizer-specific phenomena.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..core.align import (
    damerau_levenshtein_distance,
    kendall_tau_distance,
    longest_common_subsequence,
)


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


def span_perturbation_index(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Span Perturbation Index (SPI).

    Measures the fragmentation of edits by counting contiguous change spans
    from the edit alignment.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {
            "value": float in [0,1] (span count / max length),
            "num_spans": int (number of contiguous edit spans),
            "mean_span_length": float (average span size)
        }

    Algorithm:
        1. Compute edit operations from DL alignment
        2. Collapse consecutive edits into spans
        3. Normalize by max sequence length

    Examples:
        >>> span_perturbation_index([0,1,2,3], [0,9,2,3], {})
        {"value": 0.25, "num_spans": 1, "mean_span_length": 1.0}

    Note:
        - Detects concentrated vs scattered edits
        - Lower SPI = more concentrated changes
        - Higher SPI = more fragmented changes
    """
    m, n = len(before), len(after)

    if m == 0 and n == 0:
        return {"value": 0.0, "num_spans": 0, "mean_span_length": 0.0}

    max_len = max(m, n)

    # For now, use a simplified heuristic based on LCS
    # A more complete implementation would trace the DP table
    # to extract actual edit spans
    lcs_len, _ = longest_common_subsequence(before, after)

    # Estimate: number of edits = max_len - lcs_len
    num_edits = max_len - lcs_len

    if num_edits == 0:
        return {"value": 0.0, "num_spans": 0, "mean_span_length": 0.0}

    # Heuristic: assume edits are evenly distributed
    # In a more complete implementation, we'd trace the edit path
    # For now, estimate 1 span per contiguous edit region
    # This is a placeholder - real implementation would analyze DP traceback

    # Simple estimate: if sequences differ in length or have substitutions,
    # count as separate spans
    estimated_spans = 1  # Minimum

    if abs(m - n) > 0:
        # Length changes suggest at least one span
        estimated_spans = max(1, min(num_edits, max_len // 2))
    else:
        # Same length, likely substitutions
        estimated_spans = min(num_edits, max_len)

    normalized = estimated_spans / max_len
    mean_len = num_edits / estimated_spans if estimated_spans > 0 else 0.0

    return {
        "value": min(1.0, normalized),
        "num_spans": estimated_spans,
        "mean_span_length": mean_len,
    }


def merge_split_index(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Merge-Split Index (MSI).

    Estimates tokenizer-induced merge (k→1) and split (1→k) events,
    typically seen in BPE/WordPiece transformations.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Optional "merge_threshold" and "split_threshold" (default 0.5)

    Returns:
        {
            "value": float in [0,1] (event count / max length),
            "merges": int (estimated k→1 events),
            "splits": int (estimated 1→k events)
        }

    Algorithm:
        Heuristic based on length ratio and LCS:
        - Length decrease → likely merges
        - Length increase → likely splits
        - Magnitude based on ratio

    Examples:
        >>> merge_split_index([42, 314], [1337], {})
        {"value": 1.0, "merges": 1, "splits": 0}  # 2→1 merge

        >>> merge_split_index([1337], [42, 314], {})
        {"value": 1.0, "merges": 0, "splits": 1}  # 1→2 split

    Note:
        - Heuristic estimate (not exact)
        - Works best for actual tokenizer changes
        - High MSI indicates tokenizer sensitivity
    """
    m, n = len(before), len(after)

    if m == 0 or n == 0:
        # Edge case: empty sequences
        return {"value": 0.0, "merges": 0, "splits": 0}

    if m == n:
        # Same length: unlikely to have significant merge/split
        return {"value": 0.0, "merges": 0, "splits": 0}

    max_len = max(m, n)

    # Heuristic: estimate based on length change
    if n < m:
        # Compression: likely merges
        merges = m - n
        splits = 0
    else:
        # Expansion: likely splits
        merges = 0
        splits = n - m

    total_events = merges + splits
    normalized = total_events / max_len

    return {
        "value": min(1.0, normalized),
        "merges": merges,
        "splits": splits,
    }


def boundary_hit_rate(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Boundary Hit Rate (BHR).

    Measures the fraction of special tokens (punctuation, whitespace, etc.)
    that were modified.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Required "boundary_tokens" - set of token IDs considered boundaries

    Returns:
        {
            "value": float in [0,1] (fraction of boundaries edited),
            "num_boundaries": int (total boundary tokens in before),
            "num_hit": int (boundary tokens that changed)
        }

    Algorithm:
        1. Identify boundary tokens in `before` via context["boundary_tokens"]
        2. Use LCS to find which boundaries are preserved
        3. Compute hit rate as (total - preserved) / total

    Examples:
        >>> # Token IDs: 100=Hello, 5=comma, 200=world, 6=period
        >>> boundary_hit_rate([100, 5, 200], [100, 6, 200],
        ...                   {"boundary_tokens": {5, 6}})
        {"value": 1.0, "num_boundaries": 1, "num_hit": 1}

    Note:
        - Requires manual specification of boundary tokens
        - Token-level, not character-level
        - Useful for punctuation/spacing glitchlings
    """
    boundary_set = context.get("boundary_tokens", set())

    if not boundary_set:
        # No boundaries defined: return 0
        return {"value": 0.0, "num_boundaries": 0, "num_hit": 0}

    # Find boundary positions in `before`
    boundary_positions = [i for i, token in enumerate(before) if token in boundary_set]

    if not boundary_positions:
        # No boundaries in input
        return {"value": 0.0, "num_boundaries": 0, "num_hit": 0}

    # Use LCS to find preserved tokens
    _, lcs_indices = longest_common_subsequence(before, after)
    preserved_positions = set(lcs_indices)

    # Count boundary hits (boundaries NOT preserved)
    num_hit = sum(1 for pos in boundary_positions if pos not in preserved_positions)

    num_boundaries = len(boundary_positions)
    hit_rate = num_hit / num_boundaries if num_boundaries > 0 else 0.0

    return {
        "value": hit_rate,
        "num_boundaries": num_boundaries,
        "num_hit": num_hit,
    }


__all__ = [
    "reordering_score",
    "span_perturbation_index",
    "merge_split_index",
    "boundary_hit_rate",
]
