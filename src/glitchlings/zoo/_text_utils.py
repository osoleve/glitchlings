from __future__ import annotations

import re

_WORD_SPLIT_PATTERN = re.compile(r"(\s+)")
_TOKEN_EDGES_PATTERN = re.compile(r"^(\W*)(.*?)(\W*)$")


def split_preserving_whitespace(text: str) -> list[str]:
    """Split text while keeping whitespace tokens for stable reconstruction."""

    return _WORD_SPLIT_PATTERN.split(text)


def split_token_edges(token: str) -> tuple[str, str, str]:
    """Return leading, core, and trailing segments for a token."""

    match = _TOKEN_EDGES_PATTERN.match(token)
    if match is None:
        return "", token, ""
    return match.group(1), match.group(2), match.group(3)


def token_core_length(token: str) -> int:
    """Return the length of the main word characters for weighting heuristics."""

    _, core, _ = split_token_edges(token)
    candidate = core if core else token
    length = len(candidate)
    if length <= 0:
        stripped = token.strip()
        length = len(stripped) if stripped else len(token)
    if length <= 0:
        length = 1
    return length


__all__ = [
    "split_preserving_whitespace",
    "split_token_edges",
    "token_core_length",
]
