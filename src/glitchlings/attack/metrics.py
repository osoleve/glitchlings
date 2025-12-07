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
_batch_jsd = cast(BatchMetric, getattr(_rust, "batch_jensen_shannon_divergence"))
_batch_ned = cast(BatchMetric, getattr(_rust, "batch_normalized_edit_distance"))
_batch_sr = cast(BatchMetric, getattr(_rust, "batch_subsequence_retention"))


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
]
