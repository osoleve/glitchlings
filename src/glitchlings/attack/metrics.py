from typing import Protocol, Sequence

try:
    from .._zoo_rust import (
        batch_jensen_shannon_divergence,
        batch_normalized_edit_distance,
        batch_subsequence_retention,
        jensen_shannon_divergence,
        normalized_edit_distance,
        subsequence_retention,
    )
except ImportError:
    raise ImportError(
        "Could not import compiled Rust extension. "
        "Please ensure the project is installed with the Rust extension built."
    )


class Metric(Protocol):
    def __call__(self, original_tokens: Sequence[str], corrupted_tokens: Sequence[str]) -> float:
        ...


__all__ = [
    "Metric",
    "jensen_shannon_divergence",
    "normalized_edit_distance",
    "subsequence_retention",
    "batch_jensen_shannon_divergence",
    "batch_normalized_edit_distance",
    "batch_subsequence_retention",
]
