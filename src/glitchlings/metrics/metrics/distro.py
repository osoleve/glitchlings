"""Distributional metrics: cosine distance, JS divergence, entropy.

These metrics measure changes in token frequency distributions.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence


def cosine_distance(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Cosine Distance on token frequency vectors.

    Builds frequency vectors over the union vocabulary and computes
    cosine distance (1 - cosine similarity).

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Unused

    Returns:
        {"value": float in [0,1]} where 0 = identical distributions

    Formula:
        cos(θ) = (v · w) / (|v| |w|)
        distance = 1 - cos(θ)

    Examples:
        >>> cosine_distance([0,1,2], [0,1,2], {})
        {"value": 0.0}  # Identical

        >>> cosine_distance([0,0,0], [1,1,1], {})
        {"value": 1.0}  # Orthogonal (no overlap)

    Note:
        - Frequency vectors (not binary)
        - Symmetric metric
        - Dominated by common tokens unless IDF-weighted
    """
    counts_before = Counter(before)
    counts_after = Counter(after)

    if not counts_before and not counts_after:
        return {"value": 0.0}  # Both empty

    # Build frequency vectors over union vocabulary
    vocab = set(counts_before.keys()) | set(counts_after.keys())

    if not vocab:
        return {"value": 0.0}

    # Compute dot product and norms
    dot_product = 0.0
    norm_before = 0.0
    norm_after = 0.0

    for token in vocab:
        freq_before = counts_before.get(token, 0)
        freq_after = counts_after.get(token, 0)

        dot_product += freq_before * freq_after
        norm_before += freq_before * freq_before
        norm_after += freq_after * freq_after

    # Compute cosine similarity
    magnitude = math.sqrt(norm_before) * math.sqrt(norm_after)

    if magnitude == 0.0:
        # One (or both) distributions are empty. If both are empty we already
        # returned above, so hitting this branch means one vector has mass
        # while the other does not. Treat as maximally different.
        if counts_before and counts_after:
            return {"value": 0.0}
        return {"value": 1.0}

    cosine_sim = dot_product / magnitude
    distance = 1.0 - cosine_sim

    # Clamp to [0, 1] (numerical stability)
    distance = max(0.0, min(1.0, distance))

    return {"value": distance}


def jensen_shannon_divergence(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Jensen-Shannon Divergence between token distributions.

    JSD is a symmetric, bounded measure of distribution difference based
    on KL divergence.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Optional smoothing parameter "epsilon" (default 1e-8)

    Returns:
        {"value": float in [0,1]} where 0 = identical, 1 = maximally different

    Formula:
        JSD(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
        where M = 0.5 * (P + Q)
        KL(P||Q) = Σ P(x) log(P(x)/Q(x))

    Normalized to [0,1] by dividing by log(2).

    Examples:
        >>> jensen_shannon_divergence([0,1,2], [0,1,2], {})
        {"value": 0.0}  # Identical

        >>> jensen_shannon_divergence([0,0,0], [1,1,1], {})
        {"value": 1.0}  # Disjoint (maximal divergence)

    References:
        Lin (1991), "Divergence measures based on the Shannon entropy"
    """
    epsilon = context.get("epsilon", 1e-8)

    counts_before = Counter(before)
    counts_after = Counter(after)

    m, n = len(before), len(after)

    if m == 0 and n == 0:
        return {"value": 0.0}  # Both empty

    # Build distributions with smoothing
    vocab = set(counts_before.keys()) | set(counts_after.keys())
    vocab_size = len(vocab)

    if vocab_size == 0:
        return {"value": 0.0}

    # Smoothed distributions
    def make_dist(counts: Counter[int], length: int) -> dict[int, float]:
        smoothed_total = length + epsilon * vocab_size
        return {t: (counts.get(t, 0) + epsilon) / smoothed_total for t in vocab}

    p_dist = make_dist(counts_before, m)
    q_dist = make_dist(counts_after, n)

    # Compute mixture distribution M = 0.5(P + Q)
    m_dist = {t: 0.5 * (p_dist[t] + q_dist[t]) for t in vocab}

    # Compute KL divergences
    def kl_divergence(p: dict[int, float], q: dict[int, float]) -> float:
        return sum(p[t] * math.log(p[t] / q[t]) for t in vocab)

    kl_pm = kl_divergence(p_dist, m_dist)
    kl_qm = kl_divergence(q_dist, m_dist)

    jsd = 0.5 * kl_pm + 0.5 * kl_qm

    # Normalize to [0, 1] by dividing by log(2)
    jsd_normalized = jsd / math.log(2)

    # Clamp for numerical stability
    jsd_normalized = max(0.0, min(1.0, jsd_normalized))

    return {"value": jsd_normalized}


def entropy_delta(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute change in Shannon entropy (ΔH).

    Measures whether the transformation made the distribution more or less uniform.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Optional smoothing parameter "epsilon" (default 1e-8)

    Returns:
        {
            "delta": ΔH = H(after) - H(before),
            "before": H(before),
            "after": H(after)
        }

    Formula:
        H(P) = -Σ P(x) log₂(P(x))

    Interpretation:
        - ΔH > 0: More uniform (higher entropy)
        - ΔH < 0: More concentrated (lower entropy)
        - ΔH = 0: Same entropy

    Examples:
        >>> entropy_delta([0,0,0,0,0,0,0,1], [0,1,2,3,4,5,6,7], {})
        {"delta": 2.456, "before": 0.544, "after": 3.0}  # More uniform

        >>> entropy_delta([0,1,2], [0,1,2], {})
        {"delta": 0.0, "before": 1.585, "after": 1.585}  # Same

    Note:
        - Uses base-2 logarithm (bits)
        - Requires smoothing for zero probabilities
        - Not a distance metric (can be negative)
    """
    epsilon = context.get("epsilon", 1e-8)

    def compute_entropy(seq: Sequence[int]) -> float:
        if not seq:
            return 0.0

        counts = Counter(seq)
        total = len(seq)
        vocab_size = len(counts)

        # Smoothed total
        smoothed_total = total + epsilon * vocab_size

        entropy = 0.0
        for count in counts.values():
            prob = (count + epsilon) / smoothed_total
            entropy -= prob * math.log2(prob)

        return entropy

    h_before = compute_entropy(before)
    h_after = compute_entropy(after)
    delta = h_after - h_before

    return {"delta": delta, "before": h_before, "after": h_after}


__all__ = [
    "cosine_distance",
    "jensen_shannon_divergence",
    "entropy_delta",
]
