from __future__ import annotations

import importlib
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, cast

from .metrics_dispatch import TokenBatch, TokenSequence, is_batch, validate_batch_consistency

if TYPE_CHECKING:
    from collections.abc import Callable


class Metric(Protocol):
    def __call__(
        self,
        original_tokens: TokenSequence | TokenBatch,
        corrupted_tokens: TokenSequence | TokenBatch,
    ) -> float | list[float]: ...


class BatchMetric(Protocol):
    def __call__(self, inputs: TokenBatch, outputs: TokenBatch) -> list[float]: ...


try:
    _rust: Any = importlib.import_module("glitchlings._zoo_rust")
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
    raise ImportError(
        "Could not import compiled Rust extension. "
        "Please ensure the project is installed with the Rust extension built."
    ) from exc

_single_jsd = cast(Metric, getattr(_rust, "jensen_shannon_divergence"))
_single_ned = cast(Metric, getattr(_rust, "normalized_edit_distance"))
_single_sr = cast(Metric, getattr(_rust, "subsequence_retention"))
_single_ed = cast(Metric, getattr(_rust, "entropy_delta"))
_single_msi = cast(Metric, getattr(_rust, "merge_split_index"))
_batch_jsd = cast(BatchMetric, getattr(_rust, "batch_jensen_shannon_divergence"))
_batch_ned = cast(BatchMetric, getattr(_rust, "batch_normalized_edit_distance"))
_batch_sr = cast(BatchMetric, getattr(_rust, "batch_subsequence_retention"))
_batch_ed = cast(BatchMetric, getattr(_rust, "batch_entropy_delta"))
_batch_msi = cast(BatchMetric, getattr(_rust, "batch_merge_split_index"))


def _dispatch_metric(
    original: TokenSequence | TokenBatch,
    corrupted: TokenSequence | TokenBatch,
    *,
    single: Metric,
    batch: BatchMetric,
    name: str,
) -> float | list[float]:
    """Dispatch metric computation to single or batch implementation.

    Uses the pure is_batch function to determine which implementation to call.
    """
    validate_batch_consistency(original, corrupted, name)

    if is_batch(original):
        return batch(original, corrupted)

    return single(original, corrupted)


def jensen_shannon_divergence(
    original_tokens: TokenSequence | TokenBatch,
    corrupted_tokens: TokenSequence | TokenBatch,
) -> float | list[float]:
    return _dispatch_metric(
        original_tokens,
        corrupted_tokens,
        single=_single_jsd,
        batch=_batch_jsd,
        name="jensen_shannon_divergence",
    )


def normalized_edit_distance(
    original_tokens: TokenSequence | TokenBatch,
    corrupted_tokens: TokenSequence | TokenBatch,
) -> float | list[float]:
    return _dispatch_metric(
        original_tokens,
        corrupted_tokens,
        single=_single_ned,
        batch=_batch_ned,
        name="normalized_edit_distance",
    )


def subsequence_retention(
    original_tokens: TokenSequence | TokenBatch,
    corrupted_tokens: TokenSequence | TokenBatch,
) -> float | list[float]:
    return _dispatch_metric(
        original_tokens,
        corrupted_tokens,
        single=_single_sr,
        batch=_batch_sr,
        name="subsequence_retention",
    )


def entropy_delta(
    original_tokens: TokenSequence | TokenBatch,
    corrupted_tokens: TokenSequence | TokenBatch,
) -> float | list[float]:
    """Compute normalized entropy delta between original and corrupted tokens.

    Measures the change in token distribution entropy:
    ΔH = H(corrupted) - H(original), normalized to [-1, 1].

    Positive values indicate the corrupted text has higher entropy
    (more uniform/diverse token distribution). Negative values indicate
    lower entropy (more concentrated distribution).

    Args:
        original_tokens: Original token sequence(s).
        corrupted_tokens: Corrupted token sequence(s).

    Returns:
        Normalized entropy delta in [-1, 1], or list for batches.
    """
    return _dispatch_metric(
        original_tokens,
        corrupted_tokens,
        single=_single_ed,
        batch=_batch_ed,
        name="entropy_delta",
    )


def merge_split_index(
    original_tokens: TokenSequence | TokenBatch,
    corrupted_tokens: TokenSequence | TokenBatch,
) -> float | list[float]:
    """Compute merge-split index measuring subword restructuring.

    Estimates 1→k (split) and k→1 (merge) token events from alignment.
    Higher values indicate more dramatic tokenization changes.

    MSI = (splits + merges) / max(m, n) ∈ [0, 1]

    Args:
        original_tokens: Original token sequence(s).
        corrupted_tokens: Corrupted token sequence(s).

    Returns:
        Merge-split index in [0, 1], or list for batches.
    """
    return _dispatch_metric(
        original_tokens,
        corrupted_tokens,
        single=_single_msi,
        batch=_batch_msi,
        name="merge_split_index",
    )


# ---------------------------------------------------------------------------
# MetricName Enum
# ---------------------------------------------------------------------------


class MetricName(str, Enum):
    """Built-in metric names.

    Use these instead of string literals to avoid typos and enable IDE completion.

    Example:
        >>> attack = Attack(Typogre(), metrics={MetricName.NED: normalized_edit_distance})
        >>> # or get all defaults:
        >>> attack = Attack(Typogre(), metrics=MetricName.defaults())
    """

    JSD = "jensen_shannon_divergence"
    NED = "normalized_edit_distance"
    SR = "subsequence_retention"
    HD = "entropy_delta"
    MSI = "merge_split_index"

    @property
    def func(self) -> "Callable[..., float | list[float]]":
        """Get the metric function for this name."""
        return _METRIC_FUNCTIONS[self]

    @classmethod
    def defaults(cls) -> dict[str, "Callable[..., float | list[float]]"]:
        """Get all built-in metrics as a dictionary.

        Returns:
            Dictionary mapping metric names to functions.
        """
        return {m.value: m.func for m in cls}


# Mapping from enum to function - populated after functions are defined
_METRIC_FUNCTIONS: dict[MetricName, "Callable[..., float | list[float]]"] = {
    MetricName.JSD: jensen_shannon_divergence,
    MetricName.NED: normalized_edit_distance,
    MetricName.SR: subsequence_retention,
    MetricName.HD: entropy_delta,
    MetricName.MSI: merge_split_index,
}


__all__ = [
    "Metric",
    "BatchMetric",
    "MetricName",
    "TokenBatch",
    "TokenSequence",
    "jensen_shannon_divergence",
    "normalized_edit_distance",
    "subsequence_retention",
    "entropy_delta",
    "merge_split_index",
]
