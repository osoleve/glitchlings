"""Attack submodule for comparing text before and after corruption."""

from .analysis import (
    GridSearch,
    GridSearchPoint,
    GridSearchResult,
    SeedSweep,
    SeedSweepResult,
    TokenizerComparison,
    TokenizerComparisonEntry,
    TokenizerComparisonResult,
    compute_aggregate_stats,
    format_stats_summary,
)
from .compose import (
    AttackResultComponents,
    EncodedPayload,
    build_batch_result,
    build_empty_metrics,
    build_empty_result,
    build_single_result,
    extract_transcript_contents,
    format_metrics_for_batch,
    format_metrics_for_single,
)
from .core import Attack, AttackResult, MultiAttackResult
from .encode import describe_tokenizer, encode_batch, encode_single
from .metrics import (
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from .metrics_dispatch import TokenBatch, TokenSequence, is_batch, validate_batch_consistency
from .tokenization import Tokenizer

__all__ = [
    # Core
    "Attack",
    "AttackResult",
    "MultiAttackResult",
    "Tokenizer",
    # Metrics
    "jensen_shannon_divergence",
    "normalized_edit_distance",
    "subsequence_retention",
    # Analysis tools
    "SeedSweep",
    "SeedSweepResult",
    "GridSearch",
    "GridSearchResult",
    "GridSearchPoint",
    "TokenizerComparison",
    "TokenizerComparisonResult",
    "TokenizerComparisonEntry",
    "compute_aggregate_stats",
    "format_stats_summary",
    # Compose (pure)
    "AttackResultComponents",
    "EncodedPayload",
    "build_batch_result",
    "build_empty_metrics",
    "build_empty_result",
    "build_single_result",
    "extract_transcript_contents",
    "format_metrics_for_batch",
    "format_metrics_for_single",
    # Encode (pure)
    "describe_tokenizer",
    "encode_batch",
    "encode_single",
    # Metrics dispatch (pure)
    "TokenBatch",
    "TokenSequence",
    "is_batch",
    "validate_batch_consistency",
]
