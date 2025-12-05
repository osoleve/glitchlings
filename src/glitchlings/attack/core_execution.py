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
from typing import TYPE_CHECKING, Any, Callable, cast

from ..util.adapters import coerce_gaggle
from ..util.transcripts import Transcript, is_transcript
from .core_planning import (
    AttackPlan,
    EncodedData,
    ResultPlan,
    assemble_batch_result_fields,
    assemble_empty_result_fields,
    assemble_single_result_fields,
    extract_transcript_contents_pure,
)
from .encode import describe_tokenizer, encode_batch
from .metrics import (
    Metric,
    jensen_shannon_divergence,
    normalized_edit_distance,
    subsequence_retention,
)
from .tokenization import Tokenizer, resolve_tokenizer

if TYPE_CHECKING:
    from ..zoo.core import Glitchling


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
    }


# ---------------------------------------------------------------------------
# Glitchling Resolution
# ---------------------------------------------------------------------------


def resolve_glitchlings(
    glitchlings: "Glitchling | str | Sequence[str | Glitchling]",
    *,
    seed: int | None,
    transcript_target: Any = None,
) -> "Glitchling":
    """Resolve glitchling specification into a Gaggle.

    This impure function clones glitchlings and coerces them into a
    Gaggle with the specified seed.

    Args:
        glitchlings: Glitchling specification.
        seed: Master seed for the gaggle.
        transcript_target: Which transcript turns to corrupt.

    Returns:
        A Gaggle instance ready for corruption.
    """
    from ..zoo.core import Glitchling as GlitchlingClass

    # Clone to avoid mutating caller-owned objects
    if isinstance(glitchlings, GlitchlingClass):
        cloned = glitchlings.clone()
    elif isinstance(glitchlings, str):
        cloned: Any = glitchlings
    elif isinstance(glitchlings, Sequence):
        cloned_list: list[str | Glitchling] = []
        for entry in glitchlings:
            if isinstance(entry, GlitchlingClass):
                cloned_list.append(entry.clone())
            else:
                cloned_list.append(entry)
        cloned = cloned_list
    else:
        cloned = glitchlings

    return coerce_gaggle(
        cloned,
        seed=seed,
        apply_seed_to_existing=True,
        transcript_target=transcript_target,
    )


# ---------------------------------------------------------------------------
# Corruption Execution
# ---------------------------------------------------------------------------


def execute_corruption(
    gaggle: "Glitchling",
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
                raise TypeError("Attack expected string output for batch items.")
            corrupted_batch.append(corrupted)
        return corrupted_batch, corrupted_batch

    if plan.input_type == "transcript":
        corrupted_transcript = gaggle.corrupt(original_container)
        if not is_transcript(corrupted_transcript):
            raise ValueError("Attack expected transcript output for transcript input.")
        corrupted_contents = extract_transcript_contents_pure(
            cast(Sequence[Mapping[str, Any]], corrupted_transcript)
        )
        return corrupted_transcript, corrupted_contents

    # Single string
    corrupted = gaggle.corrupt(cast(str, original_container))
    if not isinstance(corrupted, str):
        raise TypeError("Attack expected string output for string input.")
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
    input_tokens: list[str] | list[list[str]],
    output_tokens: list[str] | list[list[str]],
    *,
    is_batch: bool,
) -> dict[str, float | list[float]]:
    """Execute metric computation.

    Args:
        metrics: Dictionary of metric functions.
        input_tokens: Original tokens (flat or batched).
        output_tokens: Corrupted tokens (flat or batched).
        is_batch: Whether inputs are batched.

    Returns:
        Dictionary of computed metric values.
    """
    # Prepare tokens for metrics
    if is_batch:
        metric_inputs: list[str] | list[list[str]] = input_tokens
        metric_outputs: list[str] | list[list[str]] = output_tokens
    else:
        # For single strings, pass flat token lists
        metric_inputs = input_tokens[0] if input_tokens else []  # type: ignore
        metric_outputs = output_tokens[0] if output_tokens else []  # type: ignore

    computed: dict[str, float | list[float]] = {}
    for name, metric_fn in metrics.items():
        computed[name] = metric_fn(metric_inputs, metric_outputs)

    return computed


# ---------------------------------------------------------------------------
# Full Attack Execution
# ---------------------------------------------------------------------------


def execute_attack(
    gaggle: "Glitchling",
    tokenizer: Tokenizer,
    metrics: dict[str, Metric],
    plan: AttackPlan,
    result_plan: ResultPlan,
    original_container: str | Transcript | Sequence[str],
) -> dict[str, object]:
    """Execute a complete attack and return result fields.

    This function orchestrates the full attack execution:
    1. Execute corruption
    2. Tokenize original and corrupted content
    3. Compute metrics
    4. Assemble result fields

    Args:
        gaggle: Glitchling(s) for corruption.
        tokenizer: Resolved tokenizer.
        metrics: Metric functions.
        plan: Attack execution plan.
        result_plan: Result assembly plan.
        original_container: Original input container.

    Returns:
        Dictionary of fields for AttackResult construction.
    """
    # Handle empty input
    if plan.is_empty:
        return assemble_empty_result_fields(
            original=original_container,  # type: ignore
            corrupted=original_container,  # type: ignore
            tokenizer_info=result_plan.tokenizer_info,
            metric_names=result_plan.metric_names,
        )

    # Execute corruption
    corrupted_container, corrupted_contents = execute_corruption(
        gaggle, plan, original_container
    )

    # Tokenize
    input_encoded = execute_tokenization(tokenizer, plan.original_contents)
    output_encoded = execute_tokenization(tokenizer, corrupted_contents)

    # Compute metrics
    raw_metrics = execute_metrics(
        metrics,
        cast(Any, input_encoded.tokens),
        cast(Any, output_encoded.tokens),
        is_batch=plan.is_batch,
    )

    # Format metrics according to result type
    formatted_metrics = result_plan.format_metrics(raw_metrics)

    # Assemble result
    if plan.is_batch:
        return assemble_batch_result_fields(
            original=original_container,  # type: ignore
            corrupted=corrupted_container,  # type: ignore
            input_encoded=input_encoded,
            output_encoded=output_encoded,
            tokenizer_info=result_plan.tokenizer_info,
            metrics=formatted_metrics,
        )

    return assemble_single_result_fields(
        original=cast(str, original_container),
        corrupted=cast(str, corrupted_container),
        input_encoded=input_encoded,
        output_encoded=output_encoded,
        tokenizer_info=result_plan.tokenizer_info,
        metrics=cast(dict[str, float], formatted_metrics),
    )


# ---------------------------------------------------------------------------
# Comparison Execution
# ---------------------------------------------------------------------------


def execute_comparison_entry(
    gaggle: "Glitchling",
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
