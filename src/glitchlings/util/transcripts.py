"""Shared transcript type helpers used across attack and DLC modules."""

from __future__ import annotations

from typing import Any, Literal, Sequence, TypeGuard, Union

TranscriptTurn = dict[str, Any]
Transcript = list[TranscriptTurn]

# Type alias for transcript target specifications.
# - "last": corrupt only the last turn (default behavior)
# - "all": corrupt all turns
# - "assistant": corrupt only turns with role="assistant"
# - "user": corrupt only turns with role="user"
# - int: corrupt a specific index (negative indexing supported)
# - Sequence[int]: corrupt specific indices
TranscriptTarget = Union[Literal["last", "all", "assistant", "user"], int, Sequence[int]]


def is_transcript(
    value: Any,
    *,
    allow_empty: bool = True,
    require_all_content: bool = False,
) -> TypeGuard[Transcript]:
    """Return True when ``value`` appears to be a chat transcript mapping list."""
    if not isinstance(value, list):
        return False

    if not value:
        return allow_empty

    if not all(isinstance(turn, dict) for turn in value):
        return False

    if require_all_content:
        return all("content" in turn for turn in value)

    return "content" in value[-1]


def resolve_transcript_indices(
    transcript: Transcript,
    target: TranscriptTarget,
) -> list[int]:
    """Resolve a transcript target specification to concrete indices.

    Args:
        transcript: The transcript to resolve indices for.
        target: The target specification indicating which turns to corrupt.

    Returns:
        A list of valid indices into the transcript, sorted in ascending order.

    Raises:
        ValueError: If the target specification is invalid or references
            indices outside the transcript bounds.
    """
    if not transcript:
        return []

    length = len(transcript)

    if target == "last":
        return [length - 1]

    if target == "all":
        return list(range(length))

    if target == "assistant":
        return [i for i, turn in enumerate(transcript) if turn.get("role") == "assistant"]

    if target == "user":
        return [i for i, turn in enumerate(transcript) if turn.get("role") == "user"]

    if isinstance(target, int):
        # Normalize negative indices
        normalized = target if target >= 0 else length + target
        if not 0 <= normalized < length:
            raise ValueError(f"Transcript index {target} out of bounds for length {length}")
        return [normalized]

    # Handle sequence of indices
    if isinstance(target, Sequence) and not isinstance(target, str):
        indices: list[int] = []
        for idx in target:
            if not isinstance(idx, int):
                raise ValueError(f"Transcript indices must be integers, got {type(idx).__name__}")
            normalized = idx if idx >= 0 else length + idx
            if not 0 <= normalized < length:
                raise ValueError(f"Transcript index {idx} out of bounds for length {length}")
            indices.append(normalized)
        # Deduplicate and sort
        return sorted(set(indices))

    raise ValueError(
        f"Invalid transcript target: {target!r}. "
        "Expected 'last', 'all', 'assistant', 'user', int, or sequence of ints."
    )


__all__ = [
    "Transcript",
    "TranscriptTarget",
    "TranscriptTurn",
    "is_transcript",
    "resolve_transcript_indices",
]
