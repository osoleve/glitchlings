"""Complexity metrics: compression delta.

These metrics measure changes in sequence compressibility and structure.
"""

from __future__ import annotations

import gzip
from typing import Any, Mapping, Sequence


def compression_delta(
    before: Sequence[int], after: Sequence[int], context: Mapping[str, Any]
) -> Mapping[str, float]:
    """Compute Compression Delta (CΔ).

    Measures change in compressibility by comparing gzip-compressed sizes
    of the token sequences.

    Args:
        before: Original token sequence
        after: Transformed token sequence
        context: Optional "method" (default "gzip")

    Returns:
        {
            "delta": fractional change in compressed size,
            "before_size": compressed size of before,
            "after_size": compressed size of after,
            "ratio": after_size / before_size
        }

    Formula:
        CΔ = (C(after) - C(before)) / C(before)

    Interpretation:
        - CΔ > 0: Less compressible (more random/complex)
        - CΔ < 0: More compressible (more redundant)
        - CΔ = 0: Same compressibility

    Examples:
        >>> # Increase redundancy
        >>> compression_delta([0,1,2,3,4,5,6,7], [0,0,0,0,0,0,0,0], {})
        {"delta": -0.5...}  # More compressible

        >>> # Increase diversity
        >>> compression_delta([0,0,0,0], [0,1,2,3], {})
        {"delta": 0.3...}  # Less compressible

    Note:
        - Requires serializing tokens to bytes
        - Result depends on compression algorithm and settings
        - Short sequences may have noisy estimates
        - gzip level 6 is used by default
    """
    method = context.get("method", "gzip")

    if method != "gzip":
        raise ValueError(f"Unsupported compression method: {method}")

    # Convert token sequences to byte arrays
    # Use 4 bytes per token (int32)
    def tokens_to_bytes(tokens: Sequence[int]) -> bytes:
        return b"".join(t.to_bytes(4, byteorder="little", signed=True) for t in tokens)

    bytes_before = tokens_to_bytes(before)
    bytes_after = tokens_to_bytes(after)

    # Handle empty sequences
    if not bytes_before:
        bytes_before = b"\x00"  # Minimum placeholder
    if not bytes_after:
        bytes_after = b"\x00"

    # Compress with gzip
    compressed_before = gzip.compress(bytes_before, compresslevel=6)
    compressed_after = gzip.compress(bytes_after, compresslevel=6)

    size_before = len(compressed_before)
    size_after = len(compressed_after)

    # Compute delta
    if size_before == 0:
        delta = 0.0
        ratio = 1.0
    else:
        delta = (size_after - size_before) / size_before
        ratio = size_after / size_before

    return {
        "delta": delta,
        "before_size": size_before,
        "after_size": size_after,
        "ratio": ratio,
    }


__all__ = [
    "compression_delta",
]
