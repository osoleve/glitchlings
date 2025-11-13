"""Core alignment algorithms for token sequence comparison.

This module provides fundamental sequence alignment algorithms:
- Damerau-Levenshtein distance (with transpositions)
- Longest Common Subsequence (LCS)
- Kendall-tau rank correlation (for reordering detection)

All algorithms are optimized for correctness first, performance second.
For production use, consider Cython/Numba acceleration if needed.
"""

from __future__ import annotations

from typing import Sequence, Tuple


def damerau_levenshtein_distance(
    seq1: Sequence[int], seq2: Sequence[int]
) -> Tuple[int, float]:
    """Compute Damerau-Levenshtein distance with transpositions.

    The DL distance measures the minimum number of operations to transform
    seq1 into seq2, where operations are:
    - Insertion
    - Deletion
    - Substitution
    - Transposition (adjacent swap)

    Args:
        seq1: First token sequence
        seq2: Second token sequence

    Returns:
        Tuple of (raw_distance, normalized_distance)
        - raw_distance: Integer edit distance
        - normalized_distance: Float in [0, 1], normalized by max length

    Examples:
        >>> damerau_levenshtein_distance([0,1,2], [0,2,1])
        (1, 0.333...)  # One transposition

        >>> damerau_levenshtein_distance([0,1,2], [0,1,2,3])
        (1, 0.25)  # One insertion

        >>> damerau_levenshtein_distance([], [])
        (0, 0.0)  # Identity

    References:
        Damerau (1964), "A technique for computer detection and
        correction of spelling errors"
    """
    m, n = len(seq1), len(seq2)

    # Edge cases
    if m == 0:
        raw = n
        norm = 1.0 if n > 0 else 0.0
        return raw, norm
    if n == 0:
        raw = m
        norm = 1.0 if m > 0 else 0.0
        return raw, norm

    # Initialize DP table
    # dp[i][j] = min edits to transform seq1[:i] to seq2[:j]
    INF = m + n  # Sentinel value larger than any valid distance
    dp = [[INF] * (n + 2) for _ in range(m + 2)]

    # Initialize first row/column
    dp[0][0] = INF
    for i in range(0, m + 1):
        dp[i + 1][0] = INF
        dp[i + 1][1] = i
    for j in range(0, n + 1):
        dp[0][j + 1] = INF
        dp[1][j + 1] = j

    # Track last occurrence of each character (for transpositions)
    last_match: dict[int, int] = {}

    # Fill DP table
    for i in range(1, m + 1):
        last_match_j = 0
        for j in range(1, n + 1):
            # Cost of matching current characters
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            last_i = last_match.get(seq2[j - 1], 0)
            last_j = last_match_j

            if seq1[i - 1] == seq2[j - 1]:
                last_match_j = j

            dp[i + 1][j + 1] = min(
                dp[i][j] + cost,  # Substitution (or match)
                dp[i + 1][j] + 1,  # Insertion
                dp[i][j + 1] + 1,  # Deletion
                dp[last_i][last_j] + (i - last_i - 1) + 1 + (j - last_j - 1),  # Transposition
            )

        last_match[seq1[i - 1]] = i

    raw = dp[m + 1][n + 1]
    max_len = max(m, n)
    norm = raw / max_len if max_len > 0 else 0.0

    return raw, norm


