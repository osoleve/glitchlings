"""Impure execution dispatch for Attack orchestration.

This module handles the actual execution of attack plans, including
tokenizer resolution, glitchling invocation, and metric computation.
It is the impure counterpart to core_planning.py.

**Design Philosophy:**

This module is explicitly *impure* - it resolves tokenizers, invokes
glitchling corruption functions, and calls Rust metrics. All impure
operations for Attack execution flow through this module.

The separation allows:
- Pure planning logic to be tested without dependencies
- Clear boundaries between plan construction and execution
- Mocking execution for integration tests

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from ..util.adapters import coerce_gaggle
from ..util.transcripts import Transcript, is_transcript
from .core_planning import (
    AttackPlan,
    BatchAdapter,
    EncodedData,
    ResultPlan,
    assemble_empty_result_fields,
    assemble_result_fields,
    extract_transcript_contents,
)
from .encode import encode_batch
from .metrics import (
    Metric,
    entropy_delta,
    jensen_shannon_divergence,
    merge_split_index,
    normalized_edit_distance,
    subsequence_retention,
)
from .tokenization import Tokenizer

if TYPE_CHECKING:
    from ..protocols import Corruptor


# ---------------------------------------------------------------------------
# Default Metrics
# ---------------------------------------------------------------------------


def get_default_metrics() -> dict[str, Metric]:
    """Return the default set of metrics for Attack.

    Returns:
        Dictionary mapping metric names to metric functions.
    """
    return {
        "jensen_shannon_divergence": jensen_shannon_divergence,
        "normalized_edit_distance": normalized_edit_distance,
        "subsequence_retention": subsequence_retention,
        "entropy_delta": entropy_delta,
        "merge_split_index": merge_split_index,
    }


# ---------------------------------------------------------------------------
# Glitchling Resolution
# ---------------------------------------------------------------------------


def resolve_glitchlings(
    glitchlings: "Corruptor | str | Sequence[str | Corruptor]",
    *,
    seed: int | None,
    transcript_target: Any = None,
) -> "Corruptor":
    """Resolve glitchling specification into a Gaggle.

    This impure function clones glitchlings and coerces them into a
    Gaggle with the specified seed.

    Args:
        glitchlings: Glitchling specification.
        seed: Master seed for the gaggle. If None, uses DEFAULT_ATTACK_SEED.
        transcript_target: Which transcript turns to corrupt.

    Returns:
        A Gaggle instance ready for corruption.
    """
    from ..conf import DEFAULT_ATTACK_SEED
    from ..protocols import Corruptor as CorruptorProtocol

    effective_seed = seed if seed is not None else DEFAULT_ATTACK_SEED

    # Clone to avoid mutating caller-owned objects
    cloned: Any
    if isinstance(glitchlings, CorruptorProtocol):
        cloned = glitchlings.clone()
    elif isinstance(glitchlings, str):
        cloned = glitchlings
    elif isinstance(glitchlings, Sequence):
        cloned_list: list[str | Corruptor] = []
        for entry in glitchlings:
            if isinstance(entry, CorruptorProtocol):
                cloned_list.append(entry.clone())
            else:
                cloned_list.append(entry)
        cloned = cloned_list
    else:
        cloned = glitchlings

    return coerce_gaggle(
        cloned,
        seed=effective_seed,
        apply_seed_to_existing=True,
        transcript_target=transcript_target,
    )


# ---------------------------------------------------------------------------
# Corruption Execution
# ---------------------------------------------------------------------------


def execute_corruption(
    gaggle: "Corruptor",
    plan: AttackPlan,
    original_container: str | Transcript | Sequence[str],
) -> tuple[str | Transcript | Sequence[str], list[str]]:
    """Execute corruption according to the attack plan.

    Args:
        gaggle: The glitchling(s) to use for corruption.
        plan: The attack execution plan.
        original_container: The original input container.

    Returns:
        Tuple of (corrupted_container, corrupted_contents).

    Raises:
        TypeError: If output type doesn't match input type.
    """
    if plan.input_type == "batch":
        original_batch = list(cast(Sequence[str], original_container))
        corrupted_batch: list[str] = []
        for entry in original_batch:
            corrupted = gaggle.corrupt(entry)
            if not isinstance(corrupted, str):
                raise TypeError(
                    f"Attack expected str output for batch items, got {type(corrupted).__name__}"
                )
            corrupted_batch.append(corrupted)
        return corrupted_batch, corrupted_batch

    if plan.input_type == "transcript":
        corrupted_transcript = gaggle.corrupt(cast(Transcript, original_container))
        if not is_transcript(corrupted_transcript):
            raise ValueError(
                f"Attack expected transcript output for transcript input, "
                f"got {type(corrupted_transcript).__name__}"
            )
        corrupted_contents = extract_transcript_contents(
            cast(Sequence[Mapping[str, Any]], corrupted_transcript)
        )
        return corrupted_transcript, corrupted_contents

    # Single string
    corrupted = gaggle.corrupt(cast(str, original_container))
    if not isinstance(corrupted, str):
        raise TypeError(
            f"Attack expected str output for string input, got {type(corrupted).__name__}"
        )
    return corrupted, [corrupted]


# ---------------------------------------------------------------------------
# Tokenization Execution
# ---------------------------------------------------------------------------


def execute_tokenization(
    tokenizer: Tokenizer,
    contents: list[str],
) -> EncodedData:
    """Execute tokenization on content strings.

    Args:
        tokenizer: Resolved tokenizer instance.
        contents: List of strings to tokenize.

    Returns:
        EncodedData with tokens and token IDs.
    """
    if not contents:
        return EncodedData(tokens=[], token_ids=[])

    batched_tokens, batched_ids = encode_batch(tokenizer, contents)
    return EncodedData(tokens=batched_tokens, token_ids=batched_ids)


# ---------------------------------------------------------------------------
# Metric Execution
# ---------------------------------------------------------------------------


def execute_metrics(
    metrics: dict[str, Metric],
    input_tokens: list[list[str]],
    output_tokens: list[list[str]],
) -> dict[str, list[float]]:
    """Execute metric computation on batched tokens.

    All inputs are processed as batches internally. Use BatchAdapter
    to unwrap results for single-item inputs.

    Args:
        metrics: Dictionary of metric functions.
        input_tokens: Original tokens (always batched 2D list).
        output_tokens: Corrupted tokens (always batched 2D list).

    Returns:
        Dictionary of computed metric values (always as lists).
    """
    computed: dict[str, list[float]] = {}
    for name, metric_fn in metrics.items():
        result = metric_fn(input_tokens, output_tokens)
        # Ensure result is always a list
        if isinstance(result, list):
            computed[name] = result
        else:
            computed[name] = [result]

    return computed


# ---------------------------------------------------------------------------
# Full Attack Execution
# ---------------------------------------------------------------------------


def execute_attack(
    gaggle: "Corruptor",
    tokenizer: Tokenizer,
    metrics: dict[str, Metric],
    plan: AttackPlan,
    result_plan: ResultPlan,
    original_container: str | Transcript | Sequence[str],
    *,
    include_tokens: bool = True,
) -> dict[str, object]:
    """Execute a complete attack and return result fields.

    This function orchestrates the full attack execution:
    1. Create batch adapter for uniform processing
    2. Execute corruption
    3. Tokenize original and corrupted content (always as batch)
    4. Compute metrics (always as batch)
    5. Assemble result fields (adapter unwraps as needed)

    Args:
        gaggle: Glitchling(s) for corruption.
        tokenizer: Resolved tokenizer.
        metrics: Metric functions.
        plan: Attack execution plan.
        result_plan: Result assembly plan.
        original_container: Original input container.
        include_tokens: Whether to include tokens in the result. If False,
            tokens are computed for metrics but not stored in the result.
            Defaults to True.

    Returns:
        Dictionary of fields for AttackResult construction.
    """
    # Handle empty input
    if plan.is_empty:
        return assemble_empty_result_fields(
            original=original_container,
            corrupted=original_container,
            tokenizer_info=result_plan.tokenizer_info,
            metric_names=result_plan.metric_names,
        )

    # Create batch adapter for uniform processing
    adapter = BatchAdapter.from_plan(plan)

    # Execute corruption
    corrupted_container, corrupted_contents = execute_corruption(gaggle, plan, original_container)

    # Tokenize (always returns batched EncodedData)
    input_encoded = execute_tokenization(tokenizer, plan.original_contents)
    output_encoded = execute_tokenization(tokenizer, corrupted_contents)

    # Compute metrics (always returns batched metrics)
    batch_metrics = execute_metrics(
        metrics,
        input_encoded.tokens,
        output_encoded.tokens,
    )

    # If not including tokens, use empty EncodedData for result assembly
    if not include_tokens:
        empty_encoded = EncodedData(tokens=[], token_ids=[])
        input_encoded = empty_encoded
        output_encoded = empty_encoded

    # Assemble result (adapter handles unwrapping for single inputs)
    return assemble_result_fields(
        adapter=adapter,
        original=original_container,
        corrupted=corrupted_container,
        input_encoded=input_encoded,
        output_encoded=output_encoded,
        tokenizer_info=result_plan.tokenizer_info,
        metrics=batch_metrics,
    )


# ---------------------------------------------------------------------------
# Comparison Execution
# ---------------------------------------------------------------------------


def execute_comparison_entry(
    gaggle: "Corruptor",
    tokenizer: Tokenizer,
    tokenizer_info: str,
    metrics: dict[str, Metric],
    text: str | Transcript | Sequence[str],
) -> tuple[str, dict[str, object]]:
    """Execute a single comparison entry.

    Args:
        gaggle: Glitchling(s) for corruption.
        tokenizer: Resolved tokenizer.
        tokenizer_info: Tokenizer description.
        metrics: Metric functions.
        text: Input text.

    Returns:
        Tuple of (tokenizer_info, result_fields).
    """
    from .core_planning import plan_attack, plan_result

    # Create plans
    attack_plan = plan_attack(text)
    result_plan = plan_result(attack_plan, list(metrics.keys()), tokenizer_info)

    # Execute
    fields = execute_attack(
        gaggle,
        tokenizer,
        metrics,
        attack_plan,
        result_plan,
        text,
    )

    return tokenizer_info, fields


__all__ = [
    # Defaults
    "get_default_metrics",
    # Resolution
    "resolve_glitchlings",
    # Execution
    "execute_corruption",
    "execute_tokenization",
    "execute_metrics",
    "execute_attack",
    "execute_comparison_entry",
]
