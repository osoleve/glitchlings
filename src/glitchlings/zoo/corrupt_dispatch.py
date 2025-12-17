"""Pure dispatch logic for Glitchling corruption operations.

This module contains the deterministic, side-effect-free logic for building
corruption plans. It separates the "what to corrupt" decision from the
"how to corrupt" execution.

**Design Philosophy:**

All functions in this module are *pure* - they perform dispatch analysis
based solely on their inputs, without side effects. They do not:
- Invoke corruption functions
- Modify state
- Perform I/O

The separation allows:
- Corruption dispatch to be tested without actual corruption
- Clear boundaries between planning and execution
- Reasoning about what will be corrupted before execution

See AGENTS.md "Functional Purity Architecture" for full details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..util.transcripts import (
    Transcript,
    TranscriptTarget,
    TranscriptTurn,
    is_transcript,
    resolve_transcript_indices,
)

# ---------------------------------------------------------------------------
# Type Definitions
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class StringCorruptionTarget:
    """Target specification for corrupting a plain string.

    Attributes:
        text: The string to corrupt.
    """

    text: str
    kind: Literal["string"] = "string"


@dataclass(slots=True, frozen=True)
class TranscriptTurnTarget:
    """Target specification for a single turn within a transcript.

    Attributes:
        index: Position of the turn in the transcript.
        content: The text content to corrupt.
    """

    index: int
    content: str


@dataclass(slots=True, frozen=True)
class TranscriptCorruptionTarget:
    """Target specification for corrupting transcript turns.

    Attributes:
        turns: List of turn targets with their indices and content.
        original_transcript: The original transcript for result assembly.
    """

    turns: tuple[TranscriptTurnTarget, ...]
    original_transcript: Transcript
    kind: Literal["transcript"] = "transcript"


# Union type for corruption targets
CorruptionTarget = StringCorruptionTarget | TranscriptCorruptionTarget


# ---------------------------------------------------------------------------
# Dispatch Functions
# ---------------------------------------------------------------------------


def resolve_corruption_target(
    text: str | Transcript,
    transcript_target: TranscriptTarget,
) -> CorruptionTarget:
    """Determine what needs to be corrupted from the input.

    This is a pure function that analyzes the input and returns a structured
    target specification. It does not perform any corruption.

    Args:
        text: Input text or transcript to analyze.
        transcript_target: Specification for which transcript turns to target.

    Returns:
        CorruptionTarget describing what should be corrupted.

    Note:
        Lists that are not valid transcripts (e.g., lists of strings) are
        treated as strings via casting. This handles cases like dataset column
        transformations where HuggingFace may batch values as lists.
    """
    # Handle plain strings
    if isinstance(text, str):
        return StringCorruptionTarget(text=text)

    # Handle transcripts (lists of dicts with "content" keys)
    if is_transcript(text):
        indices = resolve_transcript_indices(text, transcript_target)
        turn_targets: list[TranscriptTurnTarget] = []

        for idx in indices:
            turn = text[idx]
            content = turn.get("content")
            if isinstance(content, str):
                turn_targets.append(TranscriptTurnTarget(index=idx, content=content))

        return TranscriptCorruptionTarget(
            turns=tuple(turn_targets),
            original_transcript=text,
        )

    # Treat other types (including lists of strings) as strings by casting.
    # This handles cases like dataset column transformations where HuggingFace
    # may batch values as lists.
    return StringCorruptionTarget(text=str(text))


def count_corruption_targets(target: CorruptionTarget) -> int:
    """Count how many text segments will be corrupted.

    Args:
        target: The corruption target specification.

    Returns:
        Number of text segments that will be processed.
    """
    if isinstance(target, StringCorruptionTarget):
        return 1
    return len(target.turns)


def extract_texts_to_corrupt(target: CorruptionTarget) -> list[str]:
    """Extract all text strings that need to be corrupted.

    This is useful for batch processing or analysis.

    Args:
        target: The corruption target specification.

    Returns:
        List of text strings to corrupt.
    """
    if isinstance(target, StringCorruptionTarget):
        return [target.text]
    return [turn.content for turn in target.turns]


# ---------------------------------------------------------------------------
# Result Assembly Functions
# ---------------------------------------------------------------------------


def assemble_string_result(
    _target: StringCorruptionTarget,
    corrupted: str,
) -> str:
    """Assemble the result for a string corruption.

    Args:
        _target: The original target (unused, included for symmetry).
        corrupted: The corrupted text.

    Returns:
        The corrupted string.
    """
    return corrupted


def assemble_transcript_result(
    target: TranscriptCorruptionTarget,
    corrupted_contents: dict[int, str],
) -> Transcript:
    """Assemble the result for a transcript corruption.

    Creates a copy of the original transcript with specified turns updated.

    Args:
        target: The original target specification.
        corrupted_contents: Mapping of turn indices to corrupted content.

    Returns:
        New transcript with corrupted turns.
    """
    # Create a deep copy of the transcript
    result: list[TranscriptTurn] = [dict(turn) for turn in target.original_transcript]

    # Apply corrupted content to targeted turns
    for idx, content in corrupted_contents.items():
        if 0 <= idx < len(result):
            result[idx]["content"] = content

    return result


def assemble_corruption_result(
    target: CorruptionTarget,
    corrupted: str | dict[int, str],
) -> str | Transcript:
    """Assemble the final result based on target type.

    This is a pure function that combines the original target structure
    with the corrupted content.

    Args:
        target: The original corruption target.
        corrupted: Either a single corrupted string (for StringCorruptionTarget)
            or a mapping of indices to corrupted content (for TranscriptCorruptionTarget).

    Returns:
        The assembled result matching the input type.

    Raises:
        TypeError: If corrupted value type doesn't match target type.
    """
    if isinstance(target, StringCorruptionTarget):
        if not isinstance(corrupted, str):
            message = "String target requires corrupted string result"
            raise TypeError(message)
        return assemble_string_result(target, corrupted)

    if isinstance(target, TranscriptCorruptionTarget):
        if not isinstance(corrupted, dict):
            message = "Transcript target requires corrupted content mapping"
            raise TypeError(message)
        return assemble_transcript_result(target, corrupted)

    # Should be unreachable due to typing, but be explicit
    message = f"Unknown target type: {type(target).__name__}"
    raise TypeError(message)


# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------


def validate_text_input(text: Any) -> str | Transcript:
    """Validate that input is a supported text type.

    Args:
        text: Input to validate.

    Returns:
        The validated input.

    Raises:
        TypeError: If input is not a string or transcript.
    """
    if isinstance(text, str):
        return text
    if is_transcript(text):
        return text
    message = f"Expected string or transcript, got {type(text).__name__}"
    raise TypeError(message)


__all__ = [
    # Target types
    "StringCorruptionTarget",
    "TranscriptTurnTarget",
    "TranscriptCorruptionTarget",
    "CorruptionTarget",
    # Dispatch functions
    "resolve_corruption_target",
    "count_corruption_targets",
    "extract_texts_to_corrupt",
    # Result assembly
    "assemble_string_result",
    "assemble_transcript_result",
    "assemble_corruption_result",
    # Validation
    "validate_text_input",
]