def longest_common_subsequence(seq1: Sequence[int], seq2: Sequence[int]) -> Tuple[int, list[int]]:
    """Compute longest common subsequence (LCS) length and elements.

    LCS is the longest subsequence present in both sequences (not necessarily
    contiguous). Used for measuring order preservation.

    Args:
        seq1: First token sequence
        seq2: Second token sequence

    Returns:
        Tuple of (lcs_length, lcs_indices_in_seq1)
        - lcs_length: Length of LCS
        - lcs_indices_in_seq1: Indices of LCS elements in seq1

    Examples:
        >>> longest_common_subsequence([0,1,2], [0,2,1])
        (2, [0, 1])  # LCS is [0,1] or [0,2]

        >>> longest_common_subsequence([0,1,2], [0,1,2,3])
        (3, [0, 1, 2])  # Entire seq1

        >>> longest_common_subsequence([0,1], [2,3])
        (0, [])  # No overlap

    References:
        Standard dynamic programming LCS algorithm
    """
    m, n = len(seq1), len(seq2)

    # Edge cases
    if m == 0 or n == 0:
        return 0, []

    # DP table: dp[i][j] = LCS length of seq1[:i] and seq2[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[m][n]

    # Backtrack to find one LCS (left-to-right stable)
    indices: list[int] = []
    i, j = m, n
    while i > 0 and j > 0:
        if seq1[i - 1] == seq2[j - 1]:
            indices.append(i - 1)
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    indices.reverse()

    return lcs_length, indices


def kendall_tau_distance(rank1: Sequence[int], rank2: Sequence[int]) -> Tuple[int, float]:
    """Compute Kendall-tau distance (number of discordant pairs).

    Measures the number of pairwise disagreements between two rankings.
    Used for detecting reordering in matched token subsequences.

    Args:
        rank1: First ranking (sequence of indices)
        rank2: Second ranking (sequence of indices)

    Returns:
        Tuple of (num_inversions, normalized_distance)
        - num_inversions: Number of discordant pairs
        - normalized_distance: Float in [0, 1], normalized by n*(n-1)/2

    Examples:
        >>> kendall_tau_distance([0,1,2], [0,1,2])
        (0, 0.0)  # Perfect agreement

        >>> kendall_tau_distance([0,1,2], [2,1,0])
        (3, 1.0)  # Perfect reversal

        >>> kendall_tau_distance([0,1,2], [0,2,1])
        (1, 0.333...)  # One inversion

    Notes:
        - Handles duplicates via stable tie-breaking
        - O(n^2) naive implementation; for large n, consider merge-sort approach

    References:
        Kendall (1938), "A New Measure of Rank Correlation"
    """
    n = len(rank1)

    if n != len(rank2):
        raise ValueError(f"Rank sequences must have same length: {n} vs {len(rank2)}")

    if n <= 1:
        return 0, 0.0

    # Count inversions (pairs where order disagrees)
    inversions = 0
    for i in range(n):
        for j in range(i + 1, n):
            # Check if pair (i,j) is inverted
            if (rank1[i] < rank1[j]) != (rank2[i] < rank2[j]):
                inversions += 1

    max_inversions = n * (n - 1) // 2
    norm = inversions / max_inversions if max_inversions > 0 else 0.0

    return inversions, norm


def position_wise_match_rate(
    seq1: Sequence[int], seq2: Sequence[int], *, align_by_lcs: bool = True
) -> float:
    """Compute fraction of positions with matching tokens.

    After minimal alignment (via LCS), compute the fraction of positions
    where tokens are identical.

    Args:
        seq1: First token sequence
        seq2: Second token sequence
        align_by_lcs: Use LCS for alignment (default True)

    Returns:
        Float in [0, 1] representing match rate (higher = more matches)

    Examples:
        >>> position_wise_match_rate([0,1,2], [0,1,2])
        1.0  # All match

        >>> position_wise_match_rate([0,1,2], [0,9,2])
        0.666...  # 2 out of 3 match

    Note:
        This returns MATCH rate, not CHANGE rate. For change rate, use 1 - result.
    """
    m, n = len(seq1), len(seq2)

    if m == 0 and n == 0:
        return 1.0  # Identity
    if m == 0 or n == 0:
        return 0.0  # No overlap

    if align_by_lcs:
        # Use LCS to find matched positions
        lcs_len, _ = longest_common_subsequence(seq1, seq2)
        return lcs_len / max(m, n)
    else:
        # Simple position-wise comparison (no alignment)
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
        return matches / max(m, n)


__all__ = [
    "damerau_levenshtein_distance",
    "longest_common_subsequence",
    "kendall_tau_distance",
    "position_wise_match_rate",
]
