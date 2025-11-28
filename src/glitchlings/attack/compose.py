"""Pure result assembly functions for Attack.

This module contains pure functions for composing AttackResult instances
from pre-computed components. Functions here are:

- **Pure**: Output depends only on inputs, no side effects
- **Deterministic**: Same inputs always produce same outputs
- **Self-contained**: No IO, no Rust FFI, no config loading

Design Philosophy
-----------------
This module implements the innermost layer of Attack composition:

    Attack.run() → tokenize → corrupt → compose.py → AttackResult
    (orchestrator)  (impure)   (impure)   (pure)       (value)

Functions receive already-computed tokens, IDs, and metrics. They trust
that inputs are valid and do not re-validate. Boundary validation happens
in Attack.__init__ and before calling these functions.

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..util.transcripts import Transcript


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EncodedPayload:
    """Encoded representation of text or transcript for metric computation.

    Attributes:
        tokens: Token strings from tokenizer (flat or batched).
        token_ids: Token IDs from tokenizer (flat or batched).
        is_batched: True if this represents a transcript (batch of texts).
    """

    tokens: list[str] | list[list[str]]
    token_ids: list[int] | list[list[int]]
    is_batched: bool


@dataclass(frozen=True, slots=True)
class AttackResultComponents:
    """Intermediate structure holding all components needed for AttackResult.

    This is a pure value type that aggregates pre-computed components
    before final assembly into AttackResult.
    """

    original: "str | Transcript"
    corrupted: "str | Transcript"
    input_encoded: EncodedPayload
    output_encoded: EncodedPayload
    tokenizer_info: str
    metrics: dict[str, float | list[float]]


# ---------------------------------------------------------------------------
# Transcript Content Extraction
# ---------------------------------------------------------------------------


def extract_transcript_contents(transcript: "Transcript") -> list[str]:
    """Extract content strings from a chat transcript.

    This is a pure function that extracts the 'content' field from each
    turn in a transcript. It trusts that the transcript structure is valid
    (validated at Attack boundary).

    Args:
        transcript: List of turn dictionaries, each containing a 'content' key.

    Returns:
        List of content strings in turn order.

    Raises:
        TypeError: If a turn is missing 'content' or it isn't a string.
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
# Metric Formatting
# ---------------------------------------------------------------------------


def format_metrics_for_single(
    metrics: dict[str, float | list[float]],
) -> dict[str, float]:
    """Collapse batch metrics to single values for non-transcript results.

    When Attack processes a single string (not a transcript), metrics should
    be scalar floats. This function extracts the first element from any
    list-valued metrics.

    Args:
        metrics: Dictionary of metric names to values (float or list[float]).

    Returns:
        Dictionary with all values as floats.
    """
    result: dict[str, float] = {}
    for name, value in metrics.items():
        if isinstance(value, list):
            result[name] = value[0] if value else 0.0
        else:
            result[name] = value
    return result


def format_metrics_for_batch(
    metrics: dict[str, float | list[float]],
) -> dict[str, list[float]]:
    """Normalize metrics to list format for transcript results.

    When Attack processes a transcript (batch), metrics should be lists.
    This function wraps any scalar floats in single-element lists.

    Args:
        metrics: Dictionary of metric names to values (float or list[float]).

    Returns:
        Dictionary with all values as lists of floats.
    """
    result: dict[str, list[float]] = {}
    for name, value in metrics.items():
        if isinstance(value, list):
            result[name] = list(value)
        else:
            result[name] = [value]
    return result


# ---------------------------------------------------------------------------
# Empty Result Construction
# ---------------------------------------------------------------------------


def build_empty_metrics(metric_names: list[str]) -> dict[str, list[float]]:
    """Create empty metric results for empty transcript input.

    Args:
        metric_names: Names of metrics to include.

    Returns:
        Dictionary mapping each metric name to an empty list.
    """
    return {name: [] for name in metric_names}


# ---------------------------------------------------------------------------
# Result Assembly
# ---------------------------------------------------------------------------


def build_single_result(
    original: str,
    corrupted: str,
    input_tokens: list[str],
    input_token_ids: list[int],
    output_tokens: list[str],
    output_token_ids: list[int],
    tokenizer_info: str,
    metrics: dict[str, float | list[float]],
) -> dict[str, object]:
    """Assemble AttackResult field dictionary for single-string input.

    This is a pure function that takes all pre-computed components and
    returns a dictionary suitable for constructing an AttackResult.

    Args:
        original: Original input string.
        corrupted: Corrupted output string.
        input_tokens: Tokenized input.
        input_token_ids: Token IDs for input.
        output_tokens: Tokenized output.
        output_token_ids: Token IDs for output.
        tokenizer_info: Description of the tokenizer used.
        metrics: Computed metrics (will be collapsed to scalars).

    Returns:
        Dictionary with all AttackResult field values.
    """
    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_token_ids": input_token_ids,
        "output_token_ids": output_token_ids,
        "tokenizer_info": tokenizer_info,
        "metrics": format_metrics_for_single(metrics),
    }


def build_batch_result(
    original: "Transcript | Sequence[str]",
    corrupted: "Transcript | Sequence[str]",
    input_tokens: list[list[str]],
    input_token_ids: list[list[int]],
    output_tokens: list[list[str]],
    output_token_ids: list[list[int]],
    tokenizer_info: str,
    metrics: dict[str, float | list[float]],
) -> dict[str, object]:
    """Assemble AttackResult field dictionary for batched input.

    This is a pure function that takes all pre-computed components and
    returns a dictionary suitable for constructing an AttackResult.

    Args:
        original: Original transcript or list of strings.
        corrupted: Corrupted transcript or list of strings.
        input_tokens: Batched tokenized inputs.
        input_token_ids: Batched token IDs for inputs.
        output_tokens: Batched tokenized outputs.
        output_token_ids: Batched token IDs for outputs.
        tokenizer_info: Description of the tokenizer used.
        metrics: Computed metrics (already in batch format).

    Returns:
        Dictionary with all AttackResult field values.
    """
    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_token_ids": input_token_ids,
        "output_token_ids": output_token_ids,
        "tokenizer_info": tokenizer_info,
        "metrics": metrics,
    }


def build_empty_result(
    original: "Transcript | Sequence[str]",
    corrupted: "Transcript | Sequence[str]",
    tokenizer_info: str,
    metric_names: list[str],
) -> dict[str, object]:
    """Assemble AttackResult field dictionary for empty batch input.

    Args:
        original: Original empty transcript or list.
        corrupted: Corrupted empty transcript or list.
        tokenizer_info: Description of the tokenizer used.
        metric_names: Names of metrics to include as empty lists.

    Returns:
        Dictionary with all AttackResult field values for empty input.
    """
    return {
        "original": original,
        "corrupted": corrupted,
        "input_tokens": [],
        "output_tokens": [],
        "input_token_ids": [],
        "output_token_ids": [],
        "tokenizer_info": tokenizer_info,
        "metrics": build_empty_metrics(metric_names),
    }


__all__ = [
    # Types
    "AttackResultComponents",
    "EncodedPayload",
    # Transcript helpers
    "extract_transcript_contents",
    # Metric formatting
    "build_empty_metrics",
    "format_metrics_for_batch",
    "format_metrics_for_single",
    # Result assembly
    "build_batch_result",
    "build_empty_result",
    "build_single_result",
]
