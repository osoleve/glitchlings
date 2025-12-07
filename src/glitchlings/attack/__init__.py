"""Attack submodule for comparing text before and after corruption.

This module follows the functional purity architecture:

**Pure Planning** (core_planning.py):
- Input analysis and type guards
- Attack plan construction
- Result assembly helpers

**Impure Execution** (core_execution.py):
- Glitchling resolution
- Tokenization execution
- Metric computation

**Boundary Layer** (core.py):
- Input validation
- Orchestration via Attack class

**Analysis Tools** (analysis.py):
- SeedSweep, GridSearch, TokenizerComparison

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from .analysis import (
    GlitchlingComparisonEntry,
    GlitchlingComparisonResult,
    GridSearch,
    GridSearchPoint,
    GridSearchResult,
    SeedSweep,
    SeedSweepResult,
    TokenizerComparison,
    TokenizerComparisonEntry,
    TokenizerComparisonResult,
    compare_glitchlings,
    compare_tokenizers,
    compute_aggregate_stats,
    extract_scalar_metrics,
    format_stats_summary,
    generate_param_combinations,
    rank_grid_points,
)
from .core import Attack, AttackResult
from .core_execution import (
    execute_attack,
    execute_corruption,
    execute_metrics,
    execute_tokenization,
    get_default_metrics,
    resolve_glitchlings,
)
from .core_planning import (
    AttackPlan,
    BatchAdapter,
    EncodedData,
    ResultPlan,
    assemble_batch_result_fields,
    assemble_empty_result_fields,
    assemble_result_fields,
    assemble_single_result_fields,
    compute_token_counts,
    extract_transcript_contents,
    format_token_count_delta,
    is_string_batch,
    is_transcript_like,
    plan_attack,
    plan_result,
)
from .encode import describe_tokenizer, encode_batch, encode_single
from .metrics import (
    MetricName,
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from .metrics_dispatch import TokenBatch, TokenSequence, is_batch, validate_batch_consistency
from .tokenization import Tokenizer, list_available_tokenizers

__all__ = [
    # Core orchestration
    "Attack",
    "AttackResult",
    "Tokenizer",
    "list_available_tokenizers",
    # Metrics
    "MetricName",
    "jensen_shannon_divergence",
    "normalized_edit_distance",
    "subsequence_retention",
    # Analysis tools (impure orchestrators)
    "SeedSweep",
    "SeedSweepResult",
    "GridSearch",
    "GridSearchResult",
    "GridSearchPoint",
    "TokenizerComparison",
    "TokenizerComparisonResult",
    "TokenizerComparisonEntry",
    # Comparison functions
    "compare_glitchlings",
    "compare_tokenizers",
    "GlitchlingComparisonEntry",
    "GlitchlingComparisonResult",
    # Analysis pure helpers
    "compute_aggregate_stats",
    "format_stats_summary",
    "extract_scalar_metrics",
    "generate_param_combinations",
    "rank_grid_points",
    # Core planning (pure)
    "AttackPlan",
    "BatchAdapter",
    "ResultPlan",
    "EncodedData",
    "plan_attack",
    "plan_result",
    "is_string_batch",
    "is_transcript_like",
    "assemble_result_fields",
    "assemble_single_result_fields",
    "assemble_batch_result_fields",
    "assemble_empty_result_fields",
    "compute_token_counts",
    "extract_transcript_contents",
    "format_token_count_delta",
    # Core execution (impure)
    "get_default_metrics",
    "resolve_glitchlings",
    "execute_corruption",
    "execute_tokenization",
    "execute_metrics",
    "execute_attack",
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
