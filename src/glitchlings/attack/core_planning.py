"""Pure planning functions for Attack orchestration.

This module contains deterministic, side-effect-free logic for planning
attack execution and assembling results. Functions here operate on
already-resolved inputs without performing IO or invoking FFI.

**Design Philosophy:**

All functions in this module are *pure* - they perform planning and
composition based solely on their inputs, without side effects. They do not:
- Import or invoke Rust FFI
- Resolve tokenizers or glitchlings
- Create RNG instances
- Perform I/O of any kind

The separation allows:
- Plan verification without Rust dependencies
- Unit testing of orchestration logic in isolation
- Clear boundaries between planning and execution

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeGuard

from ..util.transcripts import Transcript

# ---------------------------------------------------------------------------
# Type Guards
# ---------------------------------------------------------------------------


def is_string_batch(value: Any) -> TypeGuard[Sequence[str]]:
    """Determine if value is a batch of strings (not a single string).

    Args:
        value: Value to check.

    Returns:
        True if value is a non-string sequence of strings.
    """
    if isinstance(value, (str, bytes)):
        return False
    if not isinstance(value, Sequence):
        return False
    return all(isinstance(item, str) for item in value)


def is_transcript_like(value: Any) -> bool:
    """Check if value resembles a transcript structure.

    A transcript is a sequence of mappings with 'role' and 'content' keys.

    Args:
        value: Value to check.

    Returns:
        True if value appears to be a transcript.
    """
    if not isinstance(value, Sequence):
        return False
    if isinstance(value, (str, bytes)):
        return False
    if not value:
        return True  # Empty sequence could be empty transcript
    first = value[0]
    return isinstance(first, Mapping) and "content" in first


# ---------------------------------------------------------------------------
# Attack Planning
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AttackPlan:
    """Pure representation of what an Attack will do.

    Attributes:
        input_type: Type of input ("string", "batch", "transcript").
        original_contents: List of content strings to process.
        batch_size: Number of items in the batch.
    """

    input_type: str
    original_contents: list[str]
    batch_size: int

    @property
    def is_batch(self) -> bool:
        """Return True if this plan represents batched input."""
        return self.input_type in ("batch", "transcript")

    @property
    def is_empty(self) -> bool:
        """Return True if there are no contents to process."""
        return self.batch_size == 0


def plan_attack(text: str | Transcript | Sequence[str]) -> AttackPlan:
    """Create an execution plan for the given input.

    This pure function analyzes the input structure and creates a plan
    without actually executing anything.

    Args:
        text: Input text, transcript, or batch of strings.

    Returns:
        AttackPlan describing how to process the input.

    Raises:
        TypeError: If input type is not recognized.
    """
    if is_string_batch(text):
        contents = list(text)
        return AttackPlan(
            input_type="batch",
            original_contents=contents,
            batch_size=len(contents),
        )

    if is_transcript_like(text):
        contents = extract_transcript_contents_pure(text)  # type: ignore[arg-type]
        return AttackPlan(
            input_type="transcript",
            original_contents=contents,
            batch_size=len(contents),
        )

    if isinstance(text, str):
        return AttackPlan(
            input_type="string",
            original_contents=[text],
            batch_size=1,
        )

    message = f"Attack expects string, transcript, or list of strings, got {type(text).__name__}"
    raise TypeError(message)


def extract_transcript_contents_pure(transcript: Sequence[Mapping[str, Any]]) -> list[str]:
    """Extract content strings from a transcript (pure version).

    Args:
        transcript: Sequence of turn mappings with 'content' keys.

    Returns:
        List of content strings.

    Raises:
        TypeError: If transcript structure is invalid.
    """
    contents: list[str] = []
    for index, turn in enumerate(transcript):
        if not isinstance(turn, Mapping):
            raise TypeError(f"Transcript turn #{index + 1} must be a mapping.")
        content = turn.get("content")
        if not isinstance(content, str):
            raise TypeError(f"Transcript turn #{index + 1} is missing string content.")
        contents.append(content)
    return contents


# ---------------------------------------------------------------------------
# Result Planning
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricPlan:
    """Plan for computing a single metric.

    Attributes:
        name: Metric name.
        use_batch: Whether to use batch computation.
    """

    name: str
    use_batch: bool


@dataclass(frozen=True, slots=True)
class ResultPlan:
    """Plan for assembling attack results.

    Attributes:
        is_batch: Whether results are batched.
        metric_names: Names of metrics to compute.
        tokenizer_info: Description of tokenizer being used.
    """

    is_batch: bool
    metric_names: tuple[str, ...]
    tokenizer_info: str

    def format_metrics(
        self,
        raw_metrics: dict[str, float | list[float]],
    ) -> dict[str, float | list[float]]:
        """Format metrics according to the result type.

        For single results, collapses list metrics to scalars.
        For batch results, ensures all metrics are lists.

        Args:
            raw_metrics: Raw metric values from computation.

        Returns:
            Formatted metrics appropriate for the result type.
        """
        if self.is_batch:
            return _format_metrics_for_batch(raw_metrics)  # type: ignore[return-value]
        return _format_metrics_for_single(raw_metrics)  # type: ignore[return-value]


def plan_result(
    attack_plan: AttackPlan,
    metric_names: Sequence[str],
    tokenizer_info: str,
) -> ResultPlan:
    """Create a plan for assembling results.

    Args:
        attack_plan: The attack execution plan.
        metric_names: Names of metrics being computed.
        tokenizer_info: Description of the tokenizer.

    Returns:
        ResultPlan for assembling the final result.
    """
    return ResultPlan(
        is_batch=attack_plan.is_batch,
        metric_names=tuple(metric_names),
        tokenizer_info=tokenizer_info,
    )


# ---------------------------------------------------------------------------
# Metric Formatting (Pure)
# ---------------------------------------------------------------------------


def _format_metrics_for_single(
    metrics: dict[str, float | list[float]],
) -> dict[str, float]:
    """Collapse batch metrics to single values.

    Args:
        metrics: Raw metrics that may be lists.

    Returns:
        Metrics as scalar floats.
    """
    result: dict[str, float] = {}
    for name, value in metrics.items():
        if isinstance(value, list):
            result[name] = value[0] if value else 0.0
        else:
            result[name] = value
    return result


def _format_metrics_for_batch(
    metrics: dict[str, float | list[float]],
) -> dict[str, list[float]]:
    """Ensure all metrics are lists.

    Args:
        metrics: Raw metrics that may be scalars.

    Returns:
        Metrics as lists of floats.
    """
    result: dict[str, list[float]] = {}
    for name, value in metrics.items():
        if isinstance(value, list):
            result[name] = list(value)
        else:
            result[name] = [value]
    return result


# ---------------------------------------------------------------------------
# Result Assembly (Pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EncodedData:
    """Encoded token data for result assembly.

    Attributes:
        tokens: Token strings (flat or batched).
        token_ids: Token IDs (flat or batched).
    """

    tokens: list[str] | list[list[str]]
    token_ids: list[int] | list[list[int]]


def assemble_single_result_fields(
    *,
    original: str,
    corrupted: str,
    input_encoded: EncodedData,
    output_encoded: EncodedData,
    tokenizer_info: str,
    metrics: dict[str, float],
) -> dict[str, object]:
    """Assemble field dictionary for single-string AttackResult.

    Args:
        original: Original input string.
        corrupted: Corrupted output string.
        input_encoded: Encoded original tokens.
        output_encoded: Encoded corrupted tokens.
        tokenizer_info: Tokenizer description.
        metrics: Computed metrics (scalar).

    Returns:
        Dictionary suitable for AttackResult construction.
    """
    # For single strings, tokens are batched internally as [[...]]
    # so we unwrap the first (and only) element
    input_tokens = input_encoded.tokens[0] if input_encoded.tokens else []
    output_tokens = output_encoded.tokens[0] if output_encoded.tokens else []
    input_ids = input_encoded.token_ids[0] if input_encoded.token_ids else []
    output_ids = output_encoded.token_ids[0] if output_encoded.token_ids else []

    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_token_ids": input_ids,
        "output_token_ids": output_ids,
        "tokenizer_info": tokenizer_info,
        "metrics": metrics,
    }


def assemble_batch_result_fields(
    *,
    original: Transcript | Sequence[str],
    corrupted: Transcript | Sequence[str],
    input_encoded: EncodedData,
    output_encoded: EncodedData,
    tokenizer_info: str,
    metrics: dict[str, float | list[float]],
) -> dict[str, object]:
    """Assemble field dictionary for batched AttackResult.

    Args:
        original: Original transcript or string batch.
        corrupted: Corrupted transcript or string batch.
        input_encoded: Encoded original tokens (batched).
        output_encoded: Encoded corrupted tokens (batched).
        tokenizer_info: Tokenizer description.
        metrics: Computed metrics (list per batch item).

    Returns:
        Dictionary suitable for AttackResult construction.
    """
    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": input_encoded.tokens,
        "output_tokens": output_encoded.tokens,
        "input_token_ids": input_encoded.token_ids,
        "output_token_ids": output_encoded.token_ids,
        "tokenizer_info": tokenizer_info,
        "metrics": metrics,
    }


def assemble_empty_result_fields(
    *,
    original: Transcript | Sequence[str],
    corrupted: Transcript | Sequence[str],
    tokenizer_info: str,
    metric_names: Sequence[str],
) -> dict[str, object]:
    """Assemble field dictionary for empty input.

    Args:
        original: Original empty transcript or list.
        corrupted: Corrupted empty transcript or list.
        tokenizer_info: Tokenizer description.
        metric_names: Names of metrics to include as empty.

    Returns:
        Dictionary suitable for AttackResult construction.
    """
    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": [],
        "output_tokens": [],
        "input_token_ids": [],
        "output_token_ids": [],
        "tokenizer_info": tokenizer_info,
        "metrics": {name: [] for name in metric_names},
    }


# ---------------------------------------------------------------------------
# Token Count Helpers (Pure)
# ---------------------------------------------------------------------------


def compute_token_counts(
    input_tokens: list[str] | list[list[str]],
    output_tokens: list[str] | list[list[str]],
) -> tuple[list[int], list[int]]:
    """Compute token counts for inputs and outputs.

    Handles both single sequences and batches.

    Args:
        input_tokens: Input token sequence(s).
        output_tokens: Output token sequence(s).

    Returns:
        Tuple of (input_counts, output_counts) as lists.
    """
    # Check if batched
    if input_tokens and isinstance(input_tokens[0], list):
        input_counts = [len(batch) for batch in input_tokens]
        output_counts = [len(batch) for batch in output_tokens]
    else:
        input_counts = [len(input_tokens)]
        output_counts = [len(output_tokens)]
    return input_counts, output_counts


def format_token_count_delta(input_count: int, output_count: int) -> str:
    """Format a token count change as a string.

    Args:
        input_count: Number of input tokens.
        output_count: Number of output tokens.

    Returns:
        Formatted string like "10 -> 12 (+2)".
    """
    delta = output_count - input_count
    return f"{input_count} -> {output_count} ({delta:+d})"


# ---------------------------------------------------------------------------
# Comparison Planning
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ComparisonPlan:
    """Plan for comparing multiple tokenizers.

    Attributes:
        tokenizer_specs: List of tokenizer specifications to compare.
        include_self: Whether to include the base tokenizer.
    """

    tokenizer_specs: tuple[Any, ...]
    include_self: bool

    @property
    def total_comparisons(self) -> int:
        """Total number of tokenizers to compare."""
        count = len(self.tokenizer_specs)
        if self.include_self:
            count += 1
        return count


def plan_comparison(
    tokenizer_specs: Sequence[Any],
    *,
    include_self: bool = True,
) -> ComparisonPlan:
    """Create a plan for tokenizer comparison.

    Args:
        tokenizer_specs: Tokenizer names or instances to compare.
        include_self: Whether to include the base tokenizer.

    Returns:
        ComparisonPlan for the comparison.

    Raises:
        ValueError: If no tokenizers would be compared.
    """
    if not tokenizer_specs and not include_self:
        raise ValueError("At least one tokenizer must be provided for comparison.")

    return ComparisonPlan(
        tokenizer_specs=tuple(tokenizer_specs),
        include_self=include_self,
    )


__all__ = [
    # Type guards
    "is_string_batch",
    "is_transcript_like",
    # Attack planning
    "AttackPlan",
    "plan_attack",
    "extract_transcript_contents_pure",
    # Result planning
    "MetricPlan",
    "ResultPlan",
    "plan_result",
    # Result assembly
    "EncodedData",
    "assemble_single_result_fields",
    "assemble_batch_result_fields",
    "assemble_empty_result_fields",
    # Token counts
    "compute_token_counts",
    "format_token_count_delta",
    # Comparison planning
    "ComparisonPlan",
    "plan_comparison",
]
