"""Pure metric dispatch functions.

This module contains pure functions for dispatching metric computations.
It does not import Rust FFI or perform any IO - it operates on already-
resolved metric functions.

Pure guarantees:
- No import side effects beyond stdlib
- No Rust FFI loading
- Deterministic dispatch logic

The impure Rust metric loading lives in metrics.py.
"""

from __future__ import annotations

from typing import Sequence, TypeGuard

TokenSequence = Sequence[str]
TokenBatch = Sequence[TokenSequence]


def is_batch(tokens: TokenSequence | TokenBatch) -> TypeGuard[TokenBatch]:
    """Determine if tokens represent a batch of sequences.

    An empty list is treated as an empty batch (returning True) so that
    ``metric([], [])`` returns ``[]`` rather than ``0.0``. This matches
    the behavior of :meth:`Attack.run` when processing empty transcripts.

    Args:
        tokens: Either a sequence of token strings or a batch of such sequences.

    Returns:
        True if tokens is a batch (list of lists), False if a single sequence.
    """
    if not tokens:
        return True  # Empty list is an empty batch

    first = tokens[0]
    return isinstance(first, Sequence) and not isinstance(first, (str, bytes))


def validate_batch_consistency(
    original: TokenSequence | TokenBatch,
    corrupted: TokenSequence | TokenBatch,
    metric_name: str,
) -> None:
    """Validate that both inputs are consistently batched or single.

    Args:
        original: Original token sequence or batch.
        corrupted: Corrupted token sequence or batch.
        metric_name: Name of the metric (for error messages).

    Raises:
        TypeError: If one input is batched and the other isn't.
    """
    original_is_batch = is_batch(original)
    corrupted_is_batch = is_batch(corrupted)

    if original_is_batch != corrupted_is_batch:
        raise TypeError(f"{metric_name} expects either both batch inputs or both single sequences")


__all__ = [
    "TokenBatch",
    "TokenSequence",
    "is_batch",
    "validate_batch_consistency",
]
