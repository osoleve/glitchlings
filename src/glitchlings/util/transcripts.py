"""Shared transcript type helpers used across attack and DLC modules."""

from __future__ import annotations

from typing import Any, TypeGuard

TranscriptTurn = dict[str, Any]
Transcript = list[TranscriptTurn]


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


__all__ = ["Transcript", "TranscriptTurn", "is_transcript"]
