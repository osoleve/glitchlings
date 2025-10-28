from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

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


def _resolve_core_length(core: str, token: str) -> int:
    """Return a stable core-length measurement used by weighting heuristics."""

    candidate = core if core else token
    length = len(candidate)
    if length <= 0:
        stripped = token.strip()
        length = len(stripped) if stripped else len(token)
    if length <= 0:
        length = 1
    return length


def token_core_length(token: str) -> int:
    """Return the length of the main word characters for weighting heuristics."""
    _, core, _ = split_token_edges(token)
    return _resolve_core_length(core, token)


@dataclass(frozen=True)
class WordToken:
    """Metadata describing a non-whitespace token yielded by word splitters."""

    index: int
    prefix: str
    core: str
    suffix: str
    core_length: int

    @property
    def has_core(self) -> bool:
        """Return ``True`` when the token contains at least one core character."""
        return bool(self.core)


def collect_word_tokens(
    tokens: Sequence[str],
    *,
    skip_first_word: bool = False,
) -> list[WordToken]:
    """Return structured metadata for non-whitespace tokens within ``tokens``.

    Args:
        tokens: Token sequence produced by :func:`split_preserving_whitespace`.
        skip_first_word: Exclude the first candidate token (used by Rushmore to
            preserve leading words).

    """
    start = 2 if skip_first_word else 0
    collected: list[WordToken] = []
    for index in range(start, len(tokens), 2):
        token = tokens[index]
        if not token or token.isspace():
            continue

        prefix, core, suffix = split_token_edges(token)
        core_length = _resolve_core_length(core, token)

        collected.append(
            WordToken(
                index=index,
                prefix=prefix,
                core=core,
                suffix=suffix,
                core_length=core_length,
            )
        )

    return collected


__all__ = [
    "split_preserving_whitespace",
    "split_token_edges",
    "token_core_length",
    "WordToken",
    "collect_word_tokens",
]
